# Beam Run operations — general-workspace

Generated from `beam/contracts/operations.yaml`. Prefer MCP; on an unavailable or malformed tool, use the mapped CLI command. Reconcile an ambiguous write before retrying.

| Operation | Safety | MCP | CLI fallback | Confirmation | Verify |
| --- | --- | --- | --- | --- | --- |
| user.current | read | getCurrentUser | `beam whoami` | none | not-required |
| workspace.create | external-effect | null | `beam workspace create <name> [--domain domain] [--icon-src url]` | explicit-workspace-create-intent | user.current |
| agent.list | read | listAgents | `beam agents list` | none | not-required |
