---
name: agents
description: Beam agents — list, inspect, build/deploy, publish, and delete agents in the workspace. Use when the user asks about their agents, agent configuration or graph structure, or wants to create, update, publish, or remove an agent.
---

# Beam agents

Prefer **MCP tools** when available; fall back to the CLI/API.

## List agents

- MCP: `listAgents`
- CLI: `beam agents list` (requires workspace set via `beam whoami` / `beam workspace`)

Summarize as a short table: name, type, id. Don't dump full JSON unless asked.

## Inspect a graph

- MCP: `getAgentGraph` (and related graph tools)
- Confirm which agent by **name** with the user if multiple match.

When describing a graph, lead with: trigger → main path → branches → exit/consent nodes.
Keep node ids available for follow-up edits/tests, but don't lead with them.

## Context files

- MCP: `downloadContextFile` when the user needs agent knowledge files locally.

## Build or update an agent

For anything beyond inspection — creating a new agent, changing its node graph,
attaching integrations, wiring triggers — use the **agent-builder** skill. It
drives the full design → spec → deploy flow and owns the graph-payload details.

Once a spec exists, the CLI deploys it (draft by default):

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
beam agents delete <agentId>    # remove an agent (irreversible)
```

- `publish` takes the `graphId` from `deploy` output (x-api-key auth).
- `delete` is **irreversible** — confirm the agent name with the user first.
  The delete route is JWT-gated, so the CLI mints a short-lived token from the
  API key automatically (`/auth/access-token`); no extra credentials needed.

## Auth / workspace

If tools fail with auth or empty lists:

```bash
beam whoami; echo "exit_code=$?"
beam workspace   # show current
```

Wrong workspace → `beam workspace <id>`. Missing auth → run `setup`.
