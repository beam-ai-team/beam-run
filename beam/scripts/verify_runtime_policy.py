#!/usr/bin/env python3
"""Verify that runtime policy cards are reproducible from the pinned baseline."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    before = {path.relative_to(RUNTIME): digest(path) for path in RUNTIME.rglob("*") if path.is_file()}
    subprocess.run([sys.executable, str(ROOT / "scripts" / "compile_runtime_policy.py")], check=True)
    after = {path.relative_to(RUNTIME): digest(path) for path in RUNTIME.rglob("*") if path.is_file()}
    if before != after:
        print("FAIL: runtime policy is not current; rerun compile_runtime_policy.py", file=sys.stderr)
        return 1
    manifest = json.loads((RUNTIME / "manifest.json").read_text())
    if manifest.get("baselineCommit") != "40fdd5687a7a4e9122c27d8b175235107c096a58":
        print("FAIL: unexpected Copilot baseline commit", file=sys.stderr)
        return 1
    required = {"common.md", "routes.md", "manifest.json"}
    if not required.issubset({path.name for path in RUNTIME.iterdir()}):
        print("FAIL: runtime policy core is incomplete", file=sys.stderr)
        return 1
    print("Runtime policy cards are reproducible and pinned to the Beam Copilot baseline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
