"""ReidX atomic quota reservations. Fail closed; never substitute a model.
Counts attempts, not successful completions. Local caps do not mirror provider quotas.
Update alias buckets when changing upstream models. Untracked aliases are exempt.
"""
import json
import os
from pathlib import Path
import sqlite3
from datetime import datetime, timezone
from litellm.integrations.custom_logger import CustomLogger

CONFIG_PATH = Path(os.getenv("BUDGET_GUARD_CONFIG", str(Path(__file__).with_name("budget_config.json"))))
DB_PATH = Path(os.getenv("BUDGET_GUARD_DB", str(Path.home() / ".local/share/reidx/budget.sqlite3")))


class QuotaExhausted(ValueError):
    pass


def check_and_record(model):
    try:
        config = json.loads(CONFIG_PATH.read_text())
        if not isinstance(config["aliases"], dict) or not isinstance(config["daily_caps"], dict):
            raise ValueError("Invalid quota configuration")
        bucket = config["aliases"].get(model)
        if bucket is None:
            return
        cap = config["daily_caps"][bucket]
        aggregate = config["aggregate_daily_cap"]
        if any(type(v) is not int or v < 1 for v in (cap, aggregate)):
            raise ValueError("Invalid quota cap")
        if DB_PATH.is_symlink() or DB_PATH.parent.is_symlink():
            raise ValueError("Quota storage symlink denied")
        DB_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        day = datetime.now(timezone.utc).date().isoformat()
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            os.chmod(DB_PATH, 0o600)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("CREATE TABLE IF NOT EXISTS requests (upstream_model TEXT, day TEXT, count INTEGER, PRIMARY KEY(upstream_model,day))")
            conn.execute("BEGIN IMMEDIATE")
            for key, ceiling in ((bucket, cap), ("__aggregate__", aggregate)):
                row = conn.execute("SELECT count FROM requests WHERE upstream_model=? AND day=?", (key,day)).fetchone()
                if row and row[0] >= ceiling:
                    raise QuotaExhausted("ReidX quota exhausted; wait for UTC reset or request an operator configuration change")
            for key in (bucket, "__aggregate__"):
                conn.execute("INSERT INTO requests VALUES (?,?,1) ON CONFLICT(upstream_model,day) DO UPDATE SET count=count+1", (key,day))
            conn.commit()
    except QuotaExhausted:
        raise
    except Exception:
        # Do not leak DB paths, credentials, request bodies or upstream exception text.
        raise ValueError("ReidX quota reservation denied: cap exhausted or configuration/storage unavailable") from None


class BudgetGuard(CustomLogger):
    async def async_pre_call_hook(self, user_api_key_dict, cache, data, call_type):
        import asyncio
        from fastapi import HTTPException
        try:
            await asyncio.to_thread(check_and_record, data.get("model", ""))
        except QuotaExhausted:
            raise HTTPException(status_code=429, detail="REIDX_QUOTA_EXHAUSTED") from None
        except ValueError:
            raise HTTPException(status_code=503, detail="REIDX_QUOTA_STORAGE_OR_CONFIG_UNAVAILABLE") from None
        return data


budget_guard_instance = BudgetGuard()
