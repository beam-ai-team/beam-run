# Beam Run operations — agent-analytics

Generated from `beam/contracts/operations.yaml`. Prefer MCP; on an unavailable or malformed tool, use the mapped CLI command. Reconcile an ambiguous write before retrying.

| Operation | Safety | MCP | CLI fallback | Confirmation | Verify |
| --- | --- | --- | --- | --- | --- |
| analytics.get | read | getAgentAnalytics | `beam analytics get <agentId> [startDate] [endDate]` | none | not-required |
| analytics.export | reversible-write | null | `beam analytics export <agentId> <startDate> <endDate>` | none | not-required |
