# Beam Run operations — inbox

Generated from `beam/contracts/operations.yaml`. Prefer MCP; on an unavailable or malformed tool, use the mapped CLI command. Reconcile an ambiguous write before retrying.

| Operation | Safety | MCP | CLI fallback | Confirmation | Verify |
| --- | --- | --- | --- | --- | --- |
| task.submit-input | reversible-write | submitUserInput | `beam tasks submit-input <taskId> <taskNodeId> <parameter> <answer>` | confirm-proposed-values | task.get |
| task.approve | external-effect | approveTaskExecution | `beam tasks approve <taskId> <taskNodeId> --confirm <taskNodeId>` | always | task.get |
| task.reject | destructive-write | rejectTaskExecution | `beam tasks reject <taskId> <taskNodeId> --confirm <taskNodeId> [--reason <text>]` | always | task.get |
| inbox.list | read | null | `beam inbox list` | none | not-required |
| inbox.unread-count | read | null | `beam inbox unread-count` | none | not-required |
| inbox.mark-read | reversible-write | null | `beam inbox mark-read <notificationId>` | none | not-required |
| inbox.delete | destructive-write | null | `beam inbox delete <notificationId> --confirm <notificationId>` | always | not-required |
