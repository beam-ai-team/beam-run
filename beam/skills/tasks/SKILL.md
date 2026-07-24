---
name: tasks
description: Beam tasks — create agent tasks, monitor progress, submit user input, and approve or reject consent steps. Use when running or operating Beam agent work from the coding agent.
---

# Beam tasks

Prefer **MCP tools** for interactive task operations.

## Create

- MCP: `createAgentTask`
- Confirm the **agent** (by name) and the **input** with the user before creating.
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
State the side-effect risk in one sentence and wait for go-ahead when the action
touches production systems.
