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

Set each node's `model` field to one of the identifiers below.

**Cost is a real constraint — pick the cheapest model that does the node's task
reliably.** Start at the lowest capability tier and only move up if the task
genuinely needs more. A simple extraction or a routing decision must not run on
a frontier model just because one is available; every node runs on every task.

### Available models by provider

**OpenAI**

| Model | Best for | Cost | Speed |
|-------|----------|------|-------|
| `GPT4_1` | Strong general-purpose, structured output | medium | fast |
| `GPT40` | Multimodal (image/audio), general tasks | medium | fast |
| `GPT40_MINI` | Light tasks — extraction, formatting | low | very fast |
| `GPT4_1_MINI` | Light tasks — extraction, formatting, classification | low | very fast |
| `GPT5` | Most capable OpenAI — complex reasoning | high | moderate |
| `GPT5_MINI` | Good reasoning at lower cost than GPT5 | medium | fast |
| `GPT5_NANO` | Fast reasoning, lightweight tasks | low | very fast |
| `GPT5_2` | Latest GPT5 variant — improved reasoning | high | moderate |

**Anthropic (Bedrock)**

| Model | Best for | Cost | Speed |
|-------|----------|------|-------|
| `BEDROCK_CLAUDE_SONNET_4` | **Default** — most tasks, good quality/speed balance | medium | fast |
| `BEDROCK_CLAUDE_SONNET_4_5` | Complex generation, nuanced writing | high | fast |
| `BEDROCK_CLAUDE_OPUS_4_5` | Hardest tasks — deep reasoning, multi-step logic | highest | slow |
| `BEDROCK_CLAUDE_3_7_SONNET` | Reliable fallback if Sonnet 4 is unavailable | medium | fast |

**Google Gemini**

| Model | Best for | Cost | Speed |
|-------|----------|------|-------|
| `GEMINI_25_PRO` | Strong reasoning, long context (1M tokens) | medium | fast |
| `GEMINI_25_FLASH` | Fast reasoning, cost-effective | low | very fast |
| `GEMINI_25_FLASH_LITE` | Ultra-light, high throughput | lowest | fastest |
| `GEMINI_3_1_PRO` | Long context (1M tokens), complex analysis | medium | fast |
| `GEMINI_3_FLASH` | Fast general tasks, good cost efficiency | low | very fast |
| `GEMINI_3_1_FLASH_LITE` | Ultra-light tasks, highest throughput | lowest | fastest |

**Other**

| Model | Provider | Best for | Cost | Speed |
|-------|----------|----------|------|-------|
| `DEEP_SEEK` | DeepSeek | Coding tasks, technical analysis | low | fast |
| `COMPOUND_BETA` | Groq | Compound AI with tool use, agentic workflows | low | very fast |
| `GPT_OSS_120B` | Groq | Large open-source model via Groq inference | low | very fast |
| `GPT_OSS_20B` | Groq | Small open-source model, fast inference | lowest | fastest |

### By task complexity

| Task | Pick one of |
|------|-------------|
| **Simple** — extraction, formatting, classification | `GPT5_NANO`, `GEMINI_25_FLASH_LITE`, `GEMINI_3_1_FLASH_LITE`, `GPT_OSS_20B`, `GPT40_MINI`, `GPT4_1_MINI`, `GEMINI_3_FLASH` |
| **Standard** — summarization, rewriting, data processing | `GPT4_1`, `GPT40`, `GPT5_MINI`, `BEDROCK_CLAUDE_SONNET_4`, `GEMINI_25_FLASH`, `GEMINI_3_1_PRO`, `DEEP_SEEK` |
| **Complex** — creative writing, nuanced analysis, multi-step logic | `GPT5`, `GPT5_2`, `BEDROCK_CLAUDE_SONNET_4`, `BEDROCK_CLAUDE_SONNET_4_5`, `GEMINI_25_PRO`, `GEMINI_3_1_PRO` |
| **Hardest** — deep reasoning, research, long-form generation | `GPT5`, `GPT5_2`, `BEDROCK_CLAUDE_OPUS_4_5` |
| **Long context** — documents over ~100k tokens | `GEMINI_25_PRO`, `GEMINI_3_1_PRO` |
| **Condition nodes** (`llm_based` routing) | `GPT40`, `GPT40_MINI`, `GPT4_1_MINI`, `GEMINI_3_FLASH`, `GEMINI_3_1_FLASH_LITE` |

### Selection rules

1. **Cheapest model that does the job — this is the primary rule.** Start at the
   lowest tier in the table above that can do the node's task reliably; only
   escalate if the task genuinely needs more capability. If a `low`-cost model
   produces the same result as a `high`-cost one, use the cheap one.
2. **Match capability to complexity.** A `lowest`-tier model fails at nuanced
   writing; a frontier model on simple formatting just wastes money.
3. **`BEDROCK_CLAUDE_SONNET_4` is the default _only_** when a task is genuinely
   "standard" and you are unsure — not a blanket choice for every node.
4. **Integration and condition nodes are cheap by nature.** They extract
   parameters or route — they do not generate. Use a `simple`-tier model
   (`GPT4_1_MINI`, `GEMINI_3_FLASH`). Never use an integration
   tool's legacy `preferredModel`.
5. **Escalate only with a clear reason.** Reserve `high`/`highest`-cost models
   (`BEDROCK_CLAUDE_OPUS_4_5`, `GPT5`, `GPT5_2`) for genuinely hard reasoning or
   long-form generation — the node's task should plainly justify the cost.

---

## Cost projection

Use this section in Phase 2 to calculate the cost of each design option and show it to the user before they approve.

### Credit rates

| Plan | 1 credit costs |
|------|---------------|
| Pro (standard) | $0.10 |
| Enterprise | $0.049 |

### Estimated credits per node run

Credits consumed depend on prompt size + output size at the node's model tier. Use these estimates per node run:

| Node tier | Typical use | Est. credits/run |
|-----------|-------------|-----------------|
| `lowest` / `simple` — Flash Lite, GPT5 Nano, OSS 20B | Extraction, classification, formatting | 1–2 |
| `low` / `simple` — Gemini Flash, GPT4_1_Mini | Light reasoning, short output | 2–4 |
| `medium` / `standard` — Claude Sonnet 4, GPT4_1, Gemini Pro | Summarisation, rewriting, data processing | 4–8 |
| `high` / `complex` — Claude Sonnet 4.5, GPT5, Gemini 2.5 Pro | Creative writing, nuanced analysis | 8–15 |
| `highest` — Claude Opus 4.5, GPT5_2 | Deep reasoning, long-form generation | 15–30 |
| Integration node | No LLM call | 0–1 |
| CodeExecutor node | Deterministic JS | 0–1 |
| Condition node (`llm_based`) | Short evaluation prompt | 1–2 |

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

If volume is unknown, state the assumption explicitly in the State 4 or State 5 display. Show two volume scenarios if the user has given no signal.
