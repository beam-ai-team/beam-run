# Phase 1 — Intake

> **On entry:** display the phase timeline — Phase 1 row (`● Intake  ──  ○ Design  ──  ...`).

**Goal:** understand the user's problem well enough to design the right agent. Map what exists before designing what will replace it.

**Exit criteria:** you know the task, inputs, outputs, integrations, branching logic, loop signals, trigger, and volume. You have the current manual process confirmed by the user. Any ambiguity is resolved.

---

## Step 1 — Read all context before asking anything

Read everything the user has provided — transcript, PDF, Slack export, file, or plain sentence — before speaking. Extract:

- **Task** — what the agent does end to end
- **Inputs** — what the user provides and in what format
- **Outputs** — what the agent produces or writes
- **Integrations** — only services the user explicitly names
- **Branching** — does the flow take different paths depending on data?
- **Repetition** — does the work run once, or once per item in a batch? Phrases like "for each", "all the", "every", "a batch of", any plural collection = **looping node**
- **Trigger** — how the agent starts (manual, email, schedule, webhook)
- **Volume** — how many times per day/week? (needed for cost projection)

Then run `search-agents` to find similar existing agents:

```bash
beam agent-builder search-agents "<keyword from the use case>"
```

If a close match exists, surface it: "I found an existing agent called X that does Y — want to start from that, or build fresh?"

---

## Step 2 — Show the intake checklist (State 1)

Display while processing. See `references/ux-flow.md` State 1 for the exact format.

Show only what you actually found — never fake a ✅ or show a source you did not check.

---

## Step 3 — Summarise + one gap question (State 2)

Show everything you extracted in plain English. See `references/ux-flow.md` State 2.

**One gapping question max.** If something is genuinely unanswerable from context, ask exactly one question — framed as labelled A/B/C choices, never open text. If everything is answerable, skip the question block entirely and say so.

Typical gap situations:
- Integration named but ambiguous ("email" → Gmail or Outlook?)
- Trigger not stated at all
- Volume completely unknown (ask: A → a few times/day, B → hundreds/day, C → occasional manual)

---

## Step 4 — Map the current manual process (State 3)

Before designing the agent, map what it replaces. Draw the current workflow as an ASCII flow, annotating slow or error-prone steps inline. Wait for explicit confirmation before moving on.

See `references/ux-flow.md` State 3 for the display format.

```
Example:

  Recruiter receives CV via email
       ↓
  Opens CV manually  ← 20–30 min/CV
       ↓
  Scores against job criteria  ← inconsistent, no audit trail
       ↓
  Pastes verdict into spreadsheet
       ↓
  Emails hiring manager

  ⚠ Pain points:
     · Manual scoring takes 20–30 min per CV
     · No consistent rubric — depends on who reviews
     · No audit trail
```

If the user corrects the map, update and re-show before proceeding to Phase 2.

---

## Exit gate

- [ ] Task, inputs, outputs confirmed
- [ ] All named integrations noted (none invented)
- [ ] Loop signals identified or ruled out
- [ ] Trigger identified or assumed with stated assumption
- [ ] Volume captured or estimated
- [ ] Business process map shown and confirmed with `yes`
- [ ] One gap question asked if needed, answered

→ Proceed to `phases/2-design.md`
