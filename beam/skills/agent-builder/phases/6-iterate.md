# Phase 6 — Iterate

> **On entry:** display the phase timeline from `references/ux-flow.md` — Phase 6 row (`✅ Intake  ──  ✅ Design  ──  ✅ Review  ──  ✅ Build  ──  ✅ Validate  ──  ● Iterate`).

**Goal:** apply the smallest fix that resolves the failure, re-validate, loop until the agent passes or the user is satisfied.

**Exit criteria:** all test tasks pass, or the user explicitly accepts the current state and moves to publish.

---

## Step 1 — Translate the failure to a specific node change

From the anomaly surfaced in Phase 5 (or the user's description), identify:
- Which node failed?
- What specifically needs to change — prompt text, input param, output param, edge condition, or model?
- What is the smallest command that applies the fix (see SKILL.md update table)?

**Prefer surgical patches over full redeploys:**
- Prompt change → `update-node-prompt`
- Param change → `update-node-params`
- Edge condition → `update-edge`
- Model change or other config → `update-node`
- Only use `deploy --agent-id` when restructuring multiple nodes

---

## Step 2 — Show the diff (State 9)

Show the before/after diff and wait for `apply`. See `references/ux-flow.md` State 9 for the exact format.

```
────────────────────────────────────────────────────
 FIX  ·  Node [N] — [Node Name]
────────────────────────────────────────────────────
 BEFORE                       AFTER
 ──────────────────────────   ──────────────────────────
 [param]   [old value]        [param]   [new value]  ↑
 [param]   [old value]        [param]   [new value]  ↓
────────────────────────────────────────────────────
 Does this look right?
 Type 'apply' to deploy the fix, or describe a change.
────────────────────────────────────────────────────
```

Do not deploy until the user types `apply`. "Yes", "go ahead", "looks right" do not proceed.

---

## Step 3 — Apply and re-run the failing task only

On `apply`:

1. Apply the change using the surgical command identified in Step 1
2. Re-deploy as **draft** (`deploy --agent-id` only if the change required it)
3. **Re-run only the failing task** — not all 5. Running the full suite on every iteration wastes time
4. Show the delta

**Node ID warning:** if you used `deploy --agent-id`, `add-node`, `remove-node`, or `update-metadata`, node IDs have changed. Re-run `get-nodes` before using any node ID again.

---

## Step 4 — Show the delta

```
 ✅ Node updated  ·  ✅ Re-deployed as draft
 Re-running Task #[N]...

 Before   ████████░░  [score or outcome]
 After    █████████░  [score or outcome]  ↑ [reason]

 ✅/❌ [VERDICT]  ·  [one sentence]

 [N]/5 tasks now correct.
```

---

## Step 5 — Loop

If the task now passes: re-run the full suite once to confirm no regression, then move to the final summary.

If the task still fails: repeat from Step 1. Do not apply a second change until you understand why the first one did not work.

If a new failure appears in the full suite: treat it as a new anomaly — run Steps 1–4 for that node.

---

## Step 6 — Final summary (State 10)

When all tasks pass or the user is satisfied. See `references/ux-flow.md` State 10 for the display format.

```
────────────────────────────────────────────────────
 DONE  ·  v[N]  ·  [Agent Name]
────────────────────────────────────────────────────
 CHANGE LOG
 Node [N] — [name]  ·  [param]  [old] → [new]

 IMPACT
 · [What behaviour changed]
 · [N]/5 test tasks pass

 DRAFT AT   [app.beam.ai/workspaces/...]
────────────────────────────────────────────────────
 Publish to make it live? Or build another agent?
────────────────────────────────────────────────────
```

Link to the **draft** URL. Publish only on explicit user confirmation.

---

## Exit gate

- [ ] Fix translated to a specific node change with the smallest command
- [ ] Diff shown; user typed `apply`
- [ ] Failing task re-run and result shown
- [ ] Full suite re-run to confirm no regression
- [ ] State 10 final summary shown
- [ ] User offered publish (not assumed)
