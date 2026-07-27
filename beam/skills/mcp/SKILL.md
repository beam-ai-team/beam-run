---
name: mcp
description: Beam MCP — which Model Context Protocol tools the Beam server exposes and when to use them vs the CLI or Public API.
---

# Beam MCP

The Beam MCP server is the primary in-editor surface. **Preferred: register it as a
direct HTTP MCP server** (`type: http`, url `https://api.beamstudio.ai/mcp`) — no local
proxy, no Node/uv. Where the host only supports stdio, the plugin bridges via `beam mcp`.

## Tool groups (from Beam docs)

| Group | Examples |
| --- | --- |
| User | `getCurrentUser` |
| Agents | `listAgents`, `downloadContextFile` |
| Graphs | `getAgentGraph`, `testGraphNode`, `getTaskNodesByTool` |
| Tasks | `createAgentTask`, `listAgentTasks`, `getTaskDetails`, `getTaskUpdates` |
| Control | `submitUserInput`, `approveTaskExecution`, `rejectTaskExecution`, `retryTaskExecution` |
| Analytics | `getAgentAnalytics`, `rateTaskOutput`, `optimizeTool`, `getToolOptimizationStatus` |

Exact tool names depend on the server version — discover what's connected in the
host's MCP panel rather than assuming this list is exhaustive.

## MCP vs CLI vs API

| Need | Use |
| --- | --- |
| Interactive agent/task work in chat | MCP |
| Auth check / workspace switch / PATH scripts | CLI (`beam whoami`, `beam workspace`) |
| App or backend integration | Public API |

## Auth note

The `/mcp` endpoint authenticates with **`Authorization: Bearer <key>`** — NOT `x-api-key`
(that's the REST API header). MCP reads the key **once at startup**; after `beam login` or
any auth/config change, restart the agent host. See the `setup` skill.

## Known issues (server-side, being fixed)

These tools currently error at the MCP layer (the server returns a non-object result, or a
DI fault); don't rely on them until the platform fix lands:

| Tool | Symptom | Workaround |
| --- | --- | --- |
| `getCurrentUser` | `structuredContent expected record` | `beam whoami` (CLI) |
| `getTaskDetails` | same, even on a valid taskId | `listAgentTasks` / `getLatestExecutions` |
| `getToolOutputSchema` | same (returns an array) | inspect via `getAgentGraph` |
| `getToolOptimizationStatus` | `UserService not found` (DI) | — |
