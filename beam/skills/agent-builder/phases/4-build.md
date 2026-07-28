# Phase 4 — Build

> **On entry:** display the phase timeline from `references/ux-flow.md` — Phase 4 row (`✅ Intake  ──  ✅ Design  ──  ✅ Review  ──  ● Build  ──  ○ Validate  ──  ○ Iterate`).

**Goal:** turn the approved design into a live draft agent on Beam — lint-clean, verified, smoke-tested.

**Exit criteria:** an agent exists in Beam as a draft, `verificationPassed: true`, 2–3 representative nodes pass smoke tests, build checklist documented.

---

## Step 0 — Load all references in parallel (do this before writing a single line)

Read all four in one parallel batch — never sequentially:

```
references/spec-format.md
references/node-authoring.md      ← skip if already loaded in Phase 2
templates/lint-checklist.md
assets/example-specs/README.md    ← pick the closest example, then read that file too
```

Loading these together removes 8–12 s of sequential I/O wait. Only after all four are in context should you start the spec.

---

## Step 1 — Write the spec

Write the agent spec to `/tmp/<slug>.json`. Use `references/spec-format.md` for the full schema. Copy the closest file from `assets/example-specs/` as a starting point — see its `README.md`.

The spec has a `nodes` array and an optional `integrations` array. Use the `toolFunctionName` values confirmed in Phase 2. Every custom GPT node's `prompt` must use the 4-section structure — see `references/node-authoring.md`.

---

## Step 2 — Lint (run before any API call)

Apply every rule in `templates/lint-checklist.md` against the spec (already loaded in Step 0). Fix all failures before proceeding. Do not skip this step.

---

## Step 3 — Dry-run

```bash
BEAM_API_KEY='...' BEAM_WORKSPACE_ID='...' BEAM_API_URL='...' \
  python3 scripts/beam.py deploy /tmp/<slug>.json --dry-run
```

Inspect the payload. Confirm: expected node count, integration nodes show in `integrationsToAttach`, no structural surprises. Fix the spec if anything looks wrong, re-lint, re-dry-run.

---

## Step 4 — Deploy

```bash
BEAM_API_KEY='...' BEAM_WORKSPACE_ID='...' BEAM_API_URL='...' \
  python3 scripts/beam.py deploy /tmp/<slug>.json
```

`deploy` creates the agent, attaches every integration, re-links downstream params, and verifies — in one call. It does **not** publish.

Check the result:
- `verificationPassed: true` → proceed.
- `verificationPassed: false` → run `verify-links <agentId>`, read every failed link, fix the spec, redeploy.

---

## Step 5 — Smoke test (2–3 representative nodes)

Test the most important nodes individually before running a full task. This catches prompt/param wiring failures cheaply.

```bash
BEAM_API_KEY='...' BEAM_WORKSPACE_ID='...' BEAM_API_URL='...' \
  python3 scripts/beam.py test-node AGENT_ID NODE_ID "Realistic task input for this node"
```

Pick nodes that: (a) do the core reasoning or extraction, (b) have the most complex prompt, (c) feed their output into other linked nodes. A bad node here fails silently in full task runs.

If a smoke test fails, fix the node prompt or params (`update-node-prompt` / `update-node-params`) and re-test before proceeding.

---

## Step 6 — Show build checklist (State 7)

Display a live checklist as each step completes. See `references/ux-flow.md` State 7 for the exact format. Then show plain-English node logic — what each node does and why that model was chosen.

---

## Step 7 — Report draft and ask about next steps

Lead with the agentId — it is the most actionable piece of information. Use the compact format from `references/ux-flow.md` State 7:

```
 ✅  Draft saved · [agentId] · not live

 Type  'test'  'publish'  or  'trigger'
```

Publish only on an explicit `publish`. If the user wants triggers first, see `references/triggers.md`.

---

## Exit gate

- [ ] Spec written and lint-clean (all 9 rules pass)
- [ ] Dry-run passed — payload inspected
- [ ] Deployed; `verificationPassed: true`
- [ ] 2–3 nodes smoke-tested
- [ ] State 7 build checklist shown
- [ ] Draft `agentId` given to user; publish/test/trigger offered

→ If testing: `phases/5-validate.md`
→ If publishing: `publish <graphId>`, then offer triggers and testing
