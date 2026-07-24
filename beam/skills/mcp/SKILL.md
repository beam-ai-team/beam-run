---
name: mcp
description: Beam MCP — which Model Context Protocol tools the Beam server exposes and when to use them vs the CLI or Public API.
---

# Beam MCP

The Beam MCP server is the primary in-editor surface. The plugin launches it via
`beam mcp` (stdio proxy to `https://api.beamstudio.ai/mcp` using the stored API key).

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

MCP reads the API key **once at startup**. After `beam login`, restart the agent
host or the MCP server won't see the new credentials. See the `setup` skill.
