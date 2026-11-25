#!/usr/bin/env python3
"""Install a ReidX release into a fresh user-owned directory."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import venv


def migrate_runtime(previous, target):
    """Copy durable state from a stopped release, including its SQLite sidecars."""
    for kind in ("data", "state"):
        destination = target / "runtime" / kind / "reidx"
        parent = previous / "runtime" / kind
        current = parent / "reidx"
        legacy = parent / "opencode"
        source = current if current.is_dir() else legacy
        if not source.is_dir():
            continue
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns("log"))
        for filename in destination.glob("opencode-reidx.db*"):
            filename.rename(filename.with_name(filename.name.replace("opencode-", "reidx-", 1)))
    for name in ("memory", "learning"):
        source = previous / name
        if source.is_dir():
            shutil.copytree(source, target / name, dirs_exist_ok=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, default=Path.home() / ".local/share/reidx")
    parser.add_argument("--binary", type=Path, help="Use a binary from a local source build")
    parser.add_argument("--migrate-from", type=Path, help="Copy sessions and memory from a stopped ReidX installation")
    args = parser.parse_args()

    source = Path(__file__).resolve().parent
    target = args.prefix.expanduser().absolute()
    previous = args.migrate_from.expanduser().resolve() if args.migrate_from else None
    if previous and (not (previous / "bin/reidx").is_file() or target.resolve().is_relative_to(previous)):
        parser.error("--migrate-from must name an existing ReidX installation outside the new prefix")
    binary = args.binary or source.parent / "bin/reidx-core"
    if not binary.is_file():
        parser.error("compiled ReidX binary missing; extract the release or pass --binary")
    try:
        target.mkdir(parents=True, mode=0o700)
    except FileExistsError:
        parser.error(f"installation already exists at {target}; choose a fresh prefix")
    try:
        for folder in ("reidx", "config", "memory", "memory-mcp", "scripts", "litellm-plugins"):
            shutil.copytree(source / folder, target / folder, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copy2(source / "setup-reidx.py", target)
        bin_dir = target / "bin"
        bin_dir.mkdir()
        for original, name in ((binary, "reidx-core"), (source / "scripts/reidx-launcher", "reidx")):
            shutil.copy2(original, bin_dir / name)
            (bin_dir / name).chmod(0o755)

        venv.EnvBuilder(with_pip=True).create(target / ".venv")
        python = target / ".venv/bin/python"
        subprocess.run([python, "-m", "pip", "install", "--disable-pip-version-check",
                        "-r", target / "memory-mcp/requirements.txt"], check=True)
        config = json.loads((target / "config/reidx/reidx.json").read_text())
        memory = config["mcp"]["servers"]["memory"]
        memory["command"] = [str(python), str(target / "memory-mcp/server.py")]
        paths = {
            "MEMORY_ROOT": target / "memory",
            "SKILL_INBOX": target / "learning/skill-inbox",
            "SKILLS_ROOT": target / "reidx/skills",
            "AGENTS_ROOT": target / "reidx/agents",
            "COMMANDS_ROOT": target / "reidx/commands",
            "GLOBAL_INSTRUCTIONS_FILE": target / "reidx/AGENTS.md",
        }
        memory["environment"].update({key: str(value) for key, value in paths.items()})
        (target / "reidx/reidx.json").write_text(json.dumps(config, indent=2) + "\n")
        shutil.copytree(target / "config/reidx/themes", target / "reidx/themes")
        shutil.copy2(target / "config/reidx/cli.json", target / "reidx/cli.json")
        if previous:
            migrate_runtime(previous, target)
    except (Exception, KeyboardInterrupt):
        shutil.rmtree(target)
        raise
    print(f"Installed ReidX in {target}")
    print(f"Run {bin_dir / 'reidx'} setup to check the embedding prerequisite.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
