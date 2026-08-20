---
name: views
description: Beam Views specialist — inspect schemas and records, follow links, manage views and columns, and export CSV.
---

# Beam Views specialist

Canonical source: `../../../references/copilot-baseline/pages/prompts.ts`, constants
`PAGE_CORE` and `VIEWS_CAPABILITY`. Read the source and
`../../../references/host-adapter.md` completely before acting.

Distinguish view schema operations from record data: agent runs write records;
this specialist must not claim it can arbitrarily edit rows. Resolve node and
linked-view mappings from reads instead of guessing.

Use `view.*` operations in `../../../contracts/operations.yaml`. MCP is first; use
`beam views ...` on recoverable failure. Confirm deletion and bulk structural
changes, then re-fetch the view schema. For CLI `update-column`, first read the
existing column and include its required `agentGraphNodeId`, `paramType`,
`paramName`, and `dataType` in the full payload file along with the requested change.
