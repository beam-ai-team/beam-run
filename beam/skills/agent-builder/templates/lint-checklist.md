# Pre-Deploy Lint Checklist

Run all 9 rules against the spec before deploying. Fix every failure. Do not skip any rule.

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

Every `conditionNode` must have `node_configurations.condition_type` set to exactly `"rule_based"` or `"llm_based"`. Any other value (empty string, `"custom"`, `null`) is rejected by Beam.

**Fix:** set `condition_type` to one of the two valid values.

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

## Rule 6 — objectSchema on object outputs

Every output param with `data_type: "object"` should have `type_options.object_schema` populated.

An absent schema means downstream nodes cannot rely on field names for `linked` params, and Beam cannot validate the output shape.

**Fix:** add `type_options: { object_schema: { field1: "string", field2: "number", ... } }` to the output param.

*(Warn, do not block — unless a downstream node uses `linked` on a specific field from this output.)*

---

## Rule 7 — Integration nodes have an empty prompt

Every integration node (any node where `toolFunctionName` is NOT `GPTAction_Custom_*`, `StandAloneAction_CodeExecutor`, or `BeamSystemAction_*`) must have `prompt: ""`.

An integration node with a non-empty prompt has conflicting behaviour — the tool's own execution logic and the prompt instruction fight each other.

**Fix:** set `prompt: ""` on all integration nodes. Move any business logic that was in the prompt to an upstream custom GPT node.

---

## Rule 8 — Condition-node edges are explicit and non-empty

Every `conditionNode` must have all its `childEdges` (or `branches`) with explicit, non-empty `condition` strings. Blank conditions, single-word labels (`"yes"`, `"no"`, `"else"`), and missing labels are invalid.

Also confirm: every `conditionNode` has at least one `default: true` edge covering the unmatched fallback case.

**Fix:** write explicit condition strings for every branch. Add a fallback edge if missing.

---

## Rule 9 — Each non-condition node has exactly one outgoing edge

Every `executionNode`, `waitingNode`, and `loopingNode` must have exactly one outgoing edge. Multiple outgoing edges on a non-condition node are not supported — Beam has no fork-join.

**Fix:** insert a `conditionNode` to handle any routing. Remove duplicate edges.

---

## Quick scan order

1. Open the spec file
2. For each node, check rules 7, 8, 9 by node type
3. For every `prompt` field, scan for single braces (Rule 1)
4. For every `conditionNode`, check `condition_type` (Rule 2) and edge labels (Rule 8)
5. For every `TriggerAgent` node, check param count and names (Rule 3)
6. For every `CodeExecutor` node, check `code` is non-empty (Rule 4)
7. Trace every `linked` param to its upstream source (Rule 5)
8. Check every `object` output for `objectSchema` (Rule 6)
