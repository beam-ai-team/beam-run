# UX Flow Reference

Interaction design for The Agent Builder. It defines display templates, command
words, and the state-by-state conversation flow.

**Load it once, the first time you need a display template you do not already
have** — not on entry to every phase. The phase timeline rows are inlined in the
phase files, so those do not require this file.

The skill drives every state. The user validates with single command words. The next valid command is always embedded in the display — the user never wonders what to type.

> **Connection note:** Step 0 of SKILL.md runs `validate` first; credentials resolve
> automatically from `beam login`, so there is nothing to collect. Show the banner on
> first load, as SKILL.md specifies — if `validate` then fails, relay its `next` field
> instead of continuing to State 1.

---

## Phase Timeline

Render this header at the **start of every phase** (when loading a new phase file). It orients the user without interrupting their flow.

**Rules:**
- `✅` = phase completed and exited
- `●` = current phase (active)
- `○` = phase not yet reached
- Show the timeline on one line, always in full — never truncate
- Place it immediately after the phase label, before any questions or output

```
PHASE [N] · [NAME]
────────────────────────────────────────────────────
 [timeline for this phase — copy exact line from table below]
```

| Phase | Timeline line |
|-------|--------------|
| 1 — Intake   | `● Intake  ──  ○ Design  ──  ○ Review  ──  ○ Build  ──  ○ Validate  ──  ○ Iterate` |
| 2 — Design   | `✅ Intake  ──  ● Design  ──  ○ Review  ──  ○ Build  ──  ○ Validate  ──  ○ Iterate` |
| 3 — Review   | `✅ Intake  ──  ✅ Design  ──  ● Review  ──  ○ Build  ──  ○ Validate  ──  ○ Iterate` |
| 4 — Build    | `✅ Intake  ──  ✅ Design  ──  ✅ Review  ──  ● Build  ──  ○ Validate  ──  ○ Iterate` |
| 5 — Validate | `✅ Intake  ──  ✅ Design  ──  ✅ Review  ──  ✅ Build  ──  ● Validate  ──  ○ Iterate` |
| 6 — Iterate  | `✅ Intake  ──  ✅ Design  ──  ✅ Review  ──  ✅ Build  ──  ✅ Validate  ──  ● Iterate` |

The timeline does not change mid-phase. Once a phase is entered, `●` stays on that phase until the phase's exit gate is passed and the next phase file is loaded.

---

## State 0 — Banner

Output after credentials are validated. Then wait — do not ask questions, do not begin intake.

```
🤖  BEAM AI  ·  The Agent Builder
────────────────────────────────────────────────────
    Drop a transcript. Get a production agent.

    I read the context. I design the flow. I build it.
    You validate and ship.
────────────────────────────────────────────────────
📥  GIVE ME
    Transcript · PDF · Slack thread · one sentence
    I'll figure out the rest.

🚀  SUGGESTED STARTS
    1. build a screening agent for [client name]
    2. rebuild [agent name] but leaner
    3. drop a file and say 'build'
────────────────────────────────────────────────────
```

---

## State 1 — Intake checklist

Show after reading context and running `search-agents`. Only list sources you actually queried. Never fake a ✅ or show a source that is not configured. No progress bar — it is static output, not live progress.

```
🤖
────────────────────────────────────────────────────
 ✅  Client      [name or one-line summary]
 ✅  Agents      [N similar found / none found]
 ✅  Volume      [signal — or: not stated, asking below]
 ✅  [Source]    [loaded — only if actually read]
────────────────────────────────────────────────────
```

---

## State 2 — Summary + one gap question

Show everything extracted. Ask at most one genuinely unanswerable thing, framed as labelled choices. If everything is answerable, skip the question block and say so.

```
🤖
────────────────────────────────────────────────────
 HERE'S WHAT I UNDERSTOOD
────────────────────────────────────────────────────

 Use case     [one-line description]
 Similar      [agent 1] · [agent 2]  (or: none found)
 Trigger      [how agent starts]
 Output       [what it produces / writes]
 Volume       [frequency]
 Integrations [explicitly named ones only]

 [2–4 sentence plain-English summary of the use case,
  what the manual process looks like today, and what
  the automation would replace]

────────────────────────────────────────────────────
 One thing I couldn't find:

 [Question — only if genuinely unanswerable from context]

   A  ⚡ [Option label]  — [description]
   B  🎯 [Option label]  — [description]
   C  💰 [Option label]  — [description]

────────────────────────────────────────────────────
```

If no question is needed:
```
 Everything I need is in the context — mapping the process now.
```

