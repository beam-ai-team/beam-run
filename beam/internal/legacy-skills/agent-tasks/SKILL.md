---
name: agent-tasks
description: One Beam agent's task and test specialist — list, inspect, create, retry, abort, delete, rate, and operate runs for an already-resolved agent.
---

# Beam agent tasks specialist

Canonical source: `../../../references/copilot-baseline/pages/prompts.ts`, constants
`PAGE_CORE`, `AGENT_SCOPED_NOTE`, and `AGENT_TASKS_CAPABILITY`. Read the source
and `../../../references/host-adapter.md` completely before acting.

Resolve one agent first. Keep real tasks (`isDraftTask:false`) separate from
tests (`isDraftTask:true`). For “this task” use an explicit task id; otherwise
list and resolve the concrete task before reading or acting.

Use the `task.*` operations in `../../../contracts/operations.yaml`. MCP is first;
execute the mapped `beam tasks ...` command on a recoverable MCP failure. Always
confirm delete and abort. Confirm retry/create when the run can repeat external
side effects. Re-read the task after every write or ambiguous outcome.

Graph edits discovered while investigating a task are handed to `agent-builder`.
