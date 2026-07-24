---
name: agents
description: Beam agents — list agents in the workspace, inspect workflow graphs, and download context files. Use when the user asks about their agents, agent configuration, or graph structure.
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

## Auth / workspace

If tools fail with auth or empty lists:

```bash
beam whoami; echo "exit_code=$?"
beam workspace   # show current
```

Wrong workspace → `beam workspace <id>`. Missing auth → run `setup`.
