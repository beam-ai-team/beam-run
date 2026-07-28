# Flow Patterns — User Intent → Graph Shape

**Beam executes nodes sequentially. There is no parallel execution.** A non-condition node has exactly one outgoing edge. To do several things, chain them. To do one of several things, use a condition node. To do a thing for each item in a list, use a looping node.

Use this file in Phase 2 (Design) when translating a verbal brief into a node layout.

---

## The four core patterns

### 1. Sequential chain — do ALL of several things

Each node has one edge to the next.

```
Extract Data → Validate → Draft Email → Send Email
```

Use when: "and then", "and after that", "also send", "and finally". Multi-step pipelines where every step always runs.

### 2. Condition node — do ONE of several things

A `conditionNode` branches based on an LLM-evaluated condition (`llm_based`) or a deterministic rule (`rule_based`). Only the matched branch runs.

```
Classify Ticket → {Condition}
                   -- urgent --> Slack Alert → Log
                   -- normal --> Log
```

Use when: "if X then Y else Z", "depending on", "based on the type", "route to different departments".

**Key judgment:** when both paths must merge back into a single result (e.g. "draft a different reply for each department then send it"), do not branch the flow. Instead, use one node that takes the classification as an input param and adjusts its output accordingly. A fork is only right when the two paths diverge and never need to recombine.

### 3. Looping node — do something for each item

A `loopingNode` repeats a body sub-flow. Count-based (`iterationCount`) or variable-based (iterates over an upstream array). Body nodes carry `parent: <loopKey>`.

```
Fetch Articles → [Loop: For Each Article]
                    → Summarise Article (parent: loop)
                 → Compile Digest
```

Use when: "for each row", "for every item", "loop over", "do this 3 times", "process a batch of N", any plural collection of inputs.

### 4. TriggerAgent fan-out — fire-and-forget sidecars

`BeamSystemAction_TriggerAgent` fires a downstream agent without blocking the main flow.

```
Main Flow → ... → Final Action
              ↘ TriggerAgent: Audit Logger   (fire-and-forget)
              ↘ TriggerAgent: Slack Notifier (fire-and-forget)
```

Use when: "also log this to audit", "send a copy to", "in parallel, notify". The parent flow does not wait for sidecars; results are observed via shared state (Airtable, Memory), not return values.

---

## User-says → pattern translation table

| What the user said | Pattern | Notes |
|---|---|---|
| "send it to Gmail **and** Slack" | Sequential chain | Two integration nodes in sequence |
| "summarise **and** translate" | Sequential chain | Same |
| "if urgent alert Slack, **else** just log it" | Condition node | LLM-based condition on priority |
| "**depending on** the department, draft a different reply" | Condition node | One branch per department |
| "classify, **respond differently**, then send the reply" | Condition + merge | See merge node below |
| "**for each** invoice line, validate" | Looping node | Variable-based on upstream array |
| "do this **three times** to triple-check" | Looping node | Count-based (`iterationCount: 3`) |
| "**also** log every decision to audit" | TriggerAgent fan-out | Fire-and-forget |
| "send **only if** the total exceeds 1000" | Condition node | Single branch with fallback no-op |
| "**wait** 2 days **then** follow up" | Waiting node | `waitType: time_based` |
| "once they **reply**, continue" | Waiting node | `waitType: condition_based` |

---

## Merge node — branches converging on a shared action

When two branches both end at the same action (e.g. "draft either an approval or a rejection, then send it"), use a merge node pattern:

```
Classify → {Condition}
              -- approved --> Draft Approval  ──┐
              -- rejected --> Draft Rejection ──┤
                                               Send Email
```

The merge node (`Send Email`) reads the drafted message with `ai_fill` — the only case where `ai_fill` is preferred over `linked` on a non-entry node, because the data could arrive from either branch.

**Anti-pattern:** do not connect both branch nodes' outputs as separate `linked` inputs on the merge node — Beam has no "pick whichever arrived" semantics for linked params.

---

## What is NOT supported

- **Parallel execution** — nodes always run in series; there is no fork-join
- **Multiple incoming edges on an execution node** — every execution node has exactly one parent edge (except the entry node)
- **Condition node → condition node directly** — insert an execution or evidence node between them
- **`is_exit: true` markers** — terminal nodes simply have no outgoing edge; explicit exit nodes are not supported
