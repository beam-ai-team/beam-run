---
name: mcp
description: Beam MCP — which Model Context Protocol tools the Beam server exposes and when to use them vs the CLI or Public API.
---

# Beam MCP

The Beam MCP server is the operational in-editor surface. Register it through
`beam mcp`, the bundled policy-enforcing stdio proxy. It exposes workspace,
task, and observability operations, while Flow-internal operations stay behind
the Agent Builder skill.

## Tool groups (from Beam docs)

| Group | Examples |
| --- | --- |
| User | `getCurrentUser` |
| Agents | `listAgents`, `downloadContextFile` |
| Tasks | `createAgentTask`, `listAgentTasks`, `getTaskDetails`, `getTaskUpdates` |
| Control | `submitUserInput`, `approveTaskExecution`, `rejectTaskExecution`, `retryTaskExecution` |
| Analytics | `getAgentAnalytics`, `rateTaskOutput`, `optimizeTool`, `getToolOptimizationStatus` |
| Workspace discovery | `listPreferredModels`, `listActiveTools` |
| Agent Views (read-only) | `listAgentViews`, `getAgentView`, `listAgentViewRecords`, `listLinkedAgentViewRecords` |

### Capability boundary

Do not add or call standalone MCP tools for Flow internals: graph/node reads,
node tests, tool schemas, graph mutation, trigger/webhook invocation, prompt or
parameter changes, consent configuration, or publishing. These are dependencies
of the configured agent behavior and must use `beam:agent-builder`.

The proxy blocks `getAgentGraph`, `getTaskNodesByTool`, `getToolOutputSchema`,
`testGraphNode`, `updateGraphNode`, and `startTask`, even if the upstream MCP
server advertises them. Use the Agent Builder CLI for guarded inspection,
testing, and all Flow changes.

Standalone MCP tools qualify only when they operate a workspace or a task from
outside the Flow: discovery, task lifecycle, consent/input at runtime, and
observability. The bundled proxy additionally supplies read-only workspace-tool
discovery and Agent View tools. They do not modify a graph, a view, or any
agent configuration.

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

## Auth note

The local proxy reads credentials when it starts and forwards them to `/mcp`.
After `beam login` or any auth/config change, restart the agent host. See the
`setup` skill.

## Known issues (server-side, being fixed)

These tools currently error at the MCP layer (the server returns a non-object result, or a
DI fault); don't rely on them until the platform fix lands:

| Tool | Symptom | Workaround |
| --- | --- | --- |
| `getCurrentUser` | `structuredContent expected record` | `beam whoami` (CLI) |
| `getTaskDetails` | same, even on a valid taskId | `listAgentTasks` / `getLatestExecutions` |
| `getToolOutputSchema` | same (returns an array) | inspect via `getAgentGraph` |
| `getToolOptimizationStatus` | `UserService not found` (DI) | — |
