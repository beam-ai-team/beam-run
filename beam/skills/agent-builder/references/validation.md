# Validation and diagnosis

Test or diagnose whenever the user asks; never make either a required phase.

## Test a requested scenario

Create only the cases the user asks for. When they ask for broad confidence,
choose representative happy-path, boundary, missing-data, and unusual-input
cases appropriate to the agent. State expected behavior before executing.

Inspect node-level output, selected condition edges, and external-action status;
do not treat a completed task as automatically correct. Present a short verdict
and the relevant node-level cause on failure.

## Fix a failure

Identify the responsible node and use the smallest patch. Show a before/after
diff when the change is material or inferred; apply a direct, unambiguous user
request without an extra confirmation. Re-run the affected scenario, then run
additional cases only when a regression risk justifies it.

## Task APIs

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

`USER_INPUT_REQUIRED` on an integration node usually means its connector needs
authorization. Preserve and report valid upstream node outputs instead of
discarding the whole result.
