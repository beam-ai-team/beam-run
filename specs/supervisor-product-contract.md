# Beam Run supervisor product contract

## Outcome

A user can complete the same core Beam workspace operation from a coding agent
as from Beam Copilot, with equivalent product instructions and safety, explicit
workspace/entity context, and recovery when the MCP layer is unavailable but
the Beam API remains healthy.

## Invariants

- The existing setup, login, registration, doctor, and signed-out onboarding
  experience remain unchanged.
- The Copilot prompt snapshot is the source for routing, specialist scope,
  tool order, confirmation, and reporting behavior.
- The coding-agent host is the supervisor runtime. Beam Run does not add a
  second LLM, memory service, or Mastra deployment.
- A normal single-domain request is owned by exactly one specialist.
- Independent reads may run in parallel; dependent and write steps stay ordered.
- MCP is attempted first when the required tool is present and healthy.
- Every supported specialist operation has a documented CLI fallback or an
  explicit platform blocker. No skill silently falls out to an improvised call.
- Flow changes remain solely owned by Agent Builder.

## Completion states

Each routed operation ends in one of four states:

1. `completed-mcp` — MCP succeeded and the result was verified where needed.
2. `completed-cli-fallback` — MCP failed at the tool/transport layer and CLI completed it.
3. `awaiting-user` — a required target, value, consent, or destructive confirmation is missing.
4. `blocked-platform` — auth, permission, or Beam API availability prevents both surfaces.

## Initial full-parity modules

Supervisor, general workspace, Agent Builder, agent tasks, global tasks, flow
reader, integrations, agent configuration, analytics, inbox, templates, views,
and Learning Hub.

## Acceptance gates

- Every specialist is mapped in `beam/contracts/copilot-parity.yaml`.
- Every operation is mapped to safety, MCP, fallback, and verification behavior.
- Routing evaluations cover every specialist plus cross-domain and destructive cases.
- Failure injection covers missing tool, malformed result, transport failure,
  auth failure, permission denial, backend failure, and ambiguous write outcome.
- Existing onboarding tests pass without changed expected output.
