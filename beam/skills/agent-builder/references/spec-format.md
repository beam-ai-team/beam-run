# Spec Format Reference

The complete JSON schema for a Beam agent spec — the file you pass to
`beam.py deploy` or `beam.py create`. `beam.py` translates this compact spec
into the full Beam API payload (generating UUIDs, wiring edges, resolving
links), so you only write the readable form below.

## Contents

- [Top-level spec](#top-level-spec)
- [Node spec](#node-spec)
- [Defaults — what you can omit](#defaults--what-you-can-omit)
- [Input params](#input-params)
- [Output params](#output-params)
- [Edges](#edges)
- [Node types](#node-types)
- [Integration nodes and the integrations array](#integration-nodes-and-the-integrations-array)
- [Condition nodes](#condition-nodes)
- [Waiting nodes](#waiting-nodes)
- [Looping nodes](#looping-nodes)
- [Flow patterns](#flow-patterns)
- [Minimal example](#minimal-example)
- [Update-merge semantics](#update-merge-semantics)

---

## Top-level spec

```json
{
  "agentName": "string (required)",
  "agentDescription": "string",
  "personality": "string",
  "restrictions": "string",
  "prompts": ["example prompt shown in the UI", "..."],
  "nodes": [ /* node spec objects — required, non-empty */ ],
  "integrations": [ /* integration objects — optional */ ]
}
```

Only `agentName` and `nodes` are required. `integrations` is part of the *same*
file — it is not a separate call.

The spec must contain **exactly one** entry node (`is_entry: true`). Node `key`
values must be unique. Every edge `target` must be a node key in the same spec.
`beam.py` checks all of this before any API call and reports a clear error.

---

## Node spec

```json
{
  "key": "write-blog",
  "name": "Write Blog Post",
  "objective": "Write a short blog post from the given topic",
  "is_entry": false,
  "node_type": null,
  "x": 250,
  "y": 150,
  "model": "BEDROCK_CLAUDE_SONNET_4",
  "tool_name": "Write Blog Post",
  "tool_description": "",
  "prompt": "## Role:\n...\n## Task:\n...\n## Context:\n```\n{topic}\n```\n## Rules:\n1. ...",
  "on_error": "STOP",
  "enable_retry": false,
  "retry_count": 1,
  "retry_wait_ms": 1000,
  "fallback_models": null,
  "evaluation_criteria": [],
  "node_configurations": null,
  "parent": null,
  "input_params": [ /* ... */ ],
  "output_params": [ /* ... */ ],
  "edges": [ { "target": "next-node-key" } ]
}
```

| Field | Type | Meaning |
|-------|------|---------|
| `key` | string | Unique identifier *within the spec*. Used to wire edges and links. Not a UUID — `beam.py` maps it to one. |
| `name` | string | Human-readable node name. Also derives the tool function name on custom nodes — keep it stable across updates. |
| `objective` | string | One line describing what the node does. **Must be unique within the agent** — `deploy` maps spec nodes to created nodes by matching objective text. |
| `is_entry` | boolean | `true` on exactly one node — the entry point. |
| `node_type` | string\|null | `null` → auto (`entryNode` if `is_entry`, else `executionNode`). Set explicitly to `"conditionNode"`, `"waitingNode"`, or `"loopingNode"`. |
| `x`, `y` | number | Canvas position. Optional — by default the script auto-positions nodes by graph depth (one row per step, branches spread across) so they never overlap in the UI. Provide **both** to pin a node to a fixed spot. On a **loop body node** `x`/`y` are read relative to the loop container, not the canvas — leave them unset so auto-layout places the body inside the loop. |
| `model` | string | LLM for this node. See `node-authoring.md`. Default `BEDROCK_CLAUDE_SONNET_4`. |
| `tool_name` | string | Display name of the node's custom tool. Defaults to `name`. |
| `tool_description` | string | Optional one-line tool description. |
| `prompt` | string | The node's LLM instruction. Custom nodes: use the 4-section markdown structure. Integration / waiting nodes: empty string `""`. |
| `on_error` | string | `"STOP"` (default) or `"CONTINUE"`. Use `CONTINUE` only for non-critical nodes (e.g. a Slack notification). |
| `enable_retry` / `retry_count` / `retry_wait_ms` | bool / num / num | Auto-retry on failure. Defaults `false` / `1` / `1000`. |
| `fallback_models` | array\|null | Alternate models if the primary fails. |
| `evaluation_criteria` | array | Quality-evaluation rules. Usually `[]`. |
| `node_configurations` | object\|null | Required for `conditionNode`, `waitingNode`, and `loopingNode` (see below). `null` otherwise. |
| `parent` | string\|null | Only on a **loop body node** — the `key` of the `loopingNode` this node runs inside. `null` otherwise. |
| `input_params` / `output_params` | arrays | See below. **Empty `[]` on integration nodes.** |
| `edges` | array | Outgoing edges. |

To end a branch, use `"node_type": "exitNode"` on a node with no outgoing
edges. The builder sets `isExitNode` and omits a tool configuration. Do not set
an `is_exit` field directly.

---

## Defaults — what you can omit

Keep specs minimal. Include a field only when it differs from the default.

| Field | Default |
|-------|---------|
| `is_entry` | `false` |
| `node_type` | `null` (auto) |
| `x`, `y` | auto-laid-out by graph depth (provide **both** to override) |
| `model` | `BEDROCK_CLAUDE_SONNET_4` |
| `tool_description` | `""` |
| `on_error` | `"STOP"` |
| `enable_retry` / `retry_count` / `retry_wait_ms` | `false` / `1` / `1000` |
| `fallback_models` | `null` |
| `evaluation_criteria` | `[]` |
| `prompt` | `""` |
| input param `required` | `true` |
| input param `fill_type` | `"user_fill"` |
| input param `is_array` | `false` |
| edge `condition` | `""` |
| `parent` | `null` |

---

## Input params

Each input param the node consumes:

```json
{
  "name": "topic",
  "description": "What the user wants the blog written about",
  "type": "string",
  "is_array": false,
  "fill_type": "ai_fill",
  "static_value": null,
  "linked_node": null,
  "linked_param": null,
  "required": true,
  "position": 0
}
```

`type` is one of `string`, `number`, `boolean`, `object`. `position` is the
0-based order.

### Fill types

How the param's value is supplied at runtime:

| `fill_type` | Use when |
|-------------|----------|
| `ai_fill` | **Default for the first node after entry**, and whenever the AI should determine the value from the task context. The user's chat message is free-form ("write about dragons"); the AI extracts `topic`. Also used for integration params like a Gmail recipient the AI infers from instructions. |
| `linked` | The value is a specific upstream node's output. Set `linked_node` (that node's `key`) and `linked_param` (its output param `name`). |
| `static` | A fixed value that never changes. Set `static_value`. |
| `user_fill` | The Beam agent has a dedicated form field the user fills at runtime. **Not** for values extracted from the chat message — use `ai_fill` for those. |

`ai_fill` vs `linked`: if you know the exact source node and param, use
`linked`. If the value merely exists somewhere in context, or the AI must
compose it, use `ai_fill`.

**Design for `linked`.** A reliable agent extracts each piece of data once, in
an upstream node, as a named output param — then every downstream node that
needs it uses a `linked` input pointing at that source. Prefer `linked`
wherever a source exists: it is deterministic, whereas `ai_fill` re-guesses the
value on every run. Reserve `ai_fill` for the entry-adjacent node (which reads
the user's free-form message) and for merge points fed by multiple branches.

A `linked` param fails to deploy if `linked_node`/`linked_param` do not match a
real upstream node key and output param name — `beam.py` reports which keys are
available.

---

## Output params

Each distinct piece of data the node produces. Downstream nodes link to these
by `name`.

```json
{
  "name": "blog_title",
  "description": "A punchy blog post title",
  "type": "string",
  "is_array": false,
  "position": 0
}
```

Give outputs descriptive names — a downstream `linked` param references them.

---

## Edges

An outgoing connection. Listed in the source node's `edges` array.

```json
{ "target": "next-node-key", "condition": "", "condition_groups": null }
```

- `target` — the `key` of the destination node.
- `condition` — for `conditionNode` (`llm_based`) edges, a natural-language
  string. `""` on a normal sequential edge.
- `condition_groups` — for `conditionNode` (`rule_based`) edges only.

**A non-condition node has exactly one outgoing edge** (or zero if it is the
last node). Multiple unconditional edges from one node is not "run both" — it is
unsupported. To run several actions, chain them.

---

## Node types

| `node_type` | Purpose | `toolConfiguration` | `node_configurations` |
|-------------|---------|---------------------|------------------------|
| `entryNode` | Entry point. Bare — no tool, no params, `objective: "Entry Node"`. | No | No |
| `executionNode` | Default. Runs one tool (custom GPT prompt or an integration). | Yes | No |
| `conditionNode` | Branches the flow. | No | Yes |
| `waitingNode` | Pauses the flow. | Yes | Yes |
| `loopingNode` | Repeats a sub-flow (a fixed count, or once per list item). | No | Yes |
| `exitNode` | Terminates a branch without executing a tool. | No | No |

The entry node is always: `{ "key": "entry", "name": "Entry", "objective": "Entry Node", "is_entry": true, "edges": [{ "target": "..." }] }` — nothing else.

---

## Integration nodes and the integrations array

An integration node runs a managed tool (Gmail, Slack, …) instead of a custom
prompt. Define it in **two places**:

**1. In `nodes`** — a minimal node, params left empty, prompt empty:

```json
{
  "key": "send-email",
  "name": "Send Email",
  "objective": "Email the finished blog post via Gmail",
  "model": "GPT4_1_MINI",
  "edges": []
}
```

Rules for the node entry:
- `input_params` and `output_params` stay **empty `[]`** (omit them) — the
  integration supplies its own. Putting params in both places causes conflicts.
- `prompt` stays `""` (omit it).
- `model` should be a capable extraction model (e.g. `GPT4_1_MINI`,
  `GEMINI_3_FLASH`) — **not** the integration's `preferredModel`, which is often
  a legacy model.
- It still needs a unique `key`, `name`, `objective`, and correct `edges`.

**2. In `integrations`** — the actual tool config:

```json
{
  "node_key": "send-email",
  "tool_function_name": "GmailAction_SendEmail",
  "tool_name": "Send Email",
  "description": "Send an email from Gmail",
  "icon_src": null,
  "preferred_model": null,
  "requires_consent": true,
  "input_params": [
    { "paramName": "email_address", "fillType": "ai_fill", "paramDescription": "Recipient", "dataType": "string", "required": true, "position": 0 },
    { "paramName": "subject", "fillType": "linked", "paramDescription": "Subject", "dataType": "string", "required": true, "position": 1,
      "linked_from_key": "write-blog", "linked_from_param": "blog_title" }
  ],
  "output_params": [
    { "paramName": "message", "paramDescription": "Send result", "dataType": "string", "position": 0 }
  ]
}
```

| Field | Meaning |
|-------|---------|
| `node_key` | The `key` of the node (in `nodes`) this tool attaches to. |
| `tool_function_name` | Exact value from `search-tools` (e.g. `GmailAction_SendEmail`). |
| `tool_name` / `description` / `requires_consent` | Tool metadata from `search-tools`. |
| `icon_src` / `preferred_model` | Optional — leave `null`. The node's model is set on the node entry in `nodes`, not here. |
| `input_params` | The tool's inputs. Note the **camelCase** field names here (`paramName`, `fillType`, `paramDescription`, `dataType`) — different from a custom node's snake_case input params. |
| `output_params` | Usually **omit** (leave `[]`). Beam publishes no output schema for integration tools, so a downstream node must not `link` to an integration output — see the note below. |

**Consuming an integration's result:** the node *after* an integration node
reads its output with `ai_fill`, **not** `link`. The integration node is
directly upstream, so its result is already in the run context. A `link` would
need a real output-param name, and Beam has no schema for an integration tool's
outputs — a guessed name that misses the tool's true output fails at run time.
So never `link` from an integration output; use `ai_fill`.

On a `linked` integration input param, use `linked_from_key` (source node key) +
`linked_from_param` (source output param name). `deploy` resolves these to the
real UUIDs after the agent is created — you never write UUIDs. If the tool's
param takes a list (e.g. a Google Sheets "append rows" `data` arg), set
`isArray: true` on the integration param and link it to an upstream output that
is itself `is_array: true` — an array output links to an array param.

For a **fixed value** on an integration param (e.g. a Slack `channel`), use
`fillType: "static"` with `staticValue: "<value>"`. (`beam.py` also accepts the
snake_case `static_value` and normalizes it — either works.) `verify-links`
reports a `static` param with an empty value as BROKEN.

`deploy` attaches every integration, then re-links any downstream node whose
linked source UUIDs changed, then verifies. `create` does **not** attach
integrations — always use `deploy` when the spec has an `integrations` array.

---

## Condition nodes

A `conditionNode` branches the flow: exactly one outgoing edge is taken. Pick
**one** condition type per node.

| `conditionType` | Use for | Edge carries |
|-----------------|---------|--------------|
| `llm_based` | Semantic/intent branching ("customer wants a refund"). | A `condition` string the routing LLM matches. |
| `rule_based` | Deterministic comparisons on upstream output params (numbers, exact matches). | A `condition_groups` array of structured rules. |

A graph may mix condition types across different nodes, but a single node uses
one type. Edges are evaluated **in order — first match wins**. A condition node
has no `toolConfiguration`, `prompt`, or `model`.

**Every edge must carry an explicit, non-empty condition.** There is no blank
fallback. "If X do A, otherwise B" produces two edges: one with the condition
for X, one with the explicit complement (NOT X). Add a catch-all edge only for
genuinely unhandled cases, and write its condition out (e.g. `"any input that
does not match the branches above"`); place it last.

### `llm_based`

```json
{
  "key": "route",
  "name": "Route Request",
  "objective": "Route the request to the right handler",
  "node_type": "conditionNode",
  "node_configurations": { "conditionType": "llm_based", "llmModel": "GPT4_1_MINI", "fallbackModels": null },
  "edges": [
    { "target": "sales",   "condition": "the customer is asking about pricing or buying" },
    { "target": "support", "condition": "the customer needs technical help or reports a problem" },
    { "target": "general", "condition": "any request that is not about sales or support" }
  ]
}
```

### `rule_based`

Each edge gets a `condition_groups` array. Rules inside a group join via
`nextRuleOperator` (`AND`/`OR`); groups join via `nextGroupOperator`. A rule
references the upstream node by its **spec key** (`sourceNodeKey`) — `beam.py`
resolves it to a UUID.

Operators: `equals`, `not_equals`, `greater_than`, `less_than`, `contains`,
`does_not_contain`, `starts_with`, `ends_with`, `is_empty`, `is_not_empty`.
Comparison value types: `static` (a literal) or `output_param` (another node's
output, via `comparisonNodeKey` + `comparisonOutputParamName`).

```json
{
  "key": "score-router",
  "name": "Score Router",
  "objective": "Route based on the evaluator score",
  "node_type": "conditionNode",
  "node_configurations": { "conditionType": "rule_based", "llmModel": null, "fallbackModels": null },
  "edges": [
    {
      "target": "approve", "condition": "score > 80",
      "condition_groups": [
        { "rules": [
            { "sourceNodeKey": "evaluator", "sourceOutputParamName": "score",
              "operator": "greater_than", "comparisonValueType": "static",
              "comparisonValue": "80", "nextRuleOperator": null } ],
          "nextGroupOperator": null }
      ]
    },
    {
      "target": "reject", "condition": "score <= 80",
      "condition_groups": [
        { "rules": [
            { "sourceNodeKey": "evaluator", "sourceOutputParamName": "score",
              "operator": "less_than", "comparisonValueType": "static",
              "comparisonValue": "81", "nextRuleOperator": null } ],
          "nextGroupOperator": null }
      ]
    }
  ]
}
```

The two edges above are exhaustive complements — no fallback edge needed. To
compare against another node's output: set `"comparisonValueType": "output_param"`,
`"comparisonNodeKey": "config-loader"`, `"comparisonOutputParamName": "expected"`.

---

## Waiting nodes

A `waitingNode` pauses the flow, then resumes to its single outgoing edge. It
cannot be the entry node and has exactly one outgoing edge.

| `waitType` | Use for | Config |
|------------|---------|--------|
| `time_based` | A fixed delay. | `timeToWaitValue` + `timeToWaitUnit` (`minutes`/`hours`/`days`/`months`). |
| `condition_based` | Waiting for a reply to a tool the flow already invoked (e.g. an email reply). | `linkedNodeKey` — the spec key of the upstream tool node whose reply you await. |

### `time_based`

```json
{
  "key": "wait-2-days",
  "name": "Wait 2 Days",
  "objective": "Wait two days before the follow-up",
  "node_type": "waitingNode",
  "node_configurations": { "waitType": "time_based", "timeToWaitValue": 2, "timeToWaitUnit": "days", "timeoutType": "no_timeout" },
  "tool_name": "Wait",
  "prompt": "",
  "edges": [{ "target": "send-followup" }]
}
```

### `condition_based`

Three constraints — **all** must hold, or use `time_based` instead:

1. The linked tool must support waiting — its `allowWaiting` must be `true`
   (check `search-tools` results, or `get-node` on an existing node).
2. The linked tool must be **directly upstream** of the wait node.
3. **No node** may sit between the linked tool and the wait node — the linked
   tool's edge connects straight to the wait node. (The wait handler subscribes
   to the reply when the wait node runs; anything in between can miss the reply.)

```json
{
  "key": "wait-for-reply",
  "name": "Wait for Email Reply",
  "objective": "Wait until the recipient replies to the sent email",
  "node_type": "waitingNode",
  "node_configurations": {
    "waitType": "condition_based",
    "linkedNodeKey": "send-email",
    "timeoutType": "set_timeout",
    "timeoutValue": 48,
    "timeoutUnit": "hours",
    "onTimeout": "continue"
  },
  "tool_name": "Wait",
  "prompt": "",
  "edges": [{ "target": "process-reply" }]
}
```

`linkedNodeKey` is the upstream send node's spec key; `beam.py` resolves it.
**Timeout** (both wait types): `timeoutType: "no_timeout"` (default) or
`"set_timeout"` with `timeoutValue` + `timeoutUnit` + `onTimeout`
(`"continue"` falls through to the next node, `"fail"` stops the run).

**No awaitable tool? Fall back to `time_based`.** If the goal wants to wait on a
human reply (e.g. a Slack approval) but no messaging tool reports
`allowWaiting: true`, `condition_based` is impossible. Use a `time_based` wait
sized to the goal's own deadline ("give them two days" → 2 days), then place a
`conditionNode` immediately after it that reads the reply from run context and
branches on it. One `time_based` wait plus a downstream condition covers both
outcomes the goal asks for — they replied, and they did not.

---

## Looping nodes

A `loopingNode` repeats a sub-flow — either a fixed number of times, or once per
item in an upstream array. It is a **container**: the nodes that run inside the
loop are ordinary nodes that name the loop through a `parent` field. A
`loopingNode` has no `toolConfiguration` and no `prompt`.

Pick exactly one loop mode, set in `node_configurations`:

| Loop mode | `node_configurations` | Behaviour |
|-----------|----------------------|-----------|
| Count-based | `{ "iterationCount": 3 }` | Runs the loop body a fixed number of times. |
| Variable-based | `{ "linkedVariableId": "<sourceNodeKey>:<paramName>" }` | Runs the loop body once per element of the named upstream array output param. `beam.py` resolves `<sourceNodeKey>` to a UUID. |

**Structure:**

- The loop node sits in the normal edge flow — an upstream node's edge points at
  it, and it points to the node that runs **after all iterations complete**.
- **Body nodes** are ordinary `executionNode` / `conditionNode` / `waitingNode`
  nodes that add `"parent": "<loopNodeKey>"`. `beam.py` resolves the key to the
  loop node's id (`parentNodeId`). Backend-generated numeric aliases on body
  nodes are internal result-aggregation metadata; do not include `alias` in a
  spec or treat it as an iteration variable.
- Body-to-body edges remain inside the sub-flow. Do not add loop-to-body or
  body-to-outside edges. If an older spec contains them, `beam.py` normalizes
  them to the canonical loop-to-next-step edge before deploying.

**Constraints:** a `loopingNode` cannot be the entry node, and loops cannot nest
(a `loopingNode` cannot itself carry a `parent`).

**Params in and out of a loop:** a variable-loop body input that needs the
current element uses `fill_type: "linked"` to the same upstream array output as
`linkedVariableId`. Agent OS resolves that link to the current array element by
iteration index. A node *after* the loop that consumes accumulated body results
uses `ai_fill` with `is_array: true` (the per-iteration outputs accumulate into
an array, not a single node output).

```json
{
  "key": "summarize-loop",
  "name": "For Each Article",
  "objective": "Loop over each candidate article",
  "node_type": "loopingNode",
  "node_configurations": { "linkedVariableId": "list-articles:articles" },
  "edges": [{ "target": "compile-digest" }]
},
{
  "key": "summarize-article",
  "name": "Summarize Article",
  "objective": "Summarize the current article",
  "parent": "summarize-loop",
  "prompt": "## Role:\n...\n\n## Context:\n```\n{article}\n```\n\n## Rules:\n1. ...",
  "input_params": [
    { "name": "article", "description": "Current loop item", "type": "string", "fill_type": "linked", "linked_node": "list-articles", "linked_param": "articles", "position": 0 }
  ],
  "output_params": [ { "name": "summary", "description": "...", "type": "string", "position": 0 } ],
  "edges": []
}
```

Flow: `list-articles -> summarize-loop -> compile-digest`, while
`summarize-article (parent: summarize-loop)` runs once per array element.
See `assets/example-specs/loop-article-digest.json` for the full spec.

**A loop body that emits several outputs.** The example above loops a body with
one output (`summary`). When the body node has *multiple* output params, each
accumulates into its own array across iterations. The node *after* the loop then
takes one `ai_fill` input per output, each `is_array: true` — e.g. a body
emitting `name`, `price`, `blurb` feeds a compile node with three `is_array`
inputs. The arrays are index-aligned (entry `i` of each is the same iteration),
so the compile prompt should pair them by position.

**`linkedVariableId` on a deployed loop.** In the spec you write
`linkedVariableId` as `"<sourceNodeKey>:<paramName>"`. `beam.py` resolves it to a
UUID at deploy time, so `get-node` on a live loop reads it back as a bare UUID —
that is expected, not a different field.

---

## Flow patterns

Beam executes nodes **sequentially — no parallelism**.

**Sequential chain (do ALL of several things):** chain the nodes; each has one
edge to the next.

```
Write Blog -> Send Slack -> Send Email
```

**Conditional branching (do ONE of several things):** a condition node; only the
matched branch runs.

```
Classify -> {Condition} --urgent--> Slack Alert
                        --normal--> Log
```

**Merge (branches converge on one final action):** several branches point their
edges at the same node — do not duplicate the action on each branch. The merge
node has multiple parent edges; use `ai_fill` (not `linked`) on its input params
because the data comes from whichever branch ran.

```
Spam Reply  --\
               >--> Send Reply (Gmail)
Normal Reply --/
```

For the full "what the user said → pattern" translation table (including waiting
and looping shapes), see `patterns/flow-patterns.md` — it is the single owner of
graph shapes; this file owns the schema.

---

## Minimal example

```json
{
  "agentName": "Story Writer",
  "agentDescription": "Writes a short story from a topic",
  "nodes": [
    { "key": "entry", "name": "Entry", "objective": "Entry Node",
      "is_entry": true, "edges": [{ "target": "write" }] },
    { "key": "write", "name": "Write Story", "objective": "Write a short story",
      "prompt": "## Role:\nYou are a fiction writer.\n\n## Task:\nWrite a short story on the topic.\n\n## Context:\n```\n{topic}\n```\n\n## Rules:\n1. 300-600 words.\n2. Output story_title and story_body.",
      "input_params": [
        { "name": "topic", "description": "Story topic", "type": "string", "fill_type": "ai_fill", "position": 0 }
      ],
      "output_params": [
        { "name": "story_title", "description": "Title", "type": "string", "position": 0 },
        { "name": "story_body", "description": "Full story", "type": "string", "position": 1 }
      ],
      "edges": [] }
  ]
}
```

See `assets/example-specs/` for fuller examples (integration, condition,
waiting, looping).

---

## Update-merge semantics

When you run `deploy --agent-id <id>`, `beam.py` merges your spec onto the live
graph:

- **Existing node matched** (by `toolFunctionName`, derived from `tool_name`) →
  kept, with its prompt, params, and integration intact; edges are rewired.
- **New spec node, no match** → built fresh.
- **Existing node not in your spec → dropped.**

Therefore: a full redeploy must include **every node you want to keep**, and
node `name`/`tool_name` values must stay stable across updates so matching
works. For small changes, prefer the quick-update commands
(`update-node-prompt`, `add-node`, etc.) — they never risk dropping a node.

**Node ids change on every full-graph write.** Any operation that PUTs the whole
graph — `deploy --agent-id`, `add-node`, `remove-node`, `update-metadata` —
makes the API assign **new** node ids (the id you send becomes a `customId`
alias). A node id captured before such an op is stale afterward, so **re-run
`get-nodes` after any of them before using a node id again.** The targeted
patches (`update-node`, `update-node-prompt`, `update-node-params`,
`update-edge`) do not change ids. Triggers bind to a node id, so a full-graph
write also drops existing triggers — add triggers only once the graph is final.
