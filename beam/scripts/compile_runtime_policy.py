#!/usr/bin/env python3
"""Compile the frozen Beam Copilot baseline into lean host-neutral runtime cards.

The baseline remains the auditable product source. Runtime hosts read only the
card for the selected domain, never the TypeScript prompt snapshots themselves.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "references" / "copilot-baseline"
RUNTIME = ROOT / "runtime"
PAGES = BASELINE / "pages" / "prompts.ts"

DOMAINS = {
    "general-workspace": ("general-agent/prompt.ts", None, False),
    "agent-builder": ("builder/prompt.ts", None, False),
    "agent-tasks": ("pages/prompts.ts", "AGENT_TASKS_CAPABILITY", True),
    "global-tasks": ("pages/prompts.ts", "TASKS_GLOBAL_CAPABILITY", False),
    "agent-flow": ("pages/prompts.ts", "AGENT_FLOW_CAPABILITY", True),
    "integrations": ("pages/prompts.ts", "INTEGRATIONS_CAPABILITY", False),
    "agent-config": ("pages/prompts.ts", "AGENT_CONFIG_CAPABILITY", True),
    "agent-analytics": ("pages/prompts.ts", "AGENT_ANALYTICS_CAPABILITY", True),
    "inbox": ("pages/prompts.ts", "INBOX_CAPABILITY", False),
    "templates": ("pages/prompts.ts", "TEMPLATES_CAPABILITY", False),
    "views": ("pages/prompts.ts", "VIEWS_CAPABILITY", False),
    "learning-hub": ("pages/prompts.ts", "LEARNING_HUB_CAPABILITY", True),
}

ROUTES = [
    ("general-workspace", "Workspace-wide discovery, broad Beam questions, and unscoped work"),
    ("agent-builder", "Create or change a flow, node, trigger, webhook, or publish state"),
    ("agent-tasks", "One agent's task history, tests, retries, ratings, and task actions"),
    ("global-tasks", "Tasks spanning more than one agent"),
    ("agent-flow", "Read or explain a graph without changing it"),
    ("integrations", "Connections and custom integrations"),
    ("agent-config", "Settings, enabled tools, sub-agents, and context files"),
    ("agent-analytics", "Agent performance and exports"),
    ("inbox", "Notifications, task consent, and requested task input"),
    ("templates", "Template discovery, prerequisites, and creation"),
    ("views", "Saved Views, columns, records, and exports"),
    ("learning-hub", "Learning Hub issues, feedback, jobs, and tuning"),
]

ACTIVITY_INSTRUCTION = (
    "Before a platform operation, write one short user-facing status line that names "
    "the outcome and scope. Group related platform calls under that line rather than "
    "narrating each command. For a read-only operation, say that no changes will be "
    "made. Before a write, test, publish, consent request, or other external-effecting "
    "operation, name the target and intended effect. After the group completes, state "
    "the result; for a change, name the exact entity and resulting state and say what "
    "was verified. Do not narrate internal routing, policy-card or file loading, MCP "
    "checks, CLI fallbacks, or individual commands."
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_backtick_constant(source: str, name: str) -> str:
    marker = f"const {name}"
    start = source.find(marker)
    if start < 0:
        raise ValueError(f"Could not find {name}")
    opening = source.find("`", start)
    if opening < 0:
        raise ValueError(f"Could not find template for {name}")
    cursor = opening + 1
    escaped = False
    while cursor < len(source):
        char = source[cursor]
        if char == "`" and not escaped:
            return source[opening + 1 : cursor]
        if char == "\\" and not escaped:
            escaped = True
        else:
            escaped = False
        cursor += 1
    raise ValueError(f"Unterminated template for {name}")


def clean_template(value: str) -> str:
    replacements = {
        "${ACTIVITY_INSTRUCTION}": ACTIVITY_INSTRUCTION,
        "${PARALLEL_TOOLS_INSTRUCTION}": "Run independent read-only checks concurrently when safe.",
        "${DATETIME_INSTRUCTION}": "Use current time only when the operation requires it.",
        "${ROUTING_TABLE_BLOCK}": "Use the generated runtime route index for routing.",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value.replace("\\`", "`").strip() + "\n"


def parse_operations() -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    current: dict[str, str] | None = None
    for line in (ROOT / "contracts" / "operations.yaml").read_text().splitlines():
        operation = re.match(r"^  ([a-z][a-z0-9.-]+):$", line)
        if operation:
            if current and "specialist" in current:
                grouped.setdefault(current["specialist"], []).append(current)
            current = {"operation": operation.group(1)}
            continue
        field = re.match(r"^    ([A-Za-z][A-Za-z0-9]*):\s*(.*)$", line)
        if field and current is not None:
            current.setdefault(field.group(1), field.group(2))
    if current and "specialist" in current:
        grouped.setdefault(current["specialist"], []).append(current)
    return grouped


def source_commit() -> str:
    readme = (BASELINE / "README.md").read_text()
    match = re.search(r"commit\s+`([0-9a-f]+)`", readme)
    if not match:
        raise ValueError("Baseline commit is missing")
    return match.group(1)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def compile_domain(domain: str, source_file: str, constant: str | None, scoped: bool) -> str:
    source = (BASELINE / source_file).read_text()
    if constant is None:
        if domain == "agent-builder":
            body = """## Builder runtime policy

