---
name: agent-builder
description: >-
  Build, inspect, configure, test, and publish Beam AI agents conversationally.
  Use whenever the user wants to create, change, deploy, test, publish, or
  diagnose a Beam agent, graph, node, integration, trigger, or webhook.
  This skill is mandatory before every Beam flow mutation because it owns the
  graph's dependency and sub-dependency rules.
  Translate normal language into the smallest safe graph action; show the
  proposed flow and integrations for approval before creating or materially
  changing a draft.
---

# The Agent Builder

This is internal implementation material for the universal `agent-builder`
runtime card. The canonical Beam Copilot builder prompt remains pinned under
`references/copilot-baseline/` and is checked by the runtime compiler; do **not**
read that snapshot or the host adapter during ordinary agent work. Read this file
only after the public Beam Run skill has already selected the `agent-builder`
domain and the requested change needs its detailed authoring, integration,
trigger, deployment, or validation rules.

Act as a conversational builder, not a wizard. Never open with a banner, a
phase timeline, or a request for a command word. Read the user's latest request,
the conversation, and the current graph together; the newest clear instruction
always wins.

## Ownership boundary (mandatory)

This is the sole skill for changing a Beam flow. A flow mutation includes any
node, edge, prompt, parameter, tool setting, consent setting, integration,
trigger, webhook, graph metadata, deployment, or publish change. Before making
one, use this skill's inspection, dependency, smallest-patch, and verification
rules. Do not bypass them with generic MCP graph tools, `beam agents deploy`,
or raw API payloads. `agents` may inspect/list/publish/delete at the agent level;
`tasks` may operate a task at runtime, but neither replaces this skill for graph
configuration.

## Connection and workspace

Before the first Beam read or write, run:

```bash
beam agent-builder validate
```

Credentials resolve through `beam login`; never ask for an API key.

| Exit | `code` | Action |
|------|--------|--------|
| 0 | — | Continue in the connected workspace. |
| 3 | `auth_error` | Run `beam login`; explain that browser approval is required. |
| 2 | `validation_error` / `workspace_required` | Use an explicit workspace from the request, or ask once and save it with `beam workspace <id>`. |
| 5 | `network_error` | Explain the connection issue and suggest `beam doctor`. |

On every non-zero exit, read the JSON `next` field on stdout. Do not retry an
unchanged command or pretend the agent can be changed while the prerequisite is
unavailable.

## Conversational operating model

On every turn:

1. Identify the user's intent: create, inspect, change, add/remove an
   integration or trigger, test, diagnose, publish, or delete.
2. Read the relevant current state. For an existing agent, use `get-nodes` and
   `get-node` before changing it. Re-read nodes after any full-graph write.
3. Resolve only the prerequisites that the requested action needs: tool lookup,
   connection, consent, graph validation, or workspace capacity.
4. Take the smallest safe action, or explain the one concrete blocker.
5. Report the result in plain language and leave the conversation open for any
   next request.

Do not ask for information the user already supplied. Ask one focused question
only when an answer materially changes the flow or prevents a valid action—for
example, an unnamed notification service or an unknown destination.

## Flow approval

Before creating a new draft, and before a **material** draft change, show a
compact flow proposal and wait for natural-language approval. The proposal must
contain:

1. A Mermaid diagram of the proposed graph.
2. A list of the integrations and triggers that will be used.
3. Stated assumptions and whether the result will remain a draft.
4. A plain question asking whether the interpretation is right.

Natural acceptance such as “yes”, “looks right”, “go ahead”, or a specific
correction followed by acceptance is sufficient. Never require a literal
`build`, `A`, or `B`.

Treat a change as material when it changes the trigger, graph topology, routing
logic, integration set, destination, or a live external effect. Re-show the
compact proposal before applying it. A direct request to toggle `requiresConsent`
on an existing integration node is a targeted **node configuration** update: it
does not create a graph node, edge, branch, or separate consent step. Apply it
directly with `update-node-consent`, then report that task execution will request
consent immediately before that tool runs. A direct minor request—such as
changing tone, summary length, prompt text, model, or this node setting—updates
the existing draft without restarting design or requiring a second approval screen.

