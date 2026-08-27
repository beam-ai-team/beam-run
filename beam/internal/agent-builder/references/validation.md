# Validation and diagnosis

Test or diagnose whenever the user asks; never make either a required phase.

## Draft readiness after every change

`verify-links` only checks linked parameter IDs. After every graph mutation,
the builder also runs the deterministic `readiness` evaluation and includes it
in the command result. It checks the fields and contracts that make a graph
safe to publish: objectives, edges, tool configuration, parameter names/types
and values, Custom GPT prompt structure and declared variables, and active MCP
tool attachments.

```bash
beam agent-builder readiness AGENT_ID
```

Treat `ready: false` as a draft defect to fix before task testing or publishing.
The CLI will save an incomplete draft so it can be repaired, but it blocks every
publish path until the report passes. This is intentionally separate from a
node's `evaluationCriteria`, which evaluates model response quality rather than
schema and graph correctness.

## Test a requested scenario

Create only the cases the user asks for. When they ask for broad confidence,
choose representative happy-path, boundary, missing-data, and unusual-input
cases appropriate to the agent. State expected behavior before executing.

### Select the graph deliberately

Read the active and draft graph IDs before creating a test task.

- If the user explicitly asks to test the draft, use `beam tasks test AGENT_ID
  "input"`. It selects the draft with `isDraftTask: true`.
- If the user explicitly asks to run the live agent, use the ordinary task
  creation path.
- Infer the target when context is sufficient: a test after relevant unpublished
  draft work uses the draft; an explicit live/production request or normal run
  without relevant draft context uses live. Do not ask merely because a draft
  exists. Ask only when the evidence genuinely conflicts or cannot identify the
  intended unpublished change.
- Create and inspect one case before creating a batch. Confirm the returned
  `agentGraphId` equals the selected active or draft graph; stop on a mismatch.

The MCP `createAgentTask` tool does not expose draft selection, so it must never
be used for a draft test. A test task can still reach real integrations; respect
consent and do not approve an external action without the user's explicit consent.

Inspect node-level output, selected condition edges, and external-action status;
do not treat a completed task as automatically correct. Present a short verdict
and the relevant node-level cause on failure.

## Fix a failure

Identify the responsible node and use the smallest patch. Show a before/after
diff when the change is material or inferred; apply a direct, unambiguous user
request without an extra confirmation. Re-run the affected scenario, then run
additional cases only when a regression risk justifies it.

## Live task API

```bash
curl -X POST "$BEAM_API_URL/agent-tasks" \
  -H "x-api-key: $BEAM_API_KEY" \
  -H "current-workspace-id: $BEAM_WORKSPACE_ID" \
  -H "Content-Type: application/json" \
  -d '{"agentId": "<id>", "input": "<task input text>"}'

curl "$BEAM_API_URL/agent-tasks/<taskId>" \
  -H "x-api-key: $BEAM_API_KEY" \
  -H "current-workspace-id: $BEAM_WORKSPACE_ID"
```

## Draft test API

Prefer the CLI, which selects the draft graph correctly:

```bash
beam tasks test AGENT_ID "<task input text>"
```

The API equivalent must include `isDraftTask: true`:

```bash
curl -X POST "$BEAM_API_URL/agent-tasks" \
  -H "x-api-key: $BEAM_API_KEY" \
  -H "current-workspace-id: $BEAM_WORKSPACE_ID" \
  -H "Content-Type: application/json" \
  -d '{"agentId":"<id>","taskQuery":{"query":"<task input text>"},"isDraftTask":true}'
```

`USER_INPUT_REQUIRED` on an integration node usually means its connector needs
authorization. Preserve and report valid upstream node outputs instead of
discarding the whole result.