Use the smallest safe graph change. Keep work as a draft unless the user explicitly
asks to publish. Inspect current nodes before changing a graph; show a compact flow
proposal before a material change; search the tool catalog before adding an
integration; verify links after a change; and obtain explicit approval before any
live external effect. Read the focused builder reference in `internal/agent-builder/`
only when the requested change requires its detailed authoring, integration, trigger,
or validation rules.
"""
        else:
            body = clean_template(extract_backtick_constant(source, "BEAM_AGENT_PROMPT"))
    else:
        body = clean_template(extract_backtick_constant(source, constant))
        if scoped:
            scoped_note = clean_template(extract_backtick_constant(PAGES.read_text(), "AGENT_SCOPED_NOTE"))
            body = scoped_note + "\n" + body
    if "Group related platform calls under that line" not in body:
        body = ACTIVITY_INSTRUCTION + "\n\n" + body
    return (
        f"# Beam Run policy — {domain}\n\n"
        f"Generated from `{source_file}`"
        + (f" (`{constant}`)" if constant else "")
        + ". Do not edit manually; run `python3 beam/scripts/compile_runtime_policy.py`.\n\n"
        + body
    )


def render_operations(domain: str, operations: list[dict[str, str]]) -> str:
    lines = [
        f"# Beam Run operations — {domain}",
        "",
        "Generated from `beam/contracts/operations.yaml`. Prefer MCP; on an unavailable or malformed tool, use the mapped CLI command. Reconcile an ambiguous write before retrying.",
        "",
        "| Operation | Safety | MCP | CLI fallback | Confirmation | Verify |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in operations:
        lines.append(
            "| {operation} | {safety} | {mcp} | `{cli}` | {confirmation} | {postRead} |".format(
                operation=item.get("operation", "—"),
                safety=item.get("safety", "read"),
                mcp=item.get("mcp", "null"),
                cli=item.get("cli", "—"),
                confirmation=item.get("confirmation", "none"),
                postRead=item.get("postRead", "not-required"),
            )
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    pages = PAGES.read_text()
    common = clean_template(extract_backtick_constant(pages, "PAGE_CORE"))
    operations = parse_operations()

    write(
        RUNTIME / "common.md",
        "# Beam Run common policy\n\n"
        "Generated from `pages/prompts.ts#PAGE_CORE`. This is the common policy embedded in every public host skill.\n\n"
        + common,
    )
    route_lines = [
        "# Beam Run route index",
        "",
        "Classify the requested outcome once, then load only that domain card. A graph mutation always routes to `agent-builder`; task execution and runtime consent remain task operations.",
        "",
        "| Domain | Use when | Policy card | Operations card |",
        "| --- | --- | --- | --- |",
    ]
    for domain, purpose in ROUTES:
        route_lines.append(
            f"| `{domain}` | {purpose} | `domains/{domain}.md` | `operations/{domain}.md` |"
        )
    write(RUNTIME / "routes.md", "\n".join(route_lines) + "\n")

    for domain, (source_file, constant, scoped) in DOMAINS.items():
        write(RUNTIME / "domains" / f"{domain}.md", compile_domain(domain, source_file, constant, scoped))
        write(RUNTIME / "operations" / f"{domain}.md", render_operations(domain, operations.get(domain, [])))

    source_files = [
        BASELINE / "supervisor" / "prompt.ts",
        BASELINE / "domain" / "routing-table.ts",
        BASELINE / "general-agent" / "prompt.ts",
        BASELINE / "builder" / "prompt.ts",
        PAGES,
        ROOT / "contracts" / "operations.yaml",
    ]
    generated = sorted(path for path in RUNTIME.rglob("*.md"))
    manifest = {
        "version": 1,
        "baselineCommit": source_commit(),
        "sources": {str(path.relative_to(ROOT)): sha256(path) for path in source_files},
        "generated": {str(path.relative_to(ROOT)): sha256(path) for path in generated},
    }
    write(RUNTIME / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
