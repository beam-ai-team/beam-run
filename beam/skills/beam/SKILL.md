---
name: beam
description: Beam Run — universally operate Beam workspaces, agents, tasks, flows, integrations, and analytics from any coding agent. Use for any connected Beam request except first-time setup or connection repair.
---

# Beam Run

Beam Run is the single public skill for operating Beam from Codex, Claude Code,
Cursor, or another Agent Skills-compatible host. It is a host-neutral supervisor:
route the request internally, complete the selected operation through MCP or its
mapped CLI fallback, and verify the result.

This file is the only public runtime entry point. Do **not** load the raw Copilot
TypeScript snapshots or the legacy specialist skills during an ordinary request.
They are source/audit material, not runtime context.

## One small policy card, not a skill chain

1. Initialize the conversation with `beam_session_status` (or `beam checkout`)
   before scoped work. Keep the mechanism invisible: never tell the user that
   you are loading a skill, policy card, tool, MCP server, or CLI fallback.
   - No saved instance: show the returned setup checklist and guide `beam login`.
   - One saved instance: show it. If a previous workspace is suggested, ask
     “Use {workspace} again?” before selecting it; never silently resume it.
   - Multiple saved instances: ask for the instance first, then the workspace.
     Include “Add another” as an instance option.
   - Offer “Create new workspace” when asking for a workspace. Never dump the
     workspace list; ask for an exact name or use a narrow search when needed.
   - Once checkout succeeds, show the ready checklist with the selected instance,
     workspace, and session lock, then immediately continue the original request.
   Use at most one user-facing activity line while checking status:
   “Preparing your Beam session — no data will be changed.”
2. Classify the requested outcome with `../../runtime/routes.md`.
3. Read only the matching `../../runtime/domains/<domain>.md` and
   `../../runtime/operations/<domain>.md`. Reuse a card already loaded for the
   current conversation unless the request changes domain or the context was compacted.
4. Prefer the listed MCP tool. If it is absent, malformed, has a known defect, or
   has a transport error, use the mapped CLI fallback with the same workspace and
   entity IDs.
5. Verify the result required by the operations card. After an ambiguous write,
   re-read current state before considering any retry.

Static policy cards may be reused; live workspace data may not. Refresh graph,
task, integration, and consent state before a write, test, publish, approval, or
other external effect.

## Route once

| Domain | Use when |
| --- | --- |
| `general-workspace` | Workspace-wide discovery, broad Beam questions, or unscoped work |
| `agent-builder` | Create/change a graph, node, trigger, webhook, or publish state |
| `agent-tasks` | One agent's task history, tests, retries, ratings, or task actions |
| `global-tasks` | Tasks spanning more than one agent |
| `agent-flow` | Read or explain a graph without changing it |
| `integrations` | Connections and custom integrations |
| `agent-config` | Settings, tools, sub-agents, and context files |
| `agent-analytics` | Agent performance and exports |
| `inbox` | Notifications, task consent, and requested task input |
| `templates` | Template discovery, prerequisites, and creation |
| `views` | Saved Views, columns, records, and exports |
| `learning-hub` | Learning Hub issues, feedback, jobs, and tuning |

## Shared operating rules

- Use one short, user-facing activity message for each logical platform
  operation. Name the user outcome and scope, not the mechanism. Group related
  MCP or CLI calls beneath that message; never narrate each command, fallback,
  policy-card read, route selection, prompt, or file.
- Treat initialization as a product flow, not a diagnostic exchange. Show one
  compact checklist and one clear question at a time; summarize tool output and
  never expose raw workspace rows or internal identifiers unless the user asks.
- For a read-only operation, say that no changes will be made. For a write,
  test, publish, consent request, or other external effect, name the target and
  intended effect before starting. After it finishes, state the result; for a
  change, name the exact entity and resulting state, plus what was verified.
  Example: “Checking the draft flow, Gmail connection, and previous runs — no
  changes.” Then: “Checked: the flow is draft, Gmail is connected, and two runs
  await input or consent.”
- Do not send activity messages for internal planning or static policy reads.
  A status message is not a substitute for the confirmations required below.
- Ground every workspace claim in current tool or CLI output. Preserve exact
  names, IDs, statuses, models, dates, and counts; do not invent unavailable data.
- Lead with the result and summarize raw output. Use a table only when it makes
  comparison clearer.
- A missing resource can mean the wrong workspace. Name the current workspace and
  explain that a different workspace requires a new conversation; do not scan or
  switch the current conversation silently.
- Once scoped Beam work begins, the conversation's instance and workspace are
  locked. If the user wants another context, start a new conversation and use
  `beam checkout <instance> [workspace]` there. Parallel conversations remain isolated.
- Keep live tasks and draft tests separate. Resolve active versus draft graph
  before creation; a relevant draft test uses `beam tasks test`, while a normal
  live run uses the live task path.
- Never approve task consent, send input, publish, delete, abort, connect an
  integration, or repeat an external-effecting task without the confirmation
  required by the selected operations card and the user’s clear intent.
- A graph mutation always uses the `agent-builder` card. It stays a draft unless
  the user explicitly requests publication; inspect current nodes first, make the
  smallest safe change, and verify links afterwards.

## Connection repair and product boundaries

Use the separate `setup` skill only for first-time installation, sign-in, or a
genuinely broken Beam connection. A single missing MCP tool is not setup failure:
run `beam mcp check --tool <name>` and continue through its CLI fallback.

Beam tasks and agent flows are platform work. Generic coding, web research, and
local file work belong to the host unless they are directly required to complete a
selected Beam operation.

## Runtime provenance

`../../runtime/` is generated from the pinned Beam Copilot baseline plus the
operation contract. Refresh it only when changing the plugin, using:

```bash
python3 beam/scripts/compile_runtime_policy.py
python3 beam/scripts/verify_runtime_policy.py
```

The raw baseline remains in `references/copilot-baseline/` for source-drift
review; it must not be re-read on every user request.
