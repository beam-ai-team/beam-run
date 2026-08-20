---
name: global-tasks
description: Beam workspace-wide task specialist — search and operate tasks across agents after resolving the target agent and task.
---

# Beam global tasks specialist

Canonical source: `../../../references/copilot-baseline/pages/prompts.ts`, constants
`PAGE_CORE` and `TASKS_GLOBAL_CAPABILITY`. Read it and
`../../../references/host-adapter.md` completely before acting.

This specialist has no preselected agent. Resolve the requested agent or task
from explicit context or bounded searches, then use the same task operation
rules as `agent-tasks`. Never scan or switch all workspaces silently.

Use `task.*` operations in `../../../contracts/operations.yaml`. MCP is first and
the mapped `beam tasks ...` command is mandatory on recoverable MCP failure.
Preserve draft/test filtering, confirmation, exact statuses, and post-write reads.
