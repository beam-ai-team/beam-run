---
name: agent-builder
description: >-
  Build, configure, deploy, and update Beam AI agents end to end. Use this skill
  whenever the user wants to create a Beam agent, build an agent on the Beam
  platform, design an agent's node flow/graph, attach an integration (Gmail,
  Slack, Outlook, etc.) to a Beam agent, add/remove/edit nodes, wire parameters
  between nodes, set up a trigger or webhook, or publish/deploy a Beam agent.
  Trigger on phrases like "build me a Beam agent", "create an agent that...",
  "add a node to my agent", "change this agent's prompt", "deploy to Beam",
  "attach Slack to the agent", "set up a trigger for the agent", or any mention
  of Beam agents, agent graphs, agent nodes, or the Beam Studio / Beam AI
  platform — even when the user does not say the word "skill".
---

# The Agent Builder

Output this banner on first load, then stop and wait — do not ask questions yet:

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
────────────────────────────────────────────────────
```

---

## Step 0 — Credentials gate (always first)

Before intake, design, or any command, collect all three:

| Variable | Meaning |
|----------|---------|
| `BEAM_API_KEY` | Beam platform API key |
| `BEAM_WORKSPACE_ID` | Workspace UUID |
| `BEAM_API_URL` | Beam API base URL (e.g. `https://api.beamstudio.ai`) |

If any are missing, ask for all three in a single message — and stop there. Then validate:

```bash
BEAM_API_KEY='...' BEAM_WORKSPACE_ID='...' BEAM_API_URL='...' \
  python3 scripts/beam.py validate
```

`{"valid": true}` → proceed. `{"valid": false}` → show the error, ask for corrections. Do not proceed until validate passes. If a later command fails 401/403, ask for fresh credentials and re-validate.

Pass credentials as environment variables on every `beam.py` call. Never write them to a file.

---

## Routing

| Intent | Path |
|--------|------|
| Build a new agent | Phases 1 → 2 → 3 → 4 → 5 → 6 in order |
| Update an existing agent | [Update workflow](#workflow--updating-an-existing-agent) below — direct entry, skip phases 1–3 |

---

## Non-negotiable rules

1. **Credentials before anything.** No intake, search, or design until `validate` passes.
2. **Publishing is a separate, explicit step.** Draft by default. Publish only on: "publish it", "make it live", "ship it". "Deploy", "create", "update", "save", "yes" do not mean publish. After deploying, tell the user it is a draft and ask whether to publish.
3. **Never assume integrations or triggers.** If the user says "notify me" without naming a service, ask which one. Never invent a node the user did not ask for.
4. **`search-tools` before any integration node.** For every integration the design needs, confirm a `toolFunctionName` via `search-tools` before drawing any node. Never design an integration node without a confirmed tool.
5. **`build` is the only build trigger.** Show Mermaid diagram + node table and wait for the user to type `build`. "Yes", "looks good", "go ahead" do not proceed to deploy.
6. **Prefer managed integrations.** When `search-tools` returns multiple matches, pick `integrationProvider: nango_cloud` first, then `pipedream`. Ask before falling back to a custom tool.
7. **Beam runs nodes sequentially — no parallel execution.** Each non-condition node has exactly one outgoing edge. Chain for "do several things" (A → B → C). Use a condition node for "do one of several things". Use a looping node for "do this for each item".
8. **Node IDs change after any full-graph write.** After `deploy --agent-id`, `add-node`, `remove-node`, or `update-metadata`, re-run `get-nodes` before using any node ID again. Surgical patches (`update-node`, `update-node-prompt`, `update-node-params`, `update-edge`) leave IDs unchanged.

---

## Workflow — building a new agent

Load each phase file as you enter that phase. Do not load all up front.

| Phase | File | What happens |
|-------|------|--------------|
| 1 — Intake | `phases/1-intake.md` | Read context, search agents, map current process, one gap question |
| 2 — Design | `phases/2-design.md` | Search tools, design options, cost projection |
| 3 — Review | `phases/3-review.md` | Mermaid + node table + cost, `build` gate |
| 4 — Build | `phases/4-build.md` | Lint, dry-run, deploy, smoke test |
| 5 — Validate | `phases/5-validate.md` | 5-scenario test suite, scoring, Learning feedback |
| 6 — Iterate | `phases/6-iterate.md` | Diagnose, patch, re-validate loop |

---

## Workflow — updating an existing agent

1. Identify the agent: user gives an `agentId`, or `search-agents <keyword>`.
2. Inspect: `get-nodes <agentId>`, then `get-node <agentId> <nodeId>` for detail (param IDs, edge IDs).
3. Gather the change. Show updated Mermaid + node table. Wait for `build`.
4. Apply the **smallest** command that fits:

| Change | Command |
|--------|---------|
| Edit a node's prompt | `update-node-prompt` |
| Edit a node's input/output params | `update-node-params` |
| Change an edge's condition | `update-edge` |
| Rename / re-describe the agent | `update-metadata` |
| Add one node | `add-node` |
| Remove one node | `remove-node` |
| Swap an integration | `attach-tool` |
| Change model or other node config | `update-node` |
| Restructure many nodes at once | `deploy --agent-id <id>` (full redeploy) |

5. **Full redeploy caution:** `deploy --agent-id` drops any node not in your spec. Include every node to keep. Matching is by `toolFunctionName`, so keep node names stable across updates.
6. Report as draft; ask about publishing.

---

## Reference files — read as needed, not all at once

| File | Read when |
|------|-----------|
| `phases/1-intake.md` … `phases/6-iterate.md` | Entering that phase |
| `patterns/tool-taxonomy.md` | Picking a tool type or naming a node |
| `patterns/flow-patterns.md` | Translating a verbal brief to a graph shape |
| `patterns/graph-quality-bar.md` | Auditing node count, data flow, prompt safety |
| `templates/lint-checklist.md` | Pre-deploy lint in Phase 4 |
| `references/ux-flow.md` | Display templates and command words for every state |
| `references/spec-format.md` | Writing or editing a spec |
| `references/node-authoring.md` | Writing prompts, choosing models, calculating cost |
| `references/integrations.md` | Searching and attaching integration tools |
| `references/triggers.md` | Setting up triggers, schedules, webhooks |
| `references/cli-reference.md` | Every `beam.py` command |
| `references/troubleshooting.md` | A command failed or links are broken |
| `assets/example-specs/` | Phase 4 — copy the closest spec as a starting point |

---

## Worked example

**User:** *"Build an agent that takes a topic, writes a blog post, and emails it to me via Gmail."*

1. Validate credentials → ok.
2. `search-agents "blog"` → no close match, new build.
3. Intake: single input (topic), single output (email sent). Volume: manual trigger, occasional. Current process: write post manually, copy-paste into Gmail. Pain point: repetitive.
4. `search-tools gmail --managed-only` → `GmailAction_SendEmail` (nango_cloud).
5. Design: 2 nodes — Write Blog (Custom GPT) → Send Email (Gmail). Simple linear, ≤4 nodes → single option.
6. Show Mermaid + node table with cost. User types `build`.
7. Lint passes. `deploy /tmp/spec.json --dry-run` → ok. `deploy /tmp/spec.json` → agentId returned, `verificationPassed: true`.
8. Smoke test on Write Blog node → output looks correct.
9. "Agent **Blog Writer & Emailer** deployed as draft (`agentId: ...`). Want to run 5 test tasks, or publish now?"
