# Beam Run host adapter

This adapter changes execution mechanics only. Product-domain behavior comes
from the corresponding Copilot prompt snapshot.

## Context

Beam Run has no guaranteed in-product page context. Resolve the normalized
context in `beam/contracts/context.yaml` from the explicit request, a Beam URL,
the remembered workspace, or a focused lookup. Never invent an id or silently
switch workspaces.

## Delegation

The coding-agent host is the supervisor runtime. Loading a specialist skill is
the equivalent of the Copilot supervisor delegating to a Mastra sub-agent. The
specialist owns the assigned operation until it completes, awaits user input,
or reports a terminal platform blocker.

## Transport

Use the operation registry in `beam/contracts/operations.yaml`.

1. Prefer the mapped MCP tool when it is present and healthy.
2. On a missing tool, protocol/shape error, known defect, or MCP transport
   failure, run the mapped CLI fallback with the same resolved context.
3. Do not call setup merely because one MCP tool is unavailable when CLI auth works.
4. If a write has an ambiguous outcome, reconcile current state before retrying.
5. Preserve all confirmation requirements when changing surfaces.

## Tool output

Ground Beam workspace claims in tool or CLI output. Preserve exact ids,
statuses, enum tokens, counts, dates, and names. Say when a field is missing;
never fill it from memory.

## User interaction

Use the host's native question/confirmation mechanism. Ask only when a required
target, value, graph mode, consent, or destructive confirmation cannot be
resolved from context.

## Navigation

Preserve useful `beam://` deep links from Copilot output when the host renders
them. Navigation is optional: lack of a Beam page does not prevent an operation
that MCP or CLI can complete.
