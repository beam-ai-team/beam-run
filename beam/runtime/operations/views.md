# Beam Run operations — views

Generated from `beam/contracts/operations.yaml`. Prefer MCP; on an unavailable or malformed tool, use the mapped CLI command. Reconcile an ambiguous write before retrying.

| Operation | Safety | MCP | CLI fallback | Confirmation | Verify |
| --- | --- | --- | --- | --- | --- |
| view.list | read | null | `beam views list` | none | not-required |
| view.get | read | null | `beam views get <viewId>` | none | not-required |
| view.records | read | null | `beam views records <viewId>` | none | not-required |
| view.export | reversible-write | null | `beam views export <viewId>` | none | not-required |
| view.linked-records | read | beam_list_linked_records | `beam views linked-records <viewId> <columnId> <numericRecordId>` | none | not-required |
| view.create | reversible-write | view_create | `beam views create <payloadFile>` | none | not-required |
| view.delete | destructive-write | view_delete | `beam views delete <viewId> --confirm <viewId>` | always | view.list |
| view.add-column | reversible-write | view_create_column | `beam views add-column <viewId> <payloadFile>` | none | view.get |
| view.update-column | reversible-write | view_update_column | `beam views update-column <viewId> <columnId> <fullPayloadFile>` | none | view.get |
| view.delete-column | destructive-write | view_delete_column | `beam views delete-column <viewId> <columnId> --confirm <columnId>` | always | view.get |
