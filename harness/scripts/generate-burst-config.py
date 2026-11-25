#!/usr/bin/env python3
"""Generate a LiteLLM profile without local concurrency caps.

Reads the current standard config and writes a second config. The standard
config is never modified. Requires PyYAML from LiteLLM's own uv environment.
"""
from __future__ import annotations
import copy
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:
    raise SystemExit(
        "PyYAML is not available in this interpreter. Run this script using "
        "the Python interpreter from the LiteLLM uv tool environment."
    ) from exc

if len(sys.argv) != 3:
    raise SystemExit(f"Usage: {sys.argv[0]} SAFE_CONFIG BURST_CONFIG")

source = Path(sys.argv[1]).expanduser()
target = Path(sys.argv[2]).expanduser()
if not source.is_file():
    raise SystemExit(f"Safe LiteLLM config not found: {source}")

with source.open("r", encoding="utf-8") as handle:
    data = yaml.safe_load(handle) or {}

burst = copy.deepcopy(data)
removed = []

for deployment in burst.get("model_list", []):
    params = deployment.get("litellm_params", {})
    for key in ("max_parallel_requests",):
        if key in params:
            removed.append(f"{deployment.get('model_name', '<unknown>')}: {key}={params.pop(key)}")

router = burst.get("router_settings", {})
if "default_max_parallel_requests" in router:
    removed.append(
        "router_settings.default_max_parallel_requests="
        f"{router.pop('default_max_parallel_requests')}"
    )

# Remove any explicit proxy-wide concurrency ceiling if one is introduced later.
for section_name in ("general_settings",):
    section = burst.get(section_name, {})
    for key in ("global_max_parallel_requests",):
        if key in section:
            removed.append(f"{section_name}.{key}={section.pop(key)}")

# Preserve retry policy and all other routing, authentication, model and safety settings.
target.parent.mkdir(parents=True, exist_ok=True)
with target.open("w", encoding="utf-8") as handle:
    yaml.safe_dump(burst, handle, sort_keys=False, allow_unicode=True, width=110)

# Verify generated YAML and ensure no local max-parallel cap remains.
with target.open("r", encoding="utf-8") as handle:
    check = yaml.safe_load(handle) or {}
for deployment in check.get("model_list", []):
    params = deployment.get("litellm_params", {})
    if "max_parallel_requests" in params:
        raise SystemExit(f"Unexpected max_parallel_requests remains on {deployment.get('model_name')}")
if check.get("router_settings", {}).get("default_max_parallel_requests") is not None:
    raise SystemExit("Unexpected router_settings.default_max_parallel_requests remains")

print(f"Generated burst config: {target}")
print(f"Model groups preserved: {len(check.get('model_list', []))}")
print("Removed local concurrency caps:")
if removed:
    for item in removed:
        print(f"  - {item}")
else:
    print("  - No explicit max-parallel caps were present in the source config.")
print("Provider-side limits are unchanged and still apply.")
