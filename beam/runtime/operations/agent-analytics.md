# Beam Run operations — agent-analytics

Generated from `beam/contracts/operations.yaml`. Follow the host transport selected during initialization: Codex uses the task-scoped CLI; other hosts prefer MCP and fall back to the mapped CLI command. Reconcile an ambiguous write before retrying.

| Operation | Safety | MCP | CLI fallback | Confirmation | Verify |
| --- | --- | --- | --- | --- | --- |
| analytics.get | read | getAgentAnalytics | `beam analytics get <agentId> [startDate] [endDate]` | none | not-required |
| analytics.export | reversible-write | null | `beam analytics export <agentId> <startDate> <endDate>` | none | not-required |
