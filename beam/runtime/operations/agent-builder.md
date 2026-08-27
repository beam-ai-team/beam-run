# Beam Run operations — agent-builder

Generated from `beam/contracts/operations.yaml`. Prefer MCP; on an unavailable or malformed tool, use the mapped CLI command. Reconcile an ambiguous write before retrying.

| Operation | Safety | MCP | CLI fallback | Confirmation | Verify |
| --- | --- | --- | --- | --- | --- |
| graph.deploy | reversible-write | null | `beam agent-builder deploy <specFile>` | none | graph.readiness |
| graph.publish | external-effect | null | `beam agent-builder publish <graphId> --agent-id <agentId>` | explicit-publish-intent | graph.get |
| graph.update-prompt | reversible-write | null | `beam agent-builder update-node-prompt <agentId> <nodeId> <promptFile>` | none | graph.readiness |
| graph.update-params | reversible-write | null | `beam agent-builder update-node-params <agentId> <nodeId> ...` | none | graph.readiness |
| graph.update-consent | reversible-write | null | `beam agent-builder update-node-consent <agentId> <nodeId> <true|false>` | none | graph.readiness |
| graph.add-node | reversible-write | null | `beam agent-builder add-node <agentId> <nodeFile> ...` | none | graph.readiness |
| graph.remove-node | destructive-write | null | `beam agent-builder remove-node <agentId> <nodeId>` | explicit | graph.readiness |
| graph.test-node | reversible-write | testGraphNode | `beam agent-builder test-node <agentId> <graphId> <nodeId> <paramsJson>` | none | not-required |