---

## State 3 — Business process map

Map the **current manual process** — not the agent, but what it replaces. Annotate pain points on the diagram. Get explicit confirmation before designing.

```
🤖
────────────────────────────────────────────────────
 YOUR CURRENT PROCESS  ·  before automation
────────────────────────────────────────────────────

  [ASCII flow of manual steps. Annotate slow or
   error-prone steps inline, e.g.:
   "← 20–30 min/CV"  "(inconsistent, no audit trail)"]

  ⚠  Pain points:
     · [pain 1]
     · [pain 2]
     · [pain 3]

────────────────────────────────────────────────────
 Is this right?
 Type 'yes' or describe what's different.
────────────────────────────────────────────────────
```

If the user corrects it, update and re-show before proceeding.

---

## State 4 — Design options + cost

Show for agents with 5+ nodes or branching. For simple linear agents, present the single option directly and skip to State 5.

Always make a recommendation. Always quote the user's own context to justify it. Never hedge.

> **⚠️ NO full node table here.** State 4 uses a compact inline node chain only — enough for the user to compare A vs B. The full node table (with tool kind, model, consent, credits per node) belongs exclusively in State 5. Rendering a full table in State 4 means the user sees the identical table twice in two consecutive messages, which is redundant and slows the session.

```
🤖
────────────────────────────────────────────────────
 OPTION A  ·  [Architecture name]
────────────────────────────────────────────────────
 [Node 1 (model · N cr)] → [Node 2 (model · N cr)] → ...

 ⏱ ~[X]s/task   [N] nodes   [X] credits/task

────────────────────────────────────────────────────
 OPTION B  ·  [Architecture name]                ★ rec.
────────────────────────────────────────────────────
 [Node flow with model and credit tags]

 ⏱ ~[X]s/task   [N] nodes   [X] credits/task

────────────────────────────────────────────────────
 COST AT [VOLUME]  ·  1 credit = $0.10 Pro · $0.049 Enterprise
 A   [X] cr/task   $[X]/wk   $[X]/mo   $[X]/yr
 B   [X] cr/task   $[X]/wk   $[X]/mo   $[X]/yr

 Recommended B — [one sentence quoting the user's own
 context — transcript, brief, or stated goal — to justify
 the recommendation.]

────────────────────────────────────────────────────
 Type A or B, or describe a change.
────────────────────────────────────────────────────
```

---

## State 5 — Review gate

Show after the user picks an option (or after single-option design). Nothing is built until `build` is typed. If the user describes a change, update and re-show this screen.

```
🤖
────────────────────────────────────────────────────
 REVIEW  ·  Nothing is built until you type 'build'
────────────────────────────────────────────────────

 Agent     [agent name]
 Tenant    [BEAM_API_URL]

 WHAT IT DOES
 [2–3 sentences in plain English written for the
  user — no node jargon, no API terminology]

 THE FLOW
```mermaid
graph TD
    [Mermaid diagram of chosen option]
```

 NODE TABLE
 [# | Node | Tool kind | Model | Consent | Est. cr]
 Omit the onError column — it is STOP on every node and adds no information.

 COST AT [VOLUME]
 [X] cr/task   $[X]/week   $[X]/month   $[X]/year
 1 credit = $0.10 Pro · $0.049 Enterprise

────────────────────────────────────────────────────
 Happy with this?
 Type 'build' to create in Beam, or describe a change.
────────────────────────────────────────────────────
```

---

## State 7 — Build progress + node logic

Show while `deploy` runs. Never show raw JSON or API output. Update each line as the step completes.

```
🤖
────────────────────────────────────────────────────
 BUILDING  ·  [Agent Name]
────────────────────────────────────────────────────

 ✅  Lint passed (9/9 rules)
 ✅  Dry-run verified
 ✅  Agent created
 ✅  Node 1: [Name] ([model] · [N] cr)
 ✅  Node 2: [Name] ([model] · [N] cr)
 ...
 ✅  [Integration] attached
 ✅  Links verified

────────────────────────────────────────────────────
 AGENT LOGIC  ·  what each node does
────────────────────────────────────────────────────

 [N]  NODE NAME   [model · N cr]
      [One sentence: what it does + why that model]
 ...

────────────────────────────────────────────────────
 ✅  Draft saved · [agentId] · not live

 Type  'test'  'publish'  or  'trigger'
────────────────────────────────────────────────────
```

---

## State 8 — Validate

Show the 5 test scenarios with expected outcomes before running. The user should know what "correct" looks like before committing compute.

