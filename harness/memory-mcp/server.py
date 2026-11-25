#!/usr/bin/env python3
"""Local ReidX memory MCP backed by SQLite FTS5 and local Nomic embeddings."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# Memory files and the SQLite database can contain private operational context.
# Apply a restrictive umask before creating any files or SQLite sidecars.
os.umask(0o077)

APP_NAME = "reidx-memory"
MEMORY_ROOT = Path(os.environ.get("MEMORY_ROOT", str(Path.home() / ".local/share/reidx/memory"))).expanduser().resolve()
SKILL_INBOX = Path(os.environ.get("SKILL_INBOX", str(Path.home() / ".local/share/reidx/learning/skill-inbox"))).expanduser().resolve()
SKILLS_ROOT = Path(os.environ.get("SKILLS_ROOT", str(Path.home() / ".config/reidx/skills"))).expanduser().resolve()
AGENTS_ROOT = Path(os.environ.get("AGENTS_ROOT", str(Path.home() / ".config/reidx/agents"))).expanduser().resolve()
COMMANDS_ROOT = Path(os.environ.get("COMMANDS_ROOT", str(Path.home() / ".config/reidx/commands"))).expanduser().resolve()
GLOBAL_INSTRUCTIONS_FILE = Path(os.environ.get("GLOBAL_INSTRUCTIONS_FILE", str(Path.home() / ".config/reidx/AGENTS.md"))).expanduser().resolve()
DB_PATH = MEMORY_ROOT / "memory.sqlite3"
API_BASE = os.environ.get("LITELLM_API_BASE", "http://127.0.0.1:4000/v1").rstrip("/")
API_KEY = os.environ.get("LITELLM_API_KEY", "")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed")
CHUNK_CHARS = 2600
OVERLAP_CHARS = 250
ALLOWED_CATEGORIES = {"architecture", "decision", "lesson", "workflow", "writing", "preference", "reference"}
ALLOWED_INDEX_CATEGORIES = ALLOWED_CATEGORIES | {"skill", "agent", "command"}
ALLOWED_SUFFIXES = {".md", ".txt", ".rst"}

mcp = FastMCP(APP_NAME)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    MEMORY_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        MEMORY_ROOT.chmod(0o700)
    except OSError:
        pass
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        tags TEXT NOT NULL DEFAULT '',
        embedding TEXT,
        content_hash TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(source, chunk_index)
    )""")
    conn.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
        source UNINDEXED, title, category, tags, content, tokenize='unicode61'
    )""")
    conn.commit()
    try:
        DB_PATH.chmod(0o600)
    except OSError:
        pass
    return conn


def split_text(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) > CHUNK_CHARS:
            if current:
                chunks.append(current)
                current = ""
            start = 0
            while start < len(paragraph):
                end = min(len(paragraph), start + CHUNK_CHARS)
                chunks.append(paragraph[start:end])
                if end == len(paragraph):
                    break
                start = max(0, end - OVERLAP_CHARS)
            continue
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= CHUNK_CHARS:
            current = candidate
        else:
            chunks.append(current)
            current = paragraph
    if current:
        chunks.append(current)
    return chunks


def embed(texts: list[str], task_prefix: str) -> list[list[float]]:
    if not API_KEY:
        raise RuntimeError("LITELLM_API_KEY is empty. Launch ReidX with reidx launch.")
    payload = json.dumps({
        "model": EMBEDDING_MODEL,
        "input": [f"{task_prefix}: {text}" for text in texts],
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{API_BASE}/embeddings",
        data=payload,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"LiteLLM embeddings returned HTTP {exc.code}; response omitted") from None
    except Exception:
        raise RuntimeError("Could not reach LiteLLM embeddings endpoint; transport details omitted") from None

    data = sorted(body.get("data", []), key=lambda item: item.get("index", 0))
    vectors = [item.get("embedding") for item in data]
    if len(vectors) != len(texts) or any(not isinstance(vector, list) or not vector for vector in vectors):
        raise RuntimeError(f"Unexpected embeddings response for model {EMBEDDING_MODEL}")
    return vectors


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return -1.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else -1.0


def index_content(source: str, title: str, category: str, content: str, tags: str = "") -> dict[str, Any]:
    chunks = split_text(content)
    if not chunks:
        return {"indexed": 0, "source": source, "message": "No text to index."}

    hashes = [hashlib.sha256(chunk.encode("utf-8")).hexdigest() for chunk in chunks]
    conn = connect()
    try:
        existing = conn.execute(
            "SELECT chunk_index, content_hash, title, category, tags, embedding FROM chunks WHERE source = ? ORDER BY chunk_index",
            (source,),
        ).fetchall()
        unchanged = (
            len(existing) == len(chunks)
            and all(
                row["chunk_index"] == index
                and row["content_hash"] == hashes[index]
                and row["title"] == title
                and row["category"] == category
                and row["tags"] == tags
                and row["embedding"] is not None
                for index, row in enumerate(existing)
            )
        )
        if unchanged:
            return {"indexed": 0, "unchanged": True, "source": source, "category": category}
    finally:
        conn.close()

    embedding_error = None
    try:
        vectors = embed(chunks, "search_document")
    except Exception as exc:
        # Keep lexical retrieval usable even when the local embedding model or
        # LiteLLM embeddings endpoint is unavailable. A later reindex retries.
        vectors = [None] * len(chunks)
        embedding_error = str(exc)[:600]

    conn = connect()
    try:
        conn.execute("DELETE FROM chunks WHERE source = ?", (source,))
        conn.execute("DELETE FROM chunks_fts WHERE source = ?", (source,))
        for index, (chunk, vector, digest) in enumerate(zip(chunks, vectors, hashes)):
            conn.execute(
                "INSERT INTO chunks(source,title,category,chunk_index,content,tags,embedding,content_hash,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (source, title, category, index, chunk, tags, json.dumps(vector) if vector is not None else None, digest, now_iso()),
            )
            conn.execute(
                "INSERT INTO chunks_fts(source,title,category,tags,content) VALUES(?,?,?,?,?)",
                (source, title, category, tags, chunk),
            )
        conn.commit()
    finally:
        conn.close()
    result = {"indexed": len(chunks), "unchanged": False, "source": source, "category": category}
    if embedding_error:
        result["embedding_warning"] = embedding_error
        result["retrieval_mode"] = "keyword-only until embeddings recover"
    return result


def index_roots() -> list[Path]:
    return [MEMORY_ROOT, SKILLS_ROOT, AGENTS_ROOT, COMMANDS_ROOT]


def allowed_source(path: Path) -> bool:
    try:
        resolved = path.expanduser().resolve(strict=True)
    except FileNotFoundError:
        return False
    for root in index_roots():
        try:
            resolved.relative_to(root)
            return resolved.is_file() and resolved.suffix.lower() in ALLOWED_SUFFIXES
        except ValueError:
            continue
    return resolved == GLOBAL_INSTRUCTIONS_FILE and resolved.is_file() and resolved.suffix.lower() in ALLOWED_SUFFIXES


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug or len(slug) > 64 or "--" in slug:
        raise ValueError("Name must produce a 1-64 character lowercase kebab-case slug.")
    return slug


@mcp.tool()
def memory_search(query: str, top_k: int = 5, category: str = "") -> str:
    """Search saved decisions, lessons, workflows, writing preferences and active skills."""
    if not query.strip():
        raise ValueError("query must not be empty")
    top_k = max(1, min(int(top_k), 10))
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM chunks" + (" WHERE category = ?" if category else ""),
            (category,) if category else (),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return "Memory is empty for this search. Use memory_remember or memory_reindex to add knowledge."

    semantic_error = None
    try:
        query_vector = embed([query], "search_query")[0]
        scored = []
        for row in rows:
            if not row["embedding"]:
                continue
            score = cosine(query_vector, json.loads(row["embedding"]))
            if score >= 0:
                scored.append((score, row))
        scored.sort(key=lambda item: item[0], reverse=True)
        if scored:
            results = [{
                "score": round(score, 4), "title": row["title"], "category": row["category"],
                "source": row["source"], "chunk": row["content"],
            } for score, row in scored[:top_k]]
            return json.dumps({"method": "semantic", "query": query, "results": results}, ensure_ascii=False, indent=2)
        semantic_error = "No stored embeddings are available yet."
    except Exception as exc:
        semantic_error = str(exc)[:600]

    # Keyword fallback always searches the FTS index, which is maintained even
    # if Nomic or the embeddings API was unavailable during indexing.
    tokens = re.findall(r"[A-Za-z0-9_]+", query)
    if not tokens:
        return json.dumps({"method": "unavailable", "query": query, "results": [],
                           "semantic_error": semantic_error}, ensure_ascii=False, indent=2)
    match = " OR ".join(f'"{token}"' for token in tokens[:12])
    conn = connect()
    try:
        sql = ("SELECT source,title,category,content,bm25(chunks_fts) AS rank "
               "FROM chunks_fts WHERE chunks_fts MATCH ?")
        params: list[Any] = [match]
        if category:
            sql += " AND category = ?"
            params.append(category)
        sql += " ORDER BY rank LIMIT ?"
        params.append(top_k)
        fts_rows = conn.execute(sql, params).fetchall()
    except sqlite3.Error as exc:
        fts_rows = []
        semantic_error = f"{semantic_error}; keyword search error: {exc}"
    finally:
        conn.close()

    results = [{
        "score": None, "title": row["title"], "category": row["category"],
        "source": row["source"], "chunk": row["content"],
    } for row in fts_rows]
    return json.dumps({"method": "keyword_fallback", "query": query, "results": results,
                       "semantic_warning": semantic_error}, ensure_ascii=False, indent=2)


@mcp.tool()
def memory_remember(title: str, content: str, category: str = "lesson", tags: str = "", task_id: str = "") -> str:
    """Save a durable, non-sensitive memory note and immediately index it for retrieval."""
    if category not in ALLOWED_CATEGORIES:
        raise ValueError(f"category must be one of: {', '.join(sorted(ALLOWED_CATEGORIES))}")
    if len(content.strip()) < 40:
        raise ValueError("Memory content is too short; save a useful, contextual note rather than a fragment.")
    if not title.strip():
        raise ValueError("title must not be empty")
    folder = MEMORY_ROOT / "entries" / category
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    slug = safe_slug(title)
    path = folder / f"{stamp}-{slug}.md"
    task_value = task_id.strip() or "not-specified"
    note = (
        f"# {title.strip()}\n\n- Date: {now_iso()}\n- Category: {category}\n"
        f"- Task: {task_value}\n- Tags: {tags.strip()}\n\n{content.strip()}\n"
    )
    path.write_text(note, encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    result = index_content(str(path.resolve()), title.strip(), category, note, tags)
    return json.dumps({"saved": True, "path": str(path), **result}, ensure_ascii=False)


@mcp.tool()
def memory_index_file(path: str, category: str = "reference", tags: str = "") -> str:
    """Index one text/Markdown file under memory, skills, agents, commands or global AGENTS.md."""
    if category not in ALLOWED_INDEX_CATEGORIES:
        raise ValueError(f"category must be one of: {', '.join(sorted(ALLOWED_INDEX_CATEGORIES))}")
    candidate = Path(path).expanduser()
    if not allowed_source(candidate):
        raise ValueError("Path is not allowed. Use files under the configured memory, skills, agents or commands directories, or the global AGENTS.md file.")
    resolved = candidate.resolve()
    content = resolved.read_text(encoding="utf-8", errors="replace")
    title = resolved.stem.replace("-", " ").replace("_", " ").title()
    result = index_content(str(resolved), title, category, content, tags)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def memory_reindex() -> str:
    """Index changed memory, skill, agent, command and global-instruction files; remove stale file entries."""
    sources: list[Path] = []
    for base in index_roots():
        if base.exists():
            sources.extend(
                path for path in base.rglob("*")
                if path.is_file() and path.suffix.lower() in ALLOWED_SUFFIXES
            )
    if GLOBAL_INSTRUCTIONS_FILE.is_file():
        sources.append(GLOBAL_INSTRUCTIONS_FILE)
    # Recheck resolved paths: a symlink inside a root must not index outside it.
    sources = sorted({path.resolve() for path in sources if allowed_source(path)})
    active_sources = {str(path) for path in sources}

    conn = connect()
    try:
        existing = [row[0] for row in conn.execute("SELECT DISTINCT source FROM chunks").fetchall()]
        for old_source in existing:
            if old_source not in active_sources:
                conn.execute("DELETE FROM chunks WHERE source = ?", (old_source,))
                conn.execute("DELETE FROM chunks_fts WHERE source = ?", (old_source,))
        conn.commit()
    finally:
        conn.close()

    indexed = 0
    unchanged = 0
    failures: list[str] = []
    embedding_warnings: list[str] = []
    for path in sources:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            if path == GLOBAL_INSTRUCTIONS_FILE:
                category = "reference"
            elif SKILLS_ROOT in path.parents:
                category = "skill"
            elif AGENTS_ROOT in path.parents:
                category = "agent"
            elif COMMANDS_ROOT in path.parents:
                category = "command"
            else:
                # Preserve the category recorded in memory/entries/<category>/.
                # Also give the seeded memory index files useful categories.
                try:
                    relative_memory_path = path.relative_to(MEMORY_ROOT)
                except ValueError:
                    relative_memory_path = Path()
                parts = relative_memory_path.parts
                if len(parts) >= 2 and parts[0] == "entries" and parts[1] in ALLOWED_CATEGORIES:
                    category = parts[1]
                else:
                    seed_categories = {
                        "architecture": "architecture",
                        "decisions": "decision",
                        "lessons": "lesson",
                        "workflows": "workflow",
                        "writing-style": "writing",
                    }
                    category = seed_categories.get(path.stem, "reference")
            title = path.stem.replace("-", " ").replace("_", " ").title()
            result = index_content(str(path), title, category, content)
            if result.get("unchanged"):
                unchanged += 1
            else:
                indexed += result.get("indexed", 0)
            if result.get("embedding_warning"):
                embedding_warnings.append(f"{path}: {result['embedding_warning']}")
        except Exception as exc:
            failures.append(f"{path}: {exc}")
    return json.dumps({
        "files_seen": len(sources), "chunks_indexed": indexed, "files_unchanged": unchanged,
        "failures": failures[:10], "embedding_warnings": embedding_warnings[:10],
        "database": str(DB_PATH),
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def memory_propose_skill(name: str, description: str, body: str, evidence: str) -> str:
    """Create an inactive SKILL.md draft in the review inbox; never activates or overwrites skills."""
    slug = safe_slug(name)
    if not description.strip() or not body.strip() or not evidence.strip():
        raise ValueError("description, body and evidence are required")
    SKILL_INBOX.mkdir(parents=True, exist_ok=True, mode=0o700)
    target_dir = SKILL_INBOX / slug
    target_dir.mkdir(parents=False, exist_ok=False, mode=0o700)
    content = (
        f"---\nname: {slug}\ndescription: {json.dumps(description.strip(), ensure_ascii=False)}\n---\n\n"
        f"{body.strip()}\n\n## Evidence and provenance\n\n{evidence.strip()}\n"
    )
    target = target_dir / "SKILL.md"
    target.write_text(content, encoding="utf-8")
    try:
        target.chmod(0o600)
    except OSError:
        pass
    return json.dumps({"draft_created": True, "path": str(target), "active": False, "approval_required": True}, ensure_ascii=False)


@mcp.tool()
def memory_recent(limit: int = 10) -> str:
    """List recently updated memory source files and categories."""
    limit = max(1, min(int(limit), 25))
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT source, MAX(updated_at) AS updated_at, MAX(title) AS title, MAX(category) AS category "
            "FROM chunks GROUP BY source ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return json.dumps([dict(row) for row in rows], ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # FastMCP uses stdout for protocol frames; never print diagnostic messages to stdout.
    mcp.run(transport="stdio")
