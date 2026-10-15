# Build a new agent

## When to use

- "Build me an agent that…", "create a Beam agent to triage tickets", "set up an
  agent that emails me a digest every morning".
- A brand-new agent built from a description. Starting from a template uses
  `start-from-a-template.md`; changing an existing agent uses
  `change-an-agents-flow.md`.

## What you need first

- A working builder connection: `graph.validate`.
- The outcome, inputs, outputs, named services, trigger, repetition, routing and side
  effects, read from the whole request. Do not ask the user to repeat a complete
  brief. Ask one focused question only when the answer changes the flow or blocks a
  valid build (for example, an unnamed notification service); otherwise state the
  assumption in the proposal.

## Steps

1. Run `graph.validate`. Check for a similar agent with `graph.search-agents` when a
   duplicate is plausible.
2. Query, don't remember. Search every named integration with `graph.search-tools` and confirm its
   `toolFunctionName`, required inputs, provider and consent behaviour. Never invent
   a tool. Check the workspace has it connected with `integration.connected`.
3. Design the flow: execution steps for processing, a condition step for exclusive
   routing, a waiting step for delayed work, a loop for a collection. Beam runs
   steps one after another: the entry step has one outgoing link, other
   non-condition steps at most one (a final action can have none). Pick models only
   from `model.catalog`, preferring the cheapest that does the job reliably. Check
   `docs.search` before relying on how a feature works (loops, automation modes,
   publishing, triggers, evaluation).
4. Show the flow proposal and wait for approval (see "Stop and ask").
5. After approval, write the spec using `../internal/agent-builder/references/spec-format.md`,
   `../internal/agent-builder/references/node-authoring.md`, the closest example in
   `../internal/agent-builder/assets/example-specs/`, and check it against
   `../internal/agent-builder/templates/lint-checklist.md`.
6. Dry-run, then create the draft with `graph.deploy` (no `--publish`).
7. Check the draft with `graph.readiness` and fix every failure.
8. Resolve the saved entry node with `graph.nodes`. Add a trigger or webhook only
   if the user asked for one, and only after the graph
   is settled: `graph.trigger-actions`, then `graph.create-trigger` and
   `graph.trigger-readiness`, or `graph.create-webhook` and `graph.webhook-readiness`.

## Stop and ask

- Before creating the draft, show the flow proposal:
  1. A Mermaid diagram of the proposed flow.
  2. A list of the integrations and triggers it will use (only ones confirmed by
     search).
  3. Any assumption, in one sentence, and that it will be created as a draft.
  4. A plain question: is this the agent you want?
  Natural acceptance such as "yes", "looks right" or "go ahead" is enough, as is a
  correction followed by agreement. Never require a command word.
- `graph.create-trigger`, `graph.create-webhook`: confirm separately; once active,
  the agent starts runs on its own.
- Never publish here. Publishing goes through `publish-a-draft.md` on a clear
  request.

## Done when

- `graph.readiness` passes, the agent exists as a draft, and the user is told its
  name, that it is a draft, and what they can do next (test it, change it, publish).
- Test only if the user asks, or to diagnose a failed check.

## If it goes wrong

- Sign-in or workspace problems from `graph.validate`: follow the action's notes,
  then resume.
- An integration is not connected: build the draft anyway if the user agrees, and
  offer `connect-or-fix-an-integration.md`.
- Dry-run or readiness check fails: fix the spec and retry once; then report the exact
  problem. Guides: `../internal/agent-builder/references/troubleshooting.md`,
  `../internal/agent-builder/patterns/flow-patterns.md`.
- Response shapes for proposals, blockers and results:
  `../internal/agent-builder/references/conversation-flow.md`.

## Actions

Generated from `../contracts/operations.yaml`; do not edit by hand. Run each
action through its MCP tool, or its CLI command when MCP is unavailable (always
the CLI in Codex). Re-read with the re-check action after a change.

| Action | MCP tool | CLI | Needs OK | Re-check | Notes |
| --- | --- | --- | --- | --- | --- |
| `agent.get` | `getAgentGraph` | `beam agents get <agentId>` | no | — | Shows activeGraphId (live) and draftGraphId (unpublished). Report the model token exactly as returned. createdAt is the default start date for analytics. |
| `agent.list` | `listAgents` | `beam agents list` | no | — | When more than one agent matches a name, ask which one; never pick by display name alone. |
| `docs.search` | — | `beam docs <query> [--page url]` | no | — | Check the live product docs before relying on how a feature works (loops, automation modes, publishing, triggers, evaluation); the live docs outrank any vendored note. |
| `graph.create-trigger` | — | `beam agent-builder create-trigger <triggerFile>` | explicit | `graph.trigger-readiness` | Once active, the agent starts runs on its own. One trigger per agent: delete the old one first. Add it last, after the graph is settled, because a graph rewrite deletes it. |
| `graph.create-webhook` | — | `beam agent-builder create-webhook <agentId>` | explicit | `graph.webhook-readiness` | Anyone with the URL can start runs; treat it as a secret. |
| `graph.deploy` | — | `beam agent-builder deploy <specFile>` | no | `graph.readiness` | Lint and run with --dry-run --summary first. With --agent-id it rewrites the whole graph: include every node to keep; node ids change and an existing trigger is deleted. Stays a draft unless --publish is passed, which needs graph.publish's confirmation. Returns a readiness report; resolve every failure before testing or publishing. |
| `graph.nodes` | `getAgentGraph` | `beam agent-builder get-nodes <agentId>` | no | — | Light list of node id and objective. The entry node has the objective 'Entry Node'. |
| `graph.readiness` | — | `beam agent-builder readiness <agentId>` | no | — | Every graph change returns this report. Resolve every failure before testing or publishing. |
| `graph.search-agents` | — | `beam agent-builder search-agents <keyword>` | no | — | Use before building, to avoid duplicating an existing agent. |
| `graph.search-tools` | — | `beam agent-builder search-tools <keyword> [--managed-only]` | no | — | Search before adding any integration step; never invent a toolFunctionName. Prefer nango_cloud, then pipedream; ask before choosing a custom fallback. |
| `graph.trigger-actions` | — | `beam agent-builder trigger-actions <integrationIdentifier>` | no | — | Actions differ per workspace; always look them up. Gives the integrationProviderId for an integration trigger; a timer needs none. |
| `graph.trigger-readiness` | — | `beam agent-builder validate-trigger <agentId> <entryNodeId>` | no | — | Run after every timer or integration trigger create or update; do not call a trigger working until it passes. |
| `graph.validate` | — | `beam agent-builder validate` | no | — | Run before the first builder read or write. Exit 3 means sign in with beam login; exit 2 means a workspace is needed; exit 5 is a network problem (suggest beam doctor). Read the JSON next field on any failure. |
| `graph.webhook-readiness` | — | `beam agent-builder validate-webhook <agentId> [--entry-node-id ID]` | no | — | Run after every webhook create; do not call a webhook working until it passes. |
| `integration.connected` | — | `beam integrations connected` | no | — | Only status 'active' counts as connected; pending and inactive do not. |
| `model.catalog` | — | `beam agent-builder models` | no | — | The only valid list of models for this workspace, including the default. Check it before setting or discussing a step's model or its cost. |
| `user.current` | `getCurrentUser` | `beam whoami` | no | — | Gives the user id that Learning Hub writes need. Never invent a user id. |
