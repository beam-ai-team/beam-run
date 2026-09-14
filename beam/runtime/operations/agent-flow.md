# Beam Run operations — agent-flow

Generated from `beam/contracts/operations.yaml`. Prefer MCP; on an unavailable or malformed tool, use the mapped CLI command. Reconcile an ambiguous write before retrying.

| Operation | Safety | MCP | CLI fallback | Confirmation | Verify |
| --- | --- | --- | --- | --- | --- |
| graph.get | read | getAgentGraph | `beam agent-builder get-graph <agentId>` | none | not-required |
| graph.nodes | read | getAgentGraph | `beam agent-builder get-nodes <agentId>` | none | not-required |
| graph.node | read | getAgentGraph | `beam agent-builder get-node <agentId> <nodeId>` | none | not-required |
| graph.verify-links | read | getAgentGraph | `beam agent-builder verify-links <agentId>` | none | not-required |
| graph.triggers | read | getAgentGraph | `beam agent-builder get-triggers <agentId> <entryNodeId>` | none | not-required |
| graph.webhook | read | getAgentGraph | `beam agent-builder get-webhook <agentId>` | none | not-required |
