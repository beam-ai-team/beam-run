---
name: tasks
description: Beam tasks — create agent tasks, monitor progress, submit user input, and approve or reject consent steps. Use when running or operating Beam agent work from the coding agent.
---

# Beam tasks

Prefer **MCP tools** for interactive task operations.

Before the first call, resolve the workspace from an explicit request/URL, then
`beam workspace`, then a sole membership. If multiple remain and no context decides,
ask the user once and remember the answer with `beam workspace <id>`. Pass that ID to every MCP tool.
If an agent/task is missing or a list is empty, name the current workspace and ask
whether the user wants to switch with `beam workspace list <search>` and
`beam workspace <id>`. Never scan or switch all workspaces silently.

## Create

- MCP: `createAgentTask`
- When the user has clearly named the agent and supplied the input, treat that as
  authorization to create the task; do not ask them to repeat it. Ask only when
  the agent or input is ambiguous, or when the task can immediately cause an
  external side effect that was not clearly authorized.
- Return the task id and a one-line status, plus a link/path if the tool provides one.

## Monitor

- MCP: `listAgentTasks`, `getTaskDetails`, `getTaskUpdates`
- Narrate status changes; don't stream raw SSE payloads to the user.

## Human-in-the-loop

When a task pauses for consent or input:

- MCP: `submitUserInput`, `approveTaskExecution`, `rejectTaskExecution`
- **Always** get explicit user approval before approving a consent step.
- For reject, confirm reason/intent with the user first.

## Retry / rate

- MCP: `retryTaskExecution`, `rateTaskOutput` when the user asks to retry or give feedback.

## Safety

Creating and approving tasks can trigger real side effects (email, CRM, tickets).
State the side-effect risk in one sentence and obtain clear natural-language
authorization when the action touches production systems.
