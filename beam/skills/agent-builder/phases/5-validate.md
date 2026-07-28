# Phase 5 — Validate

> **On entry:** display the phase timeline from `references/ux-flow.md` — Phase 5 row (`✅ Intake  ──  ✅ Design  ──  ✅ Review  ──  ✅ Build  ──  ● Validate  ──  ○ Iterate`).

**Goal:** prove the deployed agent produces correct outputs on representative inputs — not just that it runs without error.

**Exit criteria:** 5 test scenarios run and scored against expected outcomes. Failures attributed to specific nodes. Learning feedback submitted. A verdict reached.

---

## Step 1 — Generate 5 test scenarios (before running)

Generate scenarios across all five categories. Show expected outcomes **before** running — the user should know what "correct" looks like before committing compute.

| # | Category | What it tests |
|---|----------|---------------|
| 1 | **Happy path** | Clean input, expected "positive" outcome. Confirms the core flow works. |
| 2 | **Clear rejection** | Input that should produce a definitive "no" or rejection. Confirms the negative path. |
| 3 | **Edge case** | Mixed signals, ambiguous classification, near-threshold values. Confirms condition logic. |
| 4 | **Missing data** | Required fields absent or incomplete. Confirms escalation and error paths. |
| 5 | **Unusual input** | Multi-language, very long, schema-drift, or input outside the design's assumptions. Confirms graceful degradation. |

Tailor content to the actual use case — not generic test inputs. Show them in the State 8 format (see `references/ux-flow.md` State 8).

---

## Step 2 — Run the suite

Wait for the user to type `test` to see the tasks, then `run` (all 5) or `run 1 3 5` (specific).

Run tasks via the Beam task API:

```bash
# Create a task
curl -X POST "$BEAM_API_URL/agent-tasks" \
  -H "x-api-key: $BEAM_API_KEY" \
  -H "current-workspace-id: $BEAM_WORKSPACE_ID" \
  -H "Content-Type: application/json" \
  -d '{"agentId": "<id>", "input": "<task input text>"}'

# Poll for completion (repeat until status != RUNNING)
curl "$BEAM_API_URL/agent-tasks/<taskId>" \
  -H "x-api-key: $BEAM_API_KEY" \
  -H "current-workspace-id: $BEAM_WORKSPACE_ID"
```

`USER_INPUT_REQUIRED` on an integration node means the connector is not yet authorised — other nodes will still have run. Their outputs are accessible at `agentTaskNodes[].output.value` and are valid.

---

## Step 3 — Inspect results

Do not treat `COMPLETED` as sufficient. For each task:
- Read `agentTaskNodes[].output.value` per node — not just the final output
- Check which condition branches were taken (`selectedEdge`)
- Compare actual output to the expected outcome you declared in Step 1

Display results as plain-English verdicts and score bars — never raw JSON. See `references/ux-flow.md` State 8 anomaly block.

---

## Step 4 — Surface anomalies with node attribution

For each task where actual ≠ expected:
- Which node produced the wrong output? (Read the per-node trace)
- Was it a wrong extraction (Facts node), wrong reasoning (Intelligence node), or wrong routing (Condition node)?
- What specifically was wrong — off-by-one, total failure, partial?

Show the anomaly block (see `references/ux-flow.md` State 8):

```
⚠ ANOMALY · Task #[N]
────────────────────────────────────────────────────
Expected    [outcome]
Got         [outcome] — [specific reason it differs]

Node [N] ([name]) is likely responsible: [root cause
in one sentence — cite the specific param or logic].

Suggested fix: [specific, actionable node change]

Type 'fix' to review the change, or describe your own.
────────────────────────────────────────────────────
```

---

## Step 5 — Submit Learning feedback

For each task, submit feedback — positive for correct outputs, negative for failures. Granularity matters: tool-level feedback when one specific node caused the failure.

```bash
# Whole-task feedback
curl -X POST "$BEAM_API_URL/agent-tasks/<taskId>/ratings" \
  -H "x-api-key: $BEAM_API_KEY" \
  -H "current-workspace-id: $BEAM_WORKSPACE_ID" \
  -H "Content-Type: application/json" \
  -d '{"rating": "negative", "feedback": "Missed the refund-policy exception above €500.", "expectedOutput": "Escalate refunds above €500."}'
```

Useful negative feedback: what was wrong, the specific node/tool when known, expected output, business consequence.

---

## Step 6 — Verdict

| Outcome | Verdict |
|---------|---------|
| All 5 pass | **Ship it** — offer to publish |
| 4/5 pass, one failure | **Iterate** — fix the specific node, re-run the failing task |
| Multiple systemic failures | **Re-design** — primary KPI unreachable with current architecture → back to Phase 2 |

---

## Exit gate

- [ ] 5 scenarios generated with expected outcomes shown before running
- [ ] Suite covers all 5 categories
- [ ] Each task inspected at node level, not just final output
- [ ] Anomalies attributed to specific nodes with suggested fix
- [ ] Learning feedback submitted (positive or negative) per task
- [ ] Verdict reached

→ If iterating: `phases/6-iterate.md`
→ If shipping: publish, then offer triggers
