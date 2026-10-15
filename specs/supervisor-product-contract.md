# Beam Run agent product contract

## Outcome

A person building agents and wiring integrations from a coding agent can complete
every core Beam workspace operation with explicit safety stops, explicit
workspace/entity context, and recovery when the MCP layer is unavailable but the
Beam API remains healthy. Beam Run serves those builders' needs and deliberately
does not track the in-product Copilot.

## Invariants

- The existing setup, login, registration, doctor, and signed-out onboarding
  experience remain unchanged.
- The agent brief (`beam/skills/beam/SKILL.md`), the playbooks (`beam/playbooks/`)
  and the action list (`beam/contracts/operations.yaml`) are the source for routing,
  steps, confirmation, and reporting behavior.
- The coding-agent host runs the Beam Run agent. Beam Run does not add a
  second LLM, memory service, or Mastra deployment.
- A normal single-situation request follows exactly one playbook; a multi-situation
  request runs playbooks in order with the same context.
- Independent reads may run in parallel; dependent and write steps stay ordered.
- MCP is attempted first when the required tool is present and healthy.
- Every supported action has a documented CLI fallback or an
  explicit platform blocker. No playbook silently falls out to an improvised call.
- Flow changes go only through the change-an-agent's-flow and build-a-new-agent
  playbooks.

## Completion states

Each routed operation ends in one of four states:

1. `completed-mcp` — MCP succeeded and the result was verified where needed.
2. `completed-cli-fallback` — MCP failed at the tool/transport layer and CLI completed it.
3. `awaiting-user` — a required target, value, consent, or destructive confirmation is missing.
4. `blocked-platform` — auth, permission, or Beam API availability prevents both surfaces.

## Playbooks

The 16 playbooks are listed in the agent brief. Together they cover everything the
former Copilot-derived modules covered: general workspace, Agent Builder, agent and
global tasks, flow reader, integrations, agent configuration, analytics, inbox,
templates, Views and Learning Hub.

## Acceptance gates

- Every action is mapped to safety, MCP, fallback, and verification behavior, and is
  used by at least one playbook (`test/playbook-contract.sh`).
- Every action that needs confirmation is a stop point in each playbook that uses it.
- Plan evals (`test/evals/`) cover every playbook plus multi-step, safety-trap and
  non-Beam requests.
- Failure injection covers missing tool, malformed result, transport failure,
  auth failure, permission denial, backend failure, and ambiguous write outcome.
- Existing onboarding tests pass without changed expected output.
