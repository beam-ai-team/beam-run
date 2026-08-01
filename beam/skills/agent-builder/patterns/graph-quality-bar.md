# Graph Quality Bar

Load when drafting a new agent or reviewing an existing one. This is the readiness bar before smoke testing or publishing.

---

## Workflow shape

- The agent owns **one durable job** — not a whole department. If the design covers more than one distinct business process, split into two agents.
- Use nodes for meaningful workflow boundaries: extraction, lookup, validation, routing, review, action, notification, handoff.
- Use condition nodes for routing only — not for doing work. A condition node asks one routing question with business-readable outcomes.
- End on real action nodes with no outgoing edge. Do not add synthetic exit nodes or `is_exit` markers.
- **Avoid graphs above ~15 nodes** unless the demo genuinely needs that complexity. If you are approaching 15, ask: can this workflow be narrowed to a tighter slice?

---

## Data flow

- Every non-entry execution node needs a visible data contract (inputs and outputs).
- Target 3–5 input params and 3–5 output params per custom GPT node. More than 5 is a sign the node is doing two jobs.
- Prefer simple `string` or `enum` fields. Use `object` only when a downstream node needs structured machine-readable data, and always populate `objectSchema`.
- Every input param referenced in a GPT prompt must appear in `inputParams` with the matching `paramName`.
- Use `previous_node_output` for the generic upstream context param on GPT nodes. Do not use `prior_node_outputs`.
- Execution nodes may have multiple incoming edges (the merge pattern), but such a
  node must read its inputs with `ai_fill` — never `linked`, which cannot resolve
  across branches. Prefer duplicating branch-specific nodes when each branch needs
  genuinely different handling.

---

## Tool semantics

- Action/integration nodes must use workflow-specific visible tool names — not the generic `Step by Step Guide`.
- Provider-prefixed names mean the tool reads from, writes to, or triggers an external system: `Monday.com Get Banner Columns`, `Braze Schedule Content Card`, `Slack Post Ops Alert`.
- Provider-free names mean the tool performs reasoning or transformation inside the agent: `Compliance Decision Maker`, `Invoice Exception Classifier`, `Craft Marketing Ops Alert`.
- Do not name a reasoning step after the provider whose data it consumes — `Monday.com Parse Status` when you are just parsing a field → `Banner Status Parser`.
- The graph is not ready if most execution nodes show the same generic visible tool name.

---

## Prompt safety

- GPT-backed nodes must never ask the user for input during task execution.
- GPT-backed nodes must never return an empty result (`[]`, `{}`, or blank string). Add a fallback rule: "If you cannot extract X, return `'unknown'`."
- Demo-safe does not mean generic. Preserve concrete source facts from inputs: names, IDs, amounts, dates, flags, policy numbers. Do not replace real values with `demo_policy_123`, `Spring Sale`, or fake dates.
- Reasoning nodes must not claim external side effects. Mock integration nodes must explicitly state no live API call was made.

---

## Conditions and edges

- Every condition node must have a default/fallback edge covering the unmatched case.
- Branch labels must be concise and explicit: "If validation is successful", "If information is missing". Never: blank, "yes", "no", "success", "failure", "default", "else".
- Simple sequential edges must be unlabelled — no `condition` text, no `name` text.
- Do not connect condition nodes directly to condition nodes — insert an execution node between them.
- Do not let a condition branch shortcut directly into a shared downstream node while sibling branches pass through intermediate nodes first. Use branch-specific pass-through nodes, or split early terminal outcomes.

---

## Common failure modes

- **Terminal node produces JSON but never acts** — the agent decides something but
  nothing happens. Add a real action node after the decision. This applies only when
  the user asked for the action: if the brief stops at "draft a reply" or "classify
  it", a terminal node that emits the draft is the correct shape (see
  `assets/example-specs/condition-ticket-router.json`). Do not invent a send step the
  user did not ask for — that violates the "never assume integrations" rule.
- **Every node uses the same frontier model** — simple extraction and routing nodes should use Flash/Mini-tier models. Only complex reasoning justifies Sonnet/Opus.
- **Integration nodes have a non-empty prompt** — integration nodes must have `prompt: ""`. The integration handles execution; a prompt here conflicts with the tool's built-in behaviour.
- **Condition edges are blank** — the routing logic is invisible. Every branch label must describe the condition it represents.
- **Node named after what it consumes, not what it does** — `Salesforce Get Record` (when you are just parsing a field you already have) → `Renewal Risk Classifier`.
