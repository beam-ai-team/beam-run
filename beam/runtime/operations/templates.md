# Beam Run operations — templates

Generated from `beam/contracts/operations.yaml`. Prefer MCP; on an unavailable or malformed tool, use the mapped CLI command. Reconcile an ambiguous write before retrying.

| Operation | Safety | MCP | CLI fallback | Confirmation | Verify |
| --- | --- | --- | --- | --- | --- |
| template.list | read | null | `beam templates list` | none | not-required |
| template.categories | read | beam_list_template_categories | `beam templates categories` | none | not-required |
| template.get | read | null | `beam templates get <templateId>` | none | not-required |
| template.prerequisites | read | beam_get_template_with_prerequisites | `beam templates get <templateId> + beam integrations connected` | none | not-required |
| template.recommend | read | null | `beam templates recommend [categoryId]` | none | not-required |
| template.create-agent | reversible-write | null | `beam templates create-agent <templateId>` | none | agent.get |
