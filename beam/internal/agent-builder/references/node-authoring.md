# Node Authoring Reference

How to write a custom GPT node's `prompt`, and how to pick its `model`.

## Contents

- [The 4-section prompt structure](#the-4-section-prompt-structure)
- [Section guidelines](#section-guidelines)
- [Example prompts](#example-prompts)
- [Model selection](#model-selection)

---

## The 4-section prompt structure

Every **custom GPT node** (a node that is not an integration, not a condition
node, not a waiting node) must have a `prompt` built from these sections, in
this order. The structure is not decoration — Beam's runtime injects each input
param's value into the matching fenced block in `## Context:`, so the headers
and fences are load-bearing.

```
## Role:
You are a [specific role]. [One sentence on expertise or perspective.]

## Task:
[One clear instruction — what to do. Start with a verb. One paragraph max.]

## Context:
```
{input_param_name}
```

## Rules:
1. [A constraint or quality bar]
2. [The output format — name the output params the node produces]
3. [Edge-case handling]

## Examples:
[Optional. Few-shot input/output pairs — see "When to add Examples" below.]
```

Rules:
- The first four sections (`## Role:`, `## Task:`, `## Context:`, `## Rules:`)
  are **required** on every custom node.
- `## Context:` gets **one fenced code block per input param**, each containing
  exactly `{param_name}`. A node with `topic` and `tone` inputs has two fenced
  blocks. A node with no inputs still has the header (leave it empty or note
  "no input").
- Never write a plain-text prompt. Never rename or skip the required sections.
- Integration nodes and waiting nodes use `prompt: ""` — this structure does not
  apply to them.

In a JSON spec the prompt is a single string with `\n` newlines. The fenced
blocks are triple backticks — escape them as needed for valid JSON.

---

## Section guidelines

| Section | Purpose | Guidance |
|---------|---------|----------|
| `## Role:` | Sets the persona. | Be specific. "You are a senior copywriter" beats "You are helpful." |
| `## Task:` | The action. | One instruction, starts with a verb. |
| `## Context:` | Injects input data. | One fenced `{param_name}` block per input param — this is where runtime values land. |
| `## Rules:` | Constraints + output contract. | Numbered list. Always state the output format and name the output params. Cover edge cases and quality bars. |
| `## Examples:` | Few-shot anchoring. | Optional. Realistic input/output pairs. |

### When to add `## Examples:`

Add it when a plain description plus rules would leave room for
misinterpretation:

- Classification or routing with non-obvious categories.
- Data extraction or transformation with a specific output shape.
- Tasks where tone, style, or structure is hard to describe in words alone.

Skip it for simple, well-defined tasks ("summarize this", "translate to
Spanish") — the rules already pin those down.

---

## Example prompts

**Simple task — no Examples section.** A "Write Story" node, input `topic`:

```
## Role:
You are a creative fiction writer specializing in short stories. You craft
vivid, engaging narratives with strong characters.

## Task:
Write a compelling short story based on the provided topic.

## Context:
```
{topic}
```

## Rules:
1. Length: 500-1000 words.
2. Include a title at the beginning.
3. Use vivid sensory detail and dialogue.
4. End with a satisfying resolution — no cliffhangers.
5. Output two fields: story_title (just the title) and story_body (the full text).
```

**Complex task — with Examples.** A "Classify Support Ticket" node, input
`ticket_message`:

```
## Role:
You are a customer support triage specialist who classifies tickets by
department and urgency with high accuracy.

## Task:
Classify the support ticket into a department and an urgency level.

## Context:
```
{ticket_message}
```

## Rules:
1. department must be one of: billing, technical, account, general.
2. urgency must be one of: critical, high, medium, low.
3. critical = service down or a security issue; high = a blocked user;
   medium = degraded experience; low = a question or feature request.
4. When torn between two departments, pick the one handling money if billing
   is involved.

## Examples:
Input: "I was charged twice for my subscription and need a refund ASAP"
Output: department = billing, urgency = high

Input: "The dashboard has been down for 2 hours, nobody on my team can log in"
Output: department = technical, urgency = critical

Input: "How do I add a new teammate to my workspace?"
Output: department = account, urgency = low
```

---

## Model selection

Set each node's `model` field to a token from the **workspace's live model
catalog**, never from memory:

```bash
beam agent-builder models
```

The catalog is the only source of truth for three things: which tokens this
workspace accepts, which one is the **default** (a node without an explicit
`model` gets it), and what each model costs in **credits per node run**
(`creditsCost`). It changes between releases and between tenants, which is why
this file carries no model table. `deploy`, `create` and `add-node` report the
`defaultModel` they used and a `modelWarnings` list for any token the catalog
does not list, whether it sits in `model`, `fallback_models`, or a condition
node's `llmModel` and `fallbackModels`; treat a warning as a wrong token, not as
a platform error.

**Cost is a real constraint — pick the cheapest model that does the node's task
reliably.** Start at the lowest `creditsCost` that can do the job and only move
up if the task genuinely needs more. A simple extraction or a routing decision
must not run on a frontier model just because one is listed; every node runs on
every task.

### Reading the catalog

| Field | Use it for |
|-------|------------|
| `modelValue` | The exact token to write into `model` |
| `isDefault` | What a node gets when `model` is omitted; the sensible standard choice |
| `creditsCost` | Credits per node run at that model; the cost line of every projection |
| `supportsReasoning` | Needed only for genuinely multi-step reasoning; costs more |
| `isPremium` | Frontier tier; reserve for the hardest generation or analysis |

### By task complexity

| Task | Pick |
|------|------|
| **Simple** — extraction, formatting, classification, integration and condition nodes | The cheapest listed model (1 credit where available) |
| **Standard** — summarization, rewriting, data processing | The catalog default, or the cheapest non-premium model that handles the length |
| **Complex** — nuanced writing, multi-step logic, large structured objects | A `supportsReasoning` or `isPremium` model, with a stated reason |
| **Long context** — documents over ~100k tokens | A long-context model from the catalog (the Gemini Pro line at the time of writing; confirm in the catalog) |

### Selection rules

1. **Cheapest model that does the job — this is the primary rule.** If a cheaper
   model produces the same result, use the cheaper one.
2. **Match capability to complexity.** The cheapest tier fails at nuanced
   writing; a premium model on simple formatting wastes money.
3. **The default is for genuinely standard work when unsure**, not a blanket
   choice for every node.
4. **Integration and condition nodes are cheap by nature.** They extract
   parameters or route — they do not generate. Give them the cheapest listed
   model. Never use an integration tool's legacy `preferredModel`.
5. **Escalate only with a clear reason.** Reserve premium and reasoning models
   for work whose task plainly justifies the cost.
6. **Object-assembling nodes still need headroom.** A large JSON object
   truncates on the cheapest tier; use a mid-tier model and cap value lengths.

---

## Cost projection

Use this section when cost, volume, or model choice affects the user's decision.
Do not require a cost projection merely to obtain flow approval.

### Credit rates

| Plan | 1 credit costs |
|------|---------------|
| Pro (standard) | $0.10 |
| Enterprise | $0.049 |

Plan rates have no live source; these are as of September 2026. Confirm with the account owner before quoting.

### Credits per node run

Take `creditsCost` from `beam agent-builder models` for every LLM node: it is the
charge per run at that model. Nodes without an LLM call are near-free:

| Node | Est. credits/run |
|------|-----------------|
| LLM node (custom GPT, `llm_based` condition) | the model's `creditsCost` |
| Integration node | 0–1 |
| CodeExecutor node | 0–1 |

### Projection formula

```
credits_per_task  = sum of estimated credits across all nodes
                    (weight branching agents by expected branch distribution)

cost_per_task     = credits_per_task × credit_rate
                    Pro: × $0.10   |   Enterprise: × $0.049

monthly_cost      = cost_per_task × monthly_volume
weekly_cost       = cost_per_task × weekly_volume
annual_cost       = monthly_cost × 12
```

### Example

Agent: 5 nodes (Entry + 2 GPT standard + 1 condition + 1 Slack integration)
- Entry: 0 cr
- GPT node 1 (standard): ~5 cr
- GPT node 2 (standard): ~5 cr
- Condition (llm_based): ~2 cr
- Slack integration: ~1 cr
- **Total: ~13 credits/task**

At 100 tasks/day (3,000/month):
- Pro: 13 × $0.10 × 3,000 = **$3,900/month**
- Enterprise: 13 × $0.049 × 3,000 = **$1,911/month**

If you present a cost projection and volume is unknown, state the assumption
explicitly. Show two scenarios only when that comparison helps the user decide.
