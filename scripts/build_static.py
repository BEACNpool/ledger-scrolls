#!/usr/bin/env python3
"""Package tracked public project files for a private Sites review.

The GitHub Pages source remains unchanged in structure. Ignored backups, wallet
artifacts, local environments, and test output never enter the static build.
Run after staging new public source files. Never copy the whole working tree.
"""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist"
if OUT.exists():
    # Preserve the previous build; it is small, reversible, and never source.
    import time
    OUT.rename(ROOT / ("dist.previous-" + str(time.time_ns())))
OUT.mkdir()
files = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
count = 0
for name in files:
    if not name or name.startswith((".git", ".openai/", "dist/", "dist.previous-")):
        continue
    src = ROOT / name
    if not src.is_file() or src.is_symlink():
        continue
    if any(part in {"node_modules", "__pycache__", "archive", "tmp", ".venv"} for part in src.relative_to(ROOT).parts):
        raise SystemExit(f"Unexpected private/build path tracked: {name}")
    if src.suffix in {".skey", ".key", ".env", ".pyc"} or ".bak-" in name:
        raise SystemExit(f"Unexpected sensitive or backup path tracked: {name}")
    dest = OUT / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    count += 1
if not (OUT / "index.html").exists():
    raise SystemExit("Missing public entrypoint")
print(f"Static review build: {count} tracked public files -> dist/")
