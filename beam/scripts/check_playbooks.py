#!/usr/bin/env python3
"""Check that the Beam Run agent brief, playbooks and action list agree.

- every playbook has the six sections, in order, and stays short;
- the brief lists exactly the playbooks on disk;
- every action a playbook names exists in contracts/operations.yaml;
- every action in operations.yaml is used by at least one playbook;
- every action that needs confirmation, used in a playbook's Steps, is named
  under that playbook's "Stop and ask";
- every file a playbook points to exists;
- every playbook ends with an up-to-date table of the actions it names, so the
  agent never has to read the full action list. Regenerate the tables with
  `python3 beam/scripts/check_playbooks.py --write`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOKS = ROOT / "playbooks"
BRIEF = ROOT / "skills" / "beam" / "SKILL.md"
OPERATIONS = ROOT / "contracts" / "operations.yaml"

SECTIONS = ["When to use", "What you need first", "Steps", "Stop and ask", "Done when", "If it goes wrong"]
MAX_LINES = 100
ACTION = re.compile(r"`([a-z]+\.[a-z][a-z0-9-]*)`")
FILE_REF = re.compile(r"`((?:\.\./)?[A-Za-z0-9_./-]+\.(?:md|json))`")
TABLE_HEADING = "## Actions"


def load_operations() -> dict[str, dict[str, str]]:
    ops: dict[str, dict[str, str]] = {}
    current = None
    for line in OPERATIONS.read_text().splitlines():
        m = re.match(r"^  ([a-z][a-z0-9.-]+):$", line)
        if m:
            current = ops.setdefault(m.group(1), {})
            continue
        f = re.match(r"^    ([A-Za-z]+):\s*(.*)$", line)
        if f and current is not None:
            current[f.group(1)] = f.group(2)
    return ops


def sections(text: str) -> dict[str, str]:
    parts = re.split(r"^## (.+)$", text, flags=re.M)
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts), 2)}


def actions_in(text: str) -> set[str]:
    return {a for a in ACTION.findall(text) if not a.endswith(".md")}


def action_table(actions: set[str], ops: dict[str, dict[str, str]]) -> str:
    def cell(value: str) -> str:
        return value.strip().strip('"').replace("|", "\\|")
    rows = [
        TABLE_HEADING,
        "",
        "Generated from `../contracts/operations.yaml`; do not edit by hand. Run each",
        "action through its MCP tool, or its CLI command when MCP is unavailable (always",
        "the CLI in Codex). Re-read with the re-check action after a change.",
        "",
        "| Action | MCP tool | CLI | Needs OK | Re-check | Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for action in sorted(actions):
        f = ops[action]
        mcp = f.get("mcp", "null")
        rows.append("| `{}` | {} | `{}` | {} | {} | {} |".format(
            action,
            "—" if mcp == "null" else f"`{cell(mcp)}`",
            cell(f.get("cli", "")),
            "no" if f.get("confirmation", "none") == "none" else cell(f["confirmation"]),
            f"`{f['postRead']}`" if f.get("postRead") else "—",
            cell(f.get("notes", "")) or "—",
        ))
    return "\n".join(rows) + "\n"


def main() -> int:
    errors: list[str] = []
    ops = load_operations()
    write = "--write" in sys.argv

    for op, fields in ops.items():
        for key in ("safety", "cli", "status"):
            if key not in fields:
                errors.append(f"operations.yaml: {op} has no {key}")
        if fields.get("status") != "ready":
            errors.append(f"operations.yaml: {op} is not ready")
        if "specialist" in fields:
            errors.append(f"operations.yaml: {op} still names a screen specialist")

    files = sorted(PLAYBOOKS.glob("*.md"))
    on_disk = {p.name for p in files}
    listed = set(re.findall(r"`([a-z0-9-]+\.md)`", BRIEF.read_text()))
    for name in sorted(on_disk - listed):
        errors.append(f"brief does not list playbook {name}")
    for name in sorted(listed - on_disk):
        errors.append(f"brief lists a missing playbook {name}")

    used: set[str] = set()
    for path in files:
        full = path.read_text()
        text, _, table = full.partition("\n" + TABLE_HEADING + "\n")
        text = text.rstrip("\n") + "\n"
        name = path.name
        if not text.startswith("# "):
            errors.append(f"{name}: no title")
        headings = re.findall(r"^## (.+)$", text, flags=re.M)
        if headings != SECTIONS:
            errors.append(f"{name}: sections are {headings}, expected {SECTIONS}")
        if len(text.splitlines()) > MAX_LINES:
            errors.append(f"{name}: longer than {MAX_LINES} lines")

        named = actions_in(text)
        used |= named
        for action in sorted(named - ops.keys()):
            errors.append(f"{name}: names unknown action {action}")
        expected = text + "\n" + action_table(named & ops.keys(), ops)
        if write:
            path.write_text(expected)
        elif full != expected:
            errors.append(f"{name}: action table is missing or out of date; run check_playbooks.py --write")

        parts = sections(text)
        stop = actions_in(parts.get("Stop and ask", ""))
        for action in sorted(actions_in(parts.get("Steps", ""))):
            confirmation = ops.get(action, {}).get("confirmation", "none")
            if confirmation != "none" and action not in stop:
                errors.append(f"{name}: {action} needs confirmation ({confirmation}) but is not under Stop and ask")

        for ref in FILE_REF.findall(text):
            target = (PLAYBOOKS / ref).resolve() if "/" in ref else PLAYBOOKS / ref
            if not target.exists():
                errors.append(f"{name}: points to missing file {ref}")

    for action in sorted(ops.keys() - used):
        errors.append(f"operations.yaml: {action} is not used by any playbook")

    if errors:
        print("\n".join(f"FAIL: {e}" for e in errors), file=sys.stderr)
        return 1
    print(f"{len(files)} playbooks cover all {len(ops)} actions; every confirmation is a stop point.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
