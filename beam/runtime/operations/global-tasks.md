# Beam Run operations — global-tasks

Generated from `beam/contracts/operations.yaml`. Prefer MCP; on an unavailable or malformed tool, use the mapped CLI command. Reconcile an ambiguous write before retrying.

| Operation | Safety | MCP | CLI fallback | Confirmation | Verify |
| --- | --- | --- | --- | --- | --- |
| task.list | read | listAgentTasks | `beam tasks list` | none | not-required |
| task.statuses | read | beam_get_task_statuses | `beam tasks statuses [agentIds]` | none | not-required |
| task.agents | read | beam_list_task_agents | `beam tasks agents` | none | not-required |
