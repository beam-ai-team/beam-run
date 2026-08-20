# Beam Run operations — general-workspace

Generated from `beam/contracts/operations.yaml`. Prefer MCP; on an unavailable or malformed tool, use the mapped CLI command. Reconcile an ambiguous write before retrying.

| Operation | Safety | MCP | CLI fallback | Confirmation | Verify |
| --- | --- | --- | --- | --- | --- |
| user.current | read | getCurrentUser | `beam whoami` | none | not-required |
| agent.list | read | listAgents | `beam agents list` | none | not-required |