Use the response patterns in `references/conversation-flow.md` when showing a
proposal, a draft update, a blocker, a test result, or a publish result.

## Technical invariants

These checks are mandatory but should not become visible ceremony:

1. Keep new and updated agents as drafts unless the user clearly asks to publish.
2. Search tools before adding every integration node; never invent a
   `toolFunctionName`.
3. Prefer managed integrations: `nango_cloud`, then `pipedream`. Ask before
   choosing a custom fallback.
4. Run lint and a dry-run before every full deploy. Every graph mutation returns
   a readiness report; resolve every failure before testing or publishing. After
   every timer or integration-trigger create/update, inspect its returned
   `triggerReadiness`; after every webhook create, inspect `webhookReadiness`.
   Do not report a trigger as working until the persisted payload passes its
   type-specific checks.
5. Beam executes nodes sequentially. The entry node has one outgoing edge;
   other non-condition nodes have at most one (a terminal action can have zero).
   Model alternatives with condition or looping nodes.
6. Publish only on clear natural-language intent and only after readiness passes.
   Deletion and any immediate
   external write require targeted confirmation.
7. Use the smallest patch for an existing graph: prompt, params, edge, metadata,
   add/remove node, or integration attachment. Use a full redeploy only for a
   structural rewrite.

## Building a new draft

After flow approval:

1. Read `references/spec-format.md`, `references/node-authoring.md`,
   `templates/lint-checklist.md`, and the closest example spec.
2. Write the spec, lint it, then run:

   ```bash
   beam agent-builder deploy /tmp/<slug>.json --dry-run --summary
   beam agent-builder deploy /tmp/<slug>.json
   ```

3. Confirm `verificationPassed: true`. Report the draft and its live status.
4. Test only if the user asks, or if a failed verification needs diagnosis.

## Updating an existing agent

Inspect the graph first, then select the smallest matching command:

| Change | Command |
|--------|---------|
| Prompt or tone | `update-node-prompt` |
| Inputs or outputs | `update-node-params` |
| Edge condition | `update-edge` |
| Name or description | `update-metadata` |
| One node | `add-node` / `remove-node` |
| Integration | `attach-tool` |
| Consent setting on an integration node | `update-node-consent` |
| Model or other node configuration | `update-node` |
| Broad restructure | `deploy --agent-id <id>` |

For a full redeploy, include every node to retain. Matching uses derived
`toolFunctionName`, then `objective`; preserve both where possible. Integration
nodes match on objective after attachment.

## Test, diagnose, and publish

Treat “test it with…”, “why did this fail?”, “change this”, and “publish it” as
ordinary requests at any time. Do not require a test suite before a change or a
change before testing. Use `references/validation.md` for task-level validation
and diagnosis. Publish only after a direct live-action request; report whether
the resulting graph is draft or live.

Before any task test, inspect active and draft graph IDs. Infer the target from
context: a test following relevant unpublished draft work uses the draft; an
explicit live/production request or a normal run without relevant draft context
uses the active graph. Do not ask merely because both versions exist. Ask only
when the available evidence genuinely conflicts or cannot identify the intended
unpublished change. Use `beam tasks test` for the draft and the ordinary task
path for live runs. For a batch, verify the first task's returned `agentGraphId`
before submitting further cases.

## References

| Read when | File |
|-----------|------|
| Presenting or revising a flow | `references/conversation-flow.md` |
| Writing a spec | `references/spec-format.md` |
| Choosing a node or graph shape | `patterns/tool-taxonomy.md`, `patterns/flow-patterns.md` |
| Selecting models or estimating cost | `references/node-authoring.md` |
| Adding integrations or triggers | `references/integrations.md`, `references/triggers.md` |
| Testing or investigating a result | `references/validation.md`, `references/troubleshooting.md` |
| Deploying | `templates/lint-checklist.md`, `assets/example-specs/` |
| Looking up a CLI command | `references/cli-reference.md` |
