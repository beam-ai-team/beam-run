# Beam Run operations — agent-tasks

Generated from `beam/contracts/operations.yaml`. Prefer MCP; on an unavailable or malformed tool, use the mapped CLI command. Reconcile an ambiguous write before retrying.

| Operation | Safety | MCP | CLI fallback | Confirmation | Verify |
| --- | --- | --- | --- | --- | --- |
| task.latest | read | beam_get_latest_task_executions | `beam tasks latest <agentId> [pageSize]` | none | not-required |
| task.get | read | getTaskDetails | `beam tasks get <taskId>` | none | not-required |
| task.create-live | external-effect | createAgentTask | `beam tasks create <agentId> <input>` | required-if-production-side-effect | task.get |
| task.create-draft | reversible-write | null | `beam tasks test <agentId> <input>` | none | task.get |
| task.retry | external-effect | retryTaskExecution | `beam tasks retry <taskId> [--task-node-id <taskNodeId> --feedback <text>]` | required-if-production-side-effect | task.get |
| task.abort | destructive-write | null | `beam tasks abort <taskId> --confirm <taskId> [--reason <text>]` | always | task.get |
| task.delete | destructive-write | null | `beam tasks delete <taskId> --confirm <taskId>` | always | task.list |
| task.rate | reversible-write | rateTaskOutput | `beam tasks rate <taskId> <up|down> [feedback]` | none | not-required |
| task.cancel-wait | destructive-write | task_cancel_wait_node | `beam tasks cancel-wait <taskNodeId> <agentId> --confirm <taskNodeId>` | always | task.get |
