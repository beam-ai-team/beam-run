# Test a draft

## When to use

- "Test it with this email", "try the new prompt on these three examples",
  "does step 3 work with this input?"
- Right after building or changing a draft, or whenever the user wants a trial run
  that does not touch the live version.
- Not for real runs: use `run-an-agent.md`.

## What you need first

- The agent and both graph ids from `agent.get`: `draftGraphId` and `activeGraphId`.
- Which one to test. A test that follows unpublished draft work in this
  conversation uses the draft. An explicit "live" or "production" request uses the
  live path instead. Ask only when the evidence genuinely conflicts.
- The test input, or a set of realistic inputs if the user asked for general
  validation.

## Steps

1. Read `agent.get` to confirm a draft exists.
2. For one step in isolation, run `graph.test-node` with explicit inputs.
3. For the whole flow, run `task.create-draft` with the first input.
4. Read it with `task.get` and check its `agentGraphId` is the draft before
   sending any further inputs.
5. For each run, compare what happened with what the user expected, step by step:
   outputs, the branch taken, and any pause.

## Stop and ask

- A draft test can still reach real integrations. If a step sends, posts or writes
  outside Beam, it will pause for consent if consent is switched on; otherwise warn
  the user before running and get their OK.

## Done when

- Each test run is reported with its task id, status, and a plain verdict:
  did it do what was expected, and if not, at which step.

## If it goes wrong

- The first run landed on the live graph: stop, report it, and do not send more.
- A step's output is wrong: name the step and the likely cause, then offer
  `change-an-agents-flow.md` with the smallest fix.
- A run pauses for input or consent: use `clear-whats-waiting-on-me.md`, and only
  with made-up test values the user agrees to.
- Detailed diagnosis guides: `../internal/agent-builder/references/validation.md`
  and `../internal/agent-builder/references/troubleshooting.md`.

## Actions

Generated from `../contracts/operations.yaml`; do not edit by hand. Run each
action through its MCP tool, or its CLI command when MCP is unavailable (always
the CLI in Codex). Re-read with the re-check action after a change.

| Action | MCP tool | CLI | Needs OK | Re-check | Notes |
| --- | --- | --- | --- | --- | --- |
| `agent.get` | `getAgentGraph` | `beam agents get <agentId>` | no | — | Shows activeGraphId (live) and draftGraphId (unpublished). Report the model token exactly as returned. createdAt is the default start date for analytics. |
| `graph.test-node` | `testGraphNode` | `beam agent-builder test-node <agentId> <graphId> <nodeId> <paramsJson>` | no | — | Runs one step with explicit inputs; needs agentId, graphId, nodeId and a JSON params object. |
| `task.create-draft` | — | `beam tasks test <agentId> <input>` | no | `task.get` | Runs the unpublished draft. For a batch, check the first task's agentGraphId before sending the rest. |
| `task.get` | `getTaskDetails` | `beam tasks get <taskId>` | no | — | Fields are at the top level. agentTaskNodes[] holds each step's status; USER_CONSENT_REQUIRED and USER_INPUT_REQUIRED mark a paused step and carry its taskNodeId; the agent id is agentGraph.agentId. |
