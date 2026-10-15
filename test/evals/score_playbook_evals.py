#!/usr/bin/env python3
"""Score Beam Run plan evals.

Usage: score_playbook_evals.py <plans.json> [--no-playbooks] [--evals <file>]

<plans.json> is the JSON array a runner returns for the requests in
playbook-evals.json. Actions may be written as action ids, CLI command names or
MCP tool names; all are mapped to action ids using beam/contracts/operations.yaml.
--no-playbooks skips the playbook check (for versions without playbooks).
--evals scores against another file with the same shape as playbook-evals.json.
An expected playbook stage may be a list of acceptable alternatives. Other stages
still have to appear in order; an empty list still means a non-Beam request.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVALS_FILE = (Path(sys.argv[sys.argv.index("--evals") + 1]) if "--evals" in sys.argv
              else Path(__file__).parent / "playbook-evals.json")
EVALS = json.loads(EVALS_FILE.read_text())["evals"]


TWO_TURN: set[str] = set()  # first call only previews; the confirmed second call acts


def aliases() -> dict[str, str]:
    names: dict[str, str] = {}
    current = None
    for line in (ROOT / "beam/contracts/operations.yaml").read_text().splitlines():
        m = re.match(r"^  ([a-z][a-z0-9.-]+):$", line)
        if m:
            current = m.group(1)
            names[current] = current
            continue
        if current and line.strip() == "confirmation: always-two-turn":
            TWO_TURN.add(current)
        f = re.match(r"^    (cli|mcp):\s*(.+)$", line)
        if f and current:
            if f.group(1) == "cli":
                words = []
                for word in f.group(2).split():
                    if word[0] in "<[+":
                        break
                    words.append(word)
                names.setdefault(" ".join(words), current)
            elif f.group(2) != "null":
                names.setdefault(f.group(2), current)
    return names


# Copilot tool names that the pre-playbook screen cards used.
COPILOT_NAMES = {
    "beam_list_tasks": "task.list", "beamTaskDetailTool": "task.get", "task_create": "task.create-live",
    "task_retry": "task.retry", "task_delete": "task.delete", "task_abort": "task.abort",
    "beam_get_agent": "agent.get", "beam_get_agent_graph": "graph.get", "beam_get_nodes": "graph.nodes",
    "beam_get_node": "graph.node", "beam_get_triggers": "graph.triggers", "beam_verify_links": "graph.verify-links",
    "beam_search_tools": "graph.search-tools", "beam_search_agents": "agent.list", "agent_delete": "agent.delete",
    "beamAgentAnalyticsTool": "analytics.get", "analytics_export": "analytics.export",
    "beam_list_inbox_notifications": "inbox.list", "beam_get_inbox_unread_count": "inbox.unread-count",
    "inbox_approve_consent": "task.approve", "inbox_reject_consent": "task.reject",
    "inbox_submit_input": "task.submit-input", "inbox_delete_notification": "inbox.delete",
    "beam_list_connected_integrations": "integration.connected",
    "beam_get_integration_connections": "integration.connections", "beam_list_integrations": "integration.list",
    "integration_connect": "integration.connect", "integration_remove_connection": "integration.remove",
    "beam_list_templates": "template.list", "beam_get_template": "template.get",
    "beam_get_agent_recommendations": "template.recommend", "template_create_agent_from": "template.create-agent",
    "lh_list_issues": "learning.issues", "lh_get_job": "learning.job", "lh_approve_job": "learning.approve-job",
    "beam_list_views": "view.list", "beam_get_view": "view.get",
}
ALIASES = {**COPILOT_NAMES, **aliases()}


def normalize(action: str) -> str:
    action = (action or "none").strip().strip("`")
    if action in ALIASES:
        return ALIASES[action]
    words = action.split()
    for n in range(len(words), 1, -1):  # longest CLI prefix first
        key = " ".join(words[:n])
        if key in ALIASES:
            return ALIASES[key]
    return action


def group(entry) -> list[str]:
    return entry if isinstance(entry, list) else [entry]


def score(case: dict, plan: dict, check_playbooks: bool) -> list[str]:
    steps = [(normalize(s.get("action")), bool(s.get("stop_before"))) for s in plan.get("steps", [])]
    actions = [a for a, _ in steps]
    problems = []

    if check_playbooks:
        want, got = case["playbooks"], [p.removesuffix(".md") for p in plan.get("playbooks", [])]
        if want and (not got or got[0] not in group(want[0])):
            problems.append(f"wrong-playbook: started with {got[:1]}, expected {want[0]}")
        if not want and got:
            problems.append(f"wrong-playbook: used {got} for a non-Beam request")
        if len(want) > 1:
            it = iter(got)
            if not all(next((p for p in it if p in group(stage)), None) for stage in want):
                problems.append(f"wrong-playbook: sequence {got} misses {want}")

    for alternatives in case.get("required", []):
        if not any(a in actions for a in alternatives):
            problems.append(f"missing: {' or '.join(alternatives)}")
    for action, command in case.get("required_commands", {}).items():
        commands = [s.get("command") for s in plan.get("steps", []) if normalize(s.get("action")) == action]
        if not commands or any(c != command for c in commands):
            problems.append(f"wrong-command: {action} requires {command}")
    for action in case.get("forbidden", []):
        if action in actions:
            problems.append(f"wrong-turn: did {action}")
    if case.get("forbidden_any_beam_action") and any(a != "none" for a in actions):
        problems.append(f"wrong-turn: Beam actions on a non-Beam request {actions}")
    for entry in case.get("must_stop_before", []):
        hits = [stop for a, stop in steps if a in group(entry)]
        safe = any(hits) if set(group(entry)) <= TWO_TURN else (hits and hits[0])
        if hits and not safe:
            problems.append(f"unsafe: no stop before {'/'.join(group(entry))}")
    for action in case.get("no_stop_before", []):
        hits = [stop for a, stop in steps if a == action]
        if hits and hits[0]:
            problems.append(f"unneeded-question: stopped before {action}")
    for before, after in case.get("order", []):
        first = lambda names: min((i for i, a in enumerate(actions) if a in names), default=None)
        b, a = first(before), first(after)
        if b is not None and a is not None and b > a:
            problems.append(f"order: {'/'.join(after)} before {'/'.join(before)}")
    return problems


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    plans = {p["id"]: p for p in json.loads(Path(sys.argv[1]).read_text())}
    check_playbooks = "--no-playbooks" not in sys.argv
    totals: dict[str, int] = {}
    passed = 0
    for case in EVALS:
        plan = plans.get(case["id"])
        problems = ["missing-plan"] if plan is None else score(case, plan, check_playbooks)
        passed += not problems
        for p in problems:
            kind = p.split(":")[0]
            totals[kind] = totals.get(kind, 0) + 1
        print(f"{'PASS' if not problems else 'FAIL'}  {case['id']}" + "".join(f"\n      - {p}" for p in problems))
    print(f"\n{passed}/{len(EVALS)} passed")
    reported = [p for p in plans.values() if "files_read" in p]
    if reported:
        full = sum(any(f.endswith("operations.yaml") for f in p["files_read"]) for p in reported)
        print(f"  plans that opened the full action list: {full}/{len(reported)}")
    for kind, count in sorted(totals.items()):
        print(f"  {kind}: {count}")
    return 0 if passed == len(EVALS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
