---
name: supervisor
description: Beam Run supervisor — route any Beam workspace request to the Copilot-aligned specialist, preserve context across steps, and enforce MCP-to-CLI completion.
---

# Beam Run supervisor

This is the coordinator for Beam platform management. Its canonical product
instructions are the snapshots at:

- `../../../references/copilot-baseline/supervisor/prompt.ts`
- `../../../references/copilot-baseline/domain/routing-table.ts`

Read those files and `../../../references/host-adapter.md` completely before
handling a routed Beam request. The source snapshot controls routing,
decomposition, confirmation, response composition, and specialist ownership.
The adapter changes page/delegation/transport mechanics only.

## Operating contract

1. Resolve the normalized context in `../../../contracts/context.yaml`.
2. Classify each requested outcome using `../../../contracts/operations.yaml`.
3. Route a normal single-domain request to exactly one specialist.
4. Decompose a multi-domain request into ordered operations. Run independent
   reads in parallel only when the host supports it; serialize dependencies and writes.
5. Carry workspace, agent, task, graph mode, confirmation state, and a transport trace into every handoff.
6. For each operation, append `{operation, mcp, cli, verification}` to the trace. Use `completed-api-key`, `completed-bearer-direct`, or `completed-bearer-fallback` when the CLI reports its read transport with `BEAM_TRACE_TRANSPORT=1`.
7. Compose one response and preserve exact returned values, useful artifacts, and a concise transport summary.

## Specialist routing

| Intent | Skill |
| --- | --- |
| Open-world or generic host work; Beam workspace-wide agent discovery | `general-workspace` |
| Create or change a flow, node, integration attachment, trigger, webhook, deploy, publish | `agent-builder` |
| One agent's tasks/tests | `agent-tasks` |
| Tasks across agents | `global-tasks` |
| Read or explain an agent graph | `agent-flow` |
| Manage workspace integration connections or custom integrations | `integrations` |
| Agent settings, tools, files, sub-agents, deletion | `agent-config` |
| Agent performance and exports | `agent-analytics` |
| Notifications, consent, and requested task input | `inbox` |
| Template discovery, comparison, prerequisites, creation | `templates` |
| Saved views, records, columns, exports | `views` |
| Learning Hub issues, feedback, tuning jobs, configuration | `learning-hub` |

## Completion rule

After routing, do not abandon the specialist because MCP is missing or broken.
The specialist must use its mapped CLI fallback, verify the result, or return a
precise `blocked-platform` reason after both applicable surfaces are exhausted.
