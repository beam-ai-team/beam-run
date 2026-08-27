# Pre-Deploy Lint Checklist

Run all 10 rules against the spec before deploying. Fix every failure. Do not skip any rule.

Rules 1–6 are mechanical — scan the spec programmatically or carefully. Rules 7–9 are structural — check each node type.

---

## Rule 1 — Brace doubling in prompts

Every `{` and `}` in a `prompt` string must be either:
- Part of a valid placeholder: `{param_name}` where `param_name` matches an entry in `inputParams`
- Doubled to escape a literal brace: `{{` / `}}`

Scan every `prompt` field for orphan single braces. A single `{` that is not a placeholder will fail at runtime when Beam tries to inject values.

**Fix:** double every literal brace → `{{` / `}}`.

---

## Rule 2 — conditionType valid

Every `conditionNode` must have `node_configurations.conditionType` set to exactly `"rule_based"` or `"llm_based"`. Any other value (empty string, `"custom"`, `null`) is rejected by Beam.

`node_configurations` is sent to the API verbatim, so the key is **camelCase**. A
snake_case `condition_type` is ignored and the node silently falls back to
`{"conditionType": "llm_based", "llmModel": "GPT40"}` — a real behaviour change.

**Fix:** set `conditionType` to one of the two valid values.

---

## Rule 3 — TriggerAgent input shape

Every node with `toolFunctionName: "BeamSystemAction_TriggerAgent"` must have **exactly 3 input params**, named and typed as follows:

| `paramName` | `fillType` | `dataType` |
|---|---|---|
| `agentName` | `static` | `string` |
| `urls` | `ai_fill` | `string[]` |
| `payload` | `linked` | `object` |

No more, no fewer. Any deviation causes a silent misconfiguration.

**Fix:** replace the `inputParams` array with exactly these three entries.

---

## Rule 4 — CodeExecutor consistency

Every node with `toolFunctionName: "StandAloneAction_CodeExecutor"` must have:
- `code_language` set to a non-null value (e.g. `"javascript"`)
- `code` set to a non-empty string

A CodeExecutor node with empty `code` deploys but fails at runtime on every task.

**Fix:** add the `code` field with a valid function body.

---

## Rule 5 — Linked params resolve upstream

For every input param with `fill_type: "linked"`, confirm that the linked output exists in an upstream node in the graph.

Check: is the source node reachable before this node in the execution path? Is the output param name correct?

**Fix:** correct the link source, or change `fill_type` to `ai_fill` if the upstream source is not deterministic (e.g. after a condition branch that may not have run).

---

## Rule 6 — Do not rely on an object output's schema

Output-param schemas are **not** deployable today: the builder writes
`"typeOptions": null` on every output param, so a `type_options` /
`object_schema` block in a spec is silently discarded.

**Fix:** do not author one. If a downstream node needs specific fields, either
have the upstream node emit them as separate scalar output params (which *can*
be `linked`), or read the object with `ai_fill`.

---

## Rule 7 — Integration nodes have an empty prompt

Every integration node — any node with a matching entry in the spec's
`integrations` array — must have `prompt: ""`. (Check the `integrations` array,
not `toolFunctionName`: that field is derived at build time and never appears in
a spec.)

An integration node with a non-empty prompt has conflicting behaviour — the tool's own execution logic and the prompt instruction fight each other.

**Fix:** set `prompt: ""` on all integration nodes. Move any business logic that was in the prompt to an upstream custom GPT node.

---

## Rule 8 — Condition-node edges are explicit and non-empty

Every `conditionNode` must have all its `childEdges` (or `branches`) with explicit, non-empty `condition` strings. Blank conditions, single-word labels (`"yes"`, `"no"`, `"else"`), and missing labels are invalid.

There is **no** `default: true` edge flag — it does not exist in the edge schema.
Cover the fallback case with an explicit final branch whose condition names it
(e.g. `"anything else"`), not with a blank or flagged edge.

**Fix:** write explicit condition strings for every branch, including the
catch-all.

---

## Rule 9 — Nodes do not fork implicitly

Every `executionNode`, `waitingNode`, and `loopingNode` must have at most one
outgoing edge. A terminal action may have no edge; multiple outgoing edges on a
non-condition node are not supported — Beam has no fork-join. The entry node
must have exactly one outgoing edge.

**Fix:** insert a `conditionNode` to handle any routing. Remove duplicate edges.

---

## Rule 10 — Custom GPT prompts declare their inputs

Every Custom GPT node must have a non-empty prompt with `## Role:`, `## Task:`,
`## Context:`, and `## Rules:` sections; at least one declared input param; and
one `{param_name}` placeholder for every declared input. Every placeholder must
match a declared input. It must also declare at least one typed output param.

**Fix:** add the missing input/output param or correct the prompt placeholder.
Run `beam agent-builder readiness AGENT_ID` after the mutation to check the
saved graph that will actually be published.

---

## Quick scan order

1. Open the spec file
2. For each node, check rules 7, 8, 9 by node type
3. For every `prompt` field, scan for single braces (Rule 1)
4. For every `conditionNode`, check `conditionType` (Rule 2) and edge labels (Rule 8)
5. For every `TriggerAgent` node, check param count and names (Rule 3)
6. For every `CodeExecutor` node, check `code` is non-empty (Rule 4)
7. Trace every `linked` param to its upstream source (Rule 5)
8. Confirm no spec relies on an object output's schema (Rule 6)
