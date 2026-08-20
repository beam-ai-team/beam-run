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
host's MCP panel rather than assuming this list is exhaustive. The portable check
is `beam mcp check`; use `beam mcp check --tool <name>` before a specialist relies
on a particular operation.

Workspace-specific tools require an explicit workspace ID. Resolve it from the
user's request or Beam URL first, then `beam workspace`, then a sole membership.
If multiple remain possible, ask once and remember the answer. On empty/not-found
results, name the active workspace and offer a switch; never search every workspace
or change the default without the user's choice.

## MCP vs CLI vs API

| Need | Use |
| --- | --- |
| Interactive agent/task work in chat | MCP |
| Auth check / workspace switch / PATH scripts | CLI (`beam whoami`, `beam workspace`) |
| App or backend integration | Public API |

## Failure policy

MCP is preferred, not a single point of failure. Continue with the operation's
CLI mapping when a tool is absent, the endpoint is unreachable, the result shape
is invalid, or the tool matches a known server defect. Stop for authentication,
permission, validation, or platform-unavailable failures because changing
transport cannot fix them.

For writes whose response is lost or malformed, reconcile with a read before
trying another surface. Never replay a possibly-applied create, delete, publish,
approval, or external action blindly. The full policy is in
`../../../contracts/fallback-policy.yaml`.

## Auth note

The `/mcp` endpoint accepts **`Authorization: Bearer <key>`** (preferred) — and currently
also tolerates `x-api-key`. Use Bearer; `beam register` sets it for you. MCP reads the key
**once at startup**, so after `beam login` or any auth/config change, restart the agent host.
See the `setup` skill.

## Known issues (server-side, being fixed)

These tools currently error at the MCP layer (the server returns a non-object result, or a
DI fault); don't rely on them until the platform fix lands:

| Tool | Symptom | Workaround |
| --- | --- | --- |
| `getCurrentUser` | `structuredContent expected record` | `beam whoami` (CLI) |
| `getTaskDetails` | same, even on a valid taskId | `listAgentTasks` / `getLatestExecutions` |
| `getToolOutputSchema` | same (returns an array) | inspect via `getAgentGraph` |
| `getToolOptimizationStatus` | `UserService not found` (DI) | — |
