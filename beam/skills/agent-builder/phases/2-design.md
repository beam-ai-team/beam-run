# Phase 2 — Design

> **On entry:** display the phase timeline from `references/ux-flow.md` — Phase 2 row (`✅ Intake  ──  ● Design  ──  ○ Review  ──  ...`).

**Goal:** turn the intake into a concrete agent design — the right graph shape, the right tools, the right models, with a cost projection the user can act on.

**Exit criteria:** one or two architecture options with Mermaid diagrams, node-level specs, and a credit cost projection. User has picked one.

---

## Step 1 — Search tools (parallel, before any design)

For every integration the agent needs, search in parallel:

```bash
beam agent-builder search-tools gmail --managed-only
beam agent-builder search-tools slack --managed-only
```

`--managed-only` drops custom-GPT-only tools and keeps real managed integrations. If it returns nothing, remove `--managed-only` and check `references/integrations.md`.

Each result carries `toolFunctionName`, `requiredArgs`, `integrationProvider`, `allowWaiting`. **Confirm a `toolFunctionName` for every integration node before designing.** Never draw an integration node without a search result.

**Search output is large — filter inline.** Pipe through a one-liner to extract only the fields you need rather than reading a saved file in a second step:

```bash
beam agent-builder search-tools slack --managed-only | \
  python3 -c "import json,sys; [print(t['toolFunctionName'], t['requiredArgs']) \
  for t in json.load(sys.stdin)['tools'] if 'reply' in t['toolFunctionName'].lower()]"
```

---

## Step 2 — Three pre-design checks

Before drawing any graph, run these checks. They prevent the most common production failures.

**1. Does the workflow end with a real action?**
The terminal node must write, send, update, or call something external — not just produce a JSON decision. Ask: "After the agent decides X, what should actually happen?" If the answer is "just output the result," make the user confirm that explicitly.

**2. Is any node doing deterministic work?**
Parsing, arithmetic, threshold checks, format coercion, schema coercion, table lookups → use `StandAloneAction_CodeExecutor`, not Custom GPT. Custom GPT is for classification, judgment, drafting, or extraction over unstructured content.

**3. Is there a fork where one branch can skip expensive work?**
If yes, propose a `conditionNode` before the expensive step rather than running it on every path.

---

## Step 3 — Design the graph

Reference `patterns/tool-taxonomy.md` for how to type and name every node.
Reference `patterns/flow-patterns.md` for how user language maps to graph shapes.

**Wire data with `linked` — extract once, link everywhere.**
- Pull extraction high in the graph: an early node produces every structured field that downstream nodes need.
- Use `linked` for any input whose source is a named output param of an upstream node. It is deterministic — exact output of a known node.
- Use `ai_fill` for: the first node (reads the user's free-form message), merge points where data could come from either branch, and **any node directly after an integration node** (Beam publishes no output schema for integration tools — a `linked` name that misses the real output fails at run time).
- The more of the graph that is `linked`, the more reliable the agent.

**Node type selection:**

| What the goal implies | Node type |
|-----------------------|-----------|
| A processing step — run a prompt or call an integration | `executionNode` (default) |
| "if … otherwise …", classify-then-route, branch by data | `conditionNode` |
| "wait", "after N days", "once they reply", "follow up later" | `waitingNode` |
| "for each", "every", "all the …", "a batch of N", processing a list | `loopingNode` |

This table is a starting hypothesis — validate each against the whole goal. A surface "if/else" is **not** always a `conditionNode`: when both paths must merge back into one result (e.g. a combined report), model the split as a data field on one path rather than branching the flow.

**One node per processing step, one per integration action.** Never bundle "draft message + send message" into one node — see `patterns/tool-taxonomy.md` compose/send split rule.

For each custom GPT node, pick its prompt model using `references/node-authoring.md` — cheapest model that does the task reliably. Use the task-complexity table, not guesswork.

---

## Step 4 — One option or two?

**Simple linear agents (≤4 nodes, no branching, no loops):** design one option and present it directly.

**Everything else (5+ nodes, any branching, any loops):** design two architecturally distinct options. They must differ meaningfully — not just by model or node count. Show tradeoffs explicitly.

For two options, see `references/ux-flow.md` State 4 for the display format. Always make a recommendation and quote the user's own context to justify it.

---

## Step 5 — Calculate cost

For each option, sum the credit cost across all nodes. Then project at the user's stated volume.

See `references/node-authoring.md` — Cost projection section for credit rates and the per-node formula.

```
credits_per_task  = sum of each node's estimated credits
cost_per_task     = credits × $0.10 (Pro) or × $0.049 (Enterprise)
monthly_cost      = cost_per_task × monthly_volume
```

If volume is unknown, state the assumption explicitly (e.g. "assuming 100 tasks/day").

Show the cost projection alongside each option before asking the user to choose.

---

## Exit gate

- [ ] `search-tools` run for every integration; `toolFunctionName` confirmed for each
- [ ] Three pre-design checks done
- [ ] Graph designed with correct node types and `linked`-first data flow
- [ ] One or two options presented per the complexity rule
- [ ] Credit cost projection shown at user's volume
- [ ] User has picked an option (typed A or B, or confirmed the single option)

→ Proceed to `phases/3-review.md`
