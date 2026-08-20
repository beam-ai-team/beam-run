---
name: agents
description: Beam agents — list, inspect, publish, and delete agents in the workspace. For every flow, graph, node, trigger, integration, or configuration change, load and follow the agent-builder skill instead of acting from this skill.
---

# Beam agents

This is a compatibility entry point. Load `supervisor` first: it routes discovery
to `general-workspace`, graph reading to `agent-flow`, settings to `agent-config`,
analytics to `agent-analytics`, and every flow mutation to `agent-builder`.

Prefer **MCP tools** when available; fall back to the CLI/API.

## List agents

- MCP: `listAgents`
- CLI: `beam agents list` (requires workspace set via `beam whoami` / `beam workspace`)

When the MCP tool is unavailable in the current host, use the CLI before offering
setup. Missing MCP tools alone do **not** mean that Beam is disconnected: the
host loads its MCP tools at startup, while an already-signed-in CLI can still
list the user's agents.

If `beam` is not on the current shell's PATH, resolve and invoke the bundled
`bin/beam` launcher (using the setup skill's launcher fallback) and retry
`agents list`. Do **not** run `beam setup` solely because `beam` was not found
on PATH. Run setup only when the CLI reports missing or invalid authentication,
or when no usable launcher can be found.

Tell the user to fully restart the host only after they sign in or change the
MCP configuration. A new task by itself does not require a restart.

Summarize as a short table: name, type, id. Don't dump full JSON unless asked.

## Inspect a graph

- MCP: `getAgentGraph` (and related graph tools)
- Confirm which agent by **name** with the user if multiple match.

When describing a graph, lead with: trigger → main path → branches → exit/consent nodes.
Keep node ids available for follow-up edits/tests, but don't lead with them.

## Context files

- MCP: `downloadContextFile` when the user needs agent knowledge files locally.

## Flow changes: mandatory handoff

For **any** flow mutation — creating a new agent flow, changing a node or edge,
editing a prompt or parameter, altering an integration or trigger, changing tool
configuration or consent, deploying a graph, or publishing a graph — stop here
and load the **agent-builder** skill first. This is mandatory, including for
small setting changes. Do not make the change using generic graph MCP tools,
`beam agents deploy`, or raw API requests from this skill.

`agent-builder` owns the complete graph contract and its dependency rules. It
chooses the smallest safe patch, preserves graph relationships, verifies the
result, and keeps the graph as a draft unless the user explicitly asks to publish.

The commands below are reference-only after `agent-builder` has selected them;
they are not authorization to bypass that skill.

Once `agent-builder` has prepared a spec, the CLI deploys it (draft by default):

```bash
beam agents deploy spec.json                 # create a new agent (DRAFT)
beam agents deploy spec.json --agent-id ID   # update an existing agent
beam agents deploy spec.json --publish       # create + go live
```

`deploy` needs `python3` (the bundled graph builder) and posts to
`/agent-graphs/complete` with the API key. It prints `agentId` and `graphId`.
**Publishing is a separate, explicit step** — a plain `deploy` leaves a draft;
only publish when the user says "publish" / "make it live".

## Publish / delete

```bash
beam agents publish <graphId>   # promote a draft graph to live
beam agents delete <agentId> --confirm <agentId>  # remove an agent (irreversible)
```

- `publish` takes the `graphId` from `deploy` output (x-api-key auth).
- `delete` is **irreversible**. Before deleting, call `beam agents get <agentId>`,
  show the user the resolved agent name and id, and obtain explicit approval. Then
  repeat the exact id in `--confirm`; the CLI rejects unconfirmed or mismatched
  requests. The delete route is JWT-gated, so the CLI mints a short-lived token
  from the API key automatically (`/auth/access-token`); no extra credentials needed.

## Auth / workspace

If tools fail with auth or empty lists:

```bash
beam whoami; echo "exit_code=$?"
beam workspace   # show current
```

Resolve workspace from the request/Beam URL, a valid remembered default, or a sole
membership. If multiple remain possible, ask once and remember with
`beam workspace <id>`. Missing auth → run `setup`. If a list is empty or an agent is
not found, name the current workspace and ask whether the user wants to create it
there or switch. Never search all workspaces automatically.
