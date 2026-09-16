# Beam Run operations — general-workspace

Generated from `beam/contracts/operations.yaml`. Follow the host transport selected during initialization: Codex uses the task-scoped CLI; other hosts prefer MCP and fall back to the mapped CLI command. Reconcile an ambiguous write before retrying.

| Operation | Safety | MCP | CLI fallback | Confirmation | Verify |
| --- | --- | --- | --- | --- | --- |
| user.current | read | getCurrentUser | `beam whoami` | none | not-required |
| workspace.create | external-effect | null | `beam workspace create <name> [--domain domain] [--icon-src url]` | explicit-workspace-create-intent | user.current |
| agent.list | read | listAgents | `beam agents list` | none | not-required |