```
🤖
────────────────────────────────────────────────────
 TEST TASKS  ·  5 scenarios for this use case
────────────────────────────────────────────────────

 #1  [Happy path — strong match]         → EXPECTED: [outcome]
 #2  [Clear rejection]                   → EXPECTED: [outcome]
 #3  [Edge case — mixed signals]         → EXPECTED: [outcome]
 #4  [Missing / insufficient data]       → EXPECTED: [outcome]
 #5  [Unusual / unexpected input]        → EXPECTED: [outcome]

────────────────────────────────────────────────────
 Type 'test' to confirm, then 'run' for all 5,
 or 'run 1 3 5' for specific tasks.
────────────────────────────────────────────────────
```

After `run`, show one row per task with inline node status. Then surface anomalies only — no repeated table.

```
🤖
────────────────────────────────────────────────────
 T1  ████████░░  [Node A] ✅  [Node B] ✅  [Node C] ❌ ([short error])
 T2  ████████░░  [Node A] ✅  [Node B] ✅  [Node C] ❌ ([short error])
 T3  ██████████  [Node A] ✅  [Node B] ✅  [Node C] ✅
 T4  ████░░░░░░  [Node A] ✅  [Node B] ❌ ([short error])
 T5  ██████████  [Node A] ✅  [Node B] ✅
────────────────────────────────────────────────────
```

For each failing task, one compact anomaly line immediately below its row:

```
 ⚠ T[N] — [Node name]: [one-line root cause]. Fix: [one-line action].
```

Example:
```
 ⚠ T4 — Create Triage Ticket: label "Needs Triage" not found in workspace. Fix: remove labels param.
```

Only expand to a multi-line block if the root cause genuinely needs more than one sentence to explain. Default is the single line.

`USER_INPUT_REQUIRED` on an integration node = connector not yet authorised. Other nodes still ran — their outputs are valid in `agentTaskNodes[].output.value`.

---

## State 9 — Fix + iterate

When the user types `fix` or describes a change, show the specific diff. Do not deploy until `apply` is typed.

```
🤖
────────────────────────────────────────────────────
 FIX  ·  Node [N] — [Node Name]
────────────────────────────────────────────────────

 BEFORE                        AFTER
 ───────────────────────────   ───────────────────────────
 [param]   [old value]         [param]   [new value]  ↑
 [param]   [old value]         [param]   [new value]  ↓

────────────────────────────────────────────────────
 Does this look right?
 Type 'apply' to deploy the fix, or describe a change.
────────────────────────────────────────────────────
```

On `apply`:
1. Apply the change (smallest command — see SKILL.md update table)
2. Re-deploy as draft
3. Re-run **only the failing task** — not all 5
4. Show the delta:

```
 ✅ Node updated  ·  ✅ Re-deployed as draft
 Re-running Task #[N]...

 Before   ████████░░  [outcome]
 After    █████████░  [outcome]  ↑ [reason]

 ✅/❌ [VERDICT]  ·  [one sentence]

 [N]/5 tasks now correct.
```

Loop until all tasks pass or the user is satisfied.

---

## State 10 — Final summary

When all tasks pass or the user signals done.

```
🤖
────────────────────────────────────────────────────
 DONE  ·  v[N]  ·  [Agent Name]
────────────────────────────────────────────────────

 CHANGE LOG
 Node [N] — [name]
 · [param]  [old] → [new]

 IMPACT
 · [What behaviour changed]
 · [N]/5 test tasks pass

 DRAFT AT   [app.beam.ai/workspaces/...]
────────────────────────────────────────────────────
 Publish to make it live? Or build another agent?
────────────────────────────────────────────────────
```

Link to the **draft** URL until the user explicitly publishes.

---

## Command word reference

The user's only required inputs. Embed the relevant command in every display.

| User types | Skill does |
|-----------|-----------|
| `yes` | Confirms the business process map → proceeds to Phase 2 |
| `A` or `B` | Selects architecture option → shows Review gate (State 5) |
| `build` | Triggers deploy sequence (Phase 4) — the only build trigger |
| `test` | Shows 5 test scenarios with expected outcomes |
| `run` | Runs all 5 test tasks via Beam API |
| `run 1 3 5` | Runs specific tasks by number |
| `fix` | Shows before/after diff of suggested node fix |
| `apply` | Deploys fix as draft, re-runs failing task only |
| `publish` | Publishes draft agent — explicit user action only |
| `trigger` | Opens trigger setup (see `references/triggers.md`) |
