# Beam Run operations — integrations

Generated from `beam/contracts/operations.yaml`. Prefer MCP; on an unavailable or malformed tool, use the mapped CLI command. Reconcile an ambiguous write before retrying.

| Operation | Safety | MCP | CLI fallback | Confirmation | Verify |
| --- | --- | --- | --- | --- | --- |
| integration.list | read | null | `beam integrations list` | none | not-required |
| integration.categories | read | beam_list_integration_categories | `beam integrations categories` | none | not-required |
| integration.connected | read | null | `beam integrations connected` | none | not-required |
| integration.connections | read | null | `beam integrations connections <integrationId>` | none | not-required |
| integration.is-connected | read | beam_is_integration_connected | `beam integrations is-connected <toolFunctionName>` | none | not-required |
| integration.connect | external-effect | null | `beam integrations connect <payloadFile>` | required-if-credentials-or-external-effect | not-required |
| integration.update | reversible-write | integration_update_connection | `beam integrations update <payloadFile>` | none | integration.connections |
| integration.remove | destructive-write | null | `beam integrations remove <providerId> --confirm <providerId>` | always | not-required |
| integration.set-default | reversible-write | null | `beam integrations set-default <providerId> <integrationId>` | none | not-required |
| integration.custom-create | reversible-write | null | `beam integrations custom-create <payloadFile>` | none | not-required |
| integration.custom-update | reversible-write | null | `beam integrations custom-update <id> <payloadFile>` | none | not-required |
| integration.custom-remove | destructive-write | null | `beam integrations custom-remove <id> --confirm <id>` | always | not-required |
