# Tool Taxonomy

Load when picking a tool type for a node, naming a node, or auditing whether a graph reads clearly on the Beam canvas.

The five categories drive naming, icon style, and the `requiresConsent` / `onError` defaults. Get the category right and the graph becomes scannable for a reviewer or a buyer.

**Color discipline: colorful = external system touchpoint; monochrome = internal reasoning or system primitive.** This makes the canvas instantly readable.

---

## The 5 categories

| Category | What it does | Naming convention | `requiresConsent` / `onError` |
|---|---|---|---|
| **1. Custom GPT — reasoning** | Parses, classifies, validates, decides, scores, drafts, summarises, maps — over inputs already in the graph | Provider-free, named for the cognitive job: `Invoice Exception Classifier`, `Compliance Decision Maker`, `Craft Marketing Ops Alert` | false / STOP |
| **2. Custom GPT — mock integration** | Pretends to call an external system inside a demo; produces a provider-shaped request + mock result + audit note | Provider-prefixed: `Slack Post Channel Message`, `Monday.com Update Item Status`, `Braze Schedule Content Card` | false / STOP |
| **3. Real integration** | Calls an actual installed connector — sends email, updates Salesforce, posts to Slack, etc. | Same provider-prefixed pattern as mocks; `toolFunctionName` is the real Beam action (`GmailAction_SendEmail`, `SalesforceAction_UpdateRecord`) | **true for writes** / STOP; false / CONTINUE for best-effort tagging |
| **4. System actions** | Beam primitives: trigger another agent, run deterministic code | Fixed names: `BeamSystemAction_TriggerAgent`, `StandAloneAction_CodeExecutor` | false / CONTINUE (TriggerAgent — fire-and-forget); false / STOP (CodeExecutor — fail loudly) |
| **5. Condition node** | Routes between branches — no tool, no prompt | n/a — `nodeType: conditionNode` | n/a |

---

## The compose/send split rule

Never bundle "draft a message + send it" into one node. Split into two:

| Wrong (bundled) | Right (split) |
|---|---|
| `Slack Create Message` | `Craft Slack Message` (Cat 1) → `Slack Post Channel Message` (Cat 2/3) |
| `Braze Content Card Payload Mapper` | `Content Card Payload Mapper` (Cat 1) → `Braze Schedule Content Card` (Cat 2/3) |
| `Salesforce Decide Owner Reassignment` | `Owner Reassignment Decision Maker` (Cat 1) → `Salesforce Update Record Owner` (Cat 3) |

Why this matters:
- The reasoning step can be smoke-tested independently without touching the external system
- The integration step gets `requiresConsent: true` without freezing the reasoning step behind a consent gate
- The audit trail separates "what was decided" from "what was sent" — essential for Learning feedback

---

## Category 1 — Custom GPT reasoning

**Use when** the node parses, classifies, validates, decides, drafts, summarises, scores, maps, or transforms over inputs already in the graph.

**Anti-patterns:**
- `Monday.com Parse Ready Status` (you're just parsing a webhook that already arrived) → `Banner Ready Status Parser`
- `Slack Create Message` (you're drafting copy, not sending) → `Craft Slack Message`

**Use CodeExecutor instead** (Category 4) when the work is deterministic: arithmetic, threshold checks, format coercion, schema coercion, table lookups, enum combination. Custom GPT re-guesses every run; CodeExecutor is deterministic and cheaper.

---

## Category 2 — Custom GPT mock integration

**Use when** the connector is not installed, credentials are unavailable, or the demo should not touch a production system.

Required prompt guardrail on every mock node:
> Do not call `<provider>`. Set `mode="mock"`. Include an `audit_note` saying no external API call was made. Preserve all concrete source facts (IDs, amounts, dates, flags) from `task_context` and `previous_node_output`.

**Anti-pattern:** using a mock when a real connector exists and the customer signed off. Mocks in production hide consent gates and produce no auditable trail.

---

## Category 3 — Real integration

`toolFunctionName` comes from `search-tools`. Use `--managed-only` to filter to real connectors. Provider priority: `nango_cloud` → `pipedream` → ask before `custom_gpt_tool`.

`requiresConsent: true` on any node that writes, sends, updates, or deletes in an external system. Use `onError: CONTINUE` only for best-effort tagging or fire-and-forget sidecars where a failure should not halt the main flow.

---

## Category 4 — System actions

**`BeamSystemAction_TriggerAgent`** — fires a downstream agent without blocking the main flow. Use for sidecars (audit logging, parallel notifications). `onError: CONTINUE`. Requires exactly 3 input params: `agentName` (static), `urls` (ai_fill), `payload` (linked).

**`StandAloneAction_CodeExecutor`** — runs deterministic JavaScript inside a node. Use for: arithmetic, threshold checks, parsing structured data, format coercion, building lookup results. `onError: STOP` — deterministic code should fail loudly. `code_language: "javascript"`, `code` must be non-empty.

**Before designing a CodeExecutor node:** verify a working example exists in `assets/example-specs/` or that `beam.py` has explicit handling for it (`grep -n CodeExecutor scripts/beam.py`). If neither confirms within 2 lookups, fall back to a Custom GPT executionNode — it is simpler, proven, and costs only 1–2 cr more per run. Do not spend more than 2 tool calls investigating CodeExecutor configuration.

---

## Category 5 — Condition node

`nodeType: conditionNode`. No `toolFunctionName`, no `prompt`. Routes the flow — does not do work.

- `conditionType: rule_based` — uses explicit field comparisons (`score > 80`, `status = "approved"`)
- `conditionType: llm_based` — LLM evaluates a natural language condition; use a cheap model (`GPT4_1_MINI`, `GEMINI_25_FLASH`)
- Every condition node must have a default/fallback edge
- Branch labels must be explicit and non-empty — never blank, "yes", "no", or "default"
- Do not chain condition nodes directly — insert an execution node between them
