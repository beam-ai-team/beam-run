# Change an agent's flow

## When to use

- "Make the summary shorter", "switch step 2 to a cheaper model", "add a Slack alert
  after the classifier", "remove the approval step", "route refunds differently",
  "ask for consent before it sends", "add a daily trigger", "give it a webhook".
- Any change to an existing agent's steps, prompts, inputs and outputs, links,
  routing, integrations, consent settings, model, trigger or webhook. This playbook is
  the only way to change a flow.
- Name, description and starter prompts: use `manage-agent-settings-and-files.md`.

## What you need first

- A working builder connection: `graph.validate`.
- The agent and its current steps: `graph.nodes`, then `graph.node` for the steps
  being changed. Re-read after any change that rewrites the graph.
- Whether the change is minor or material. Material means it changes the trigger,
  the shape of the flow, routing, the set of integrations, a destination, or anything
  that acts outside Beam. Minor means tone, length, prompt wording, a model, or a
  single setting.

## Steps

1. Run `graph.validate`, then read `graph.nodes` and the affected `graph.node`.
   Query, don't remember: check `model.catalog` before changing a model, and
   `docs.search` before relying on how a feature works.
2. Pick the smallest action that does the job:
   - prompt or tone: `graph.update-prompt`
   - inputs or outputs: `graph.update-params`
   - a branch condition: `graph.update-edge`
   - model or other step configuration: `graph.update-node`
   - consent before a tool runs: `graph.update-consent`
   - add or remove one step: `graph.add-node` / `graph.remove-node`
   - add an integration to a step: `graph.search-tools`, then `graph.attach-tool`
   - trigger: `graph.trigger-actions`, `graph.create-trigger`,
     `graph.update-trigger`, `graph.toggle-trigger`, `graph.delete-trigger`
   - webhook: `graph.create-webhook` / `graph.delete-webhook`
   - a broad restructure only: `graph.deploy` with `--agent-id`, including every
     step to keep
3. Check the result with `graph.readiness` (it includes links) and re-read the
   changed step with `graph.node`. After a trigger change, run
   `graph.trigger-readiness`; after creating a webhook, `graph.webhook-readiness`.
   Do not call a trigger or webhook working until its check passes.
4. If the change rewrote the graph (add or remove a step, full redeploy), re-read
   `graph.nodes` and re-create any trigger it removed, with the user's OK.

## Stop and ask

- A material change: show a before-and-after flow diagram and the integration list,
  and wait for natural approval before applying it.
- A minor change the user asked for directly: apply it without a second approval,
  then report it.
- An inferred fix (one the user did not spell out): show the before and after first.
- `graph.remove-node`, `graph.delete-trigger`, `graph.delete-webhook`: always
  confirm.
- `graph.create-trigger`, `graph.update-trigger`, `graph.toggle-trigger`,
  `graph.create-webhook`: confirm; these can make the agent start runs on its own.
- Never publish here. The draft stays a draft until `publish-a-draft.md`.

## Done when

- `graph.readiness` passes, the changed step reads back as intended, and the user
  is told exactly what changed and that the agent is still a draft.
- Offer `test-a-draft.md` when the change affects behaviour.

## If it goes wrong

- The integration being attached is not connected yet: attach it anyway, and tell
  the user that step will fail at run time until they connect it
  (`connect-or-fix-an-integration.md`).
- The change landed on the wrong step: re-read and correct with the same small action.
- Readiness fails or links broke: fix them before reporting; if they cannot be
  fixed, say which step and why.
- Detailed rules: `../internal/agent-builder/references/node-authoring.md`,
  `../internal/agent-builder/references/integrations.md`,
  `../internal/agent-builder/references/triggers.md`,
  `../internal/agent-builder/references/cli-reference.md`.

## Actions

Generated from `../contracts/operations.yaml`; do not edit by hand. Run each
action through its MCP tool, or its CLI command when MCP is unavailable (always
the CLI in Codex). Re-read with the re-check action after a change.

| Action | MCP tool | CLI | Needs OK | Re-check | Notes |
| --- | --- | --- | --- | --- | --- |
| `docs.search` | — | `beam docs <query> [--page url]` | no | — | Check the live product docs before relying on how a feature works (loops, automation modes, publishing, triggers, evaluation); the live docs outrank any vendored note. |
| `graph.add-node` | — | `beam agent-builder add-node <agentId> <nodeFile> ...` | no | `graph.readiness` | Rewrites the graph: node ids change and an existing trigger is deleted. Re-read nodes afterwards and re-create the trigger. |
| `graph.attach-tool` | — | `beam agent-builder attach-tool <agentId> <graphId> <nodeId> <toolConfigFile>` | no | `graph.readiness` | — |
| `graph.create-trigger` | — | `beam agent-builder create-trigger <triggerFile>` | explicit | `graph.trigger-readiness` | Once active, the agent starts runs on its own. One trigger per agent: delete the old one first. Add it last, after the graph is settled, because a graph rewrite deletes it. |
| `graph.create-webhook` | — | `beam agent-builder create-webhook <agentId>` | explicit | `graph.webhook-readiness` | Anyone with the URL can start runs; treat it as a secret. |
| `graph.delete-trigger` | — | `beam agent-builder delete-trigger <triggerId>` | always | `graph.triggers` | — |
| `graph.delete-webhook` | — | `beam agent-builder delete-webhook <agentId>` | always | `graph.webhook` | — |
| `graph.deploy` | — | `beam agent-builder deploy <specFile>` | no | `graph.readiness` | Lint and run with --dry-run --summary first. With --agent-id it rewrites the whole graph: include every node to keep; node ids change and an existing trigger is deleted. Stays a draft unless --publish is passed, which needs graph.publish's confirmation. Returns a readiness report; resolve every failure before testing or publishing. |
| `graph.node` | `getAgentGraph` | `beam agent-builder get-node <agentId> <nodeId>` | no | — | — |
| `graph.nodes` | `getAgentGraph` | `beam agent-builder get-nodes <agentId>` | no | — | Light list of node id and objective. The entry node has the objective 'Entry Node'. |
| `graph.readiness` | — | `beam agent-builder readiness <agentId>` | no | — | Every graph change returns this report. Resolve every failure before testing or publishing. |
| `graph.remove-node` | — | `beam agent-builder remove-node <agentId> <nodeId>` | explicit | `graph.readiness` | Rewrites the graph: node ids change and an existing trigger is deleted. Re-read nodes afterwards. |
| `graph.search-tools` | — | `beam agent-builder search-tools <keyword> [--managed-only]` | no | — | Search before adding any integration step; never invent a toolFunctionName. Prefer nango_cloud, then pipedream; ask before choosing a custom fallback. |
| `graph.toggle-trigger` | — | `beam agent-builder toggle-trigger <triggerId>` | explicit | `graph.triggers` | Switching a trigger on makes the agent start runs on its own; say which way it is switching. |
| `graph.trigger-actions` | — | `beam agent-builder trigger-actions <integrationIdentifier>` | no | — | Actions differ per workspace; always look them up. Gives the integrationProviderId for an integration trigger; a timer needs none. |
| `graph.trigger-readiness` | — | `beam agent-builder validate-trigger <agentId> <entryNodeId>` | no | — | Run after every timer or integration trigger create or update; do not call a trigger working until it passes. |
| `graph.update-consent` | — | `beam agent-builder update-node-consent <agentId> <nodeId> <true\|false>` | no | `graph.readiness` | A setting on an existing integration step, not a new step: the run asks for consent right before that tool runs. |
| `graph.update-edge` | — | `beam agent-builder update-edge <edgeId> [--condition TEXT]` | no | `graph.readiness` | — |
| `graph.update-node` | — | `beam agent-builder update-node <agentId> <graphId> <nodeFile>` | no | `graph.readiness` | For a step's model or other configuration. Read the full node first and send it back whole. |
| `graph.update-params` | — | `beam agent-builder update-node-params <agentId> <nodeId> ...` | no | `graph.readiness` | — |
| `graph.update-prompt` | — | `beam agent-builder update-node-prompt <agentId> <nodeId> <promptFile>` | no | `graph.readiness` | Smallest change for prompt or tone edits. |
| `graph.update-trigger` | — | `beam agent-builder update-trigger <triggerId> <triggerFile>` | explicit | `graph.trigger-readiness` | — |
| `graph.validate` | — | `beam agent-builder validate` | no | — | Run before the first builder read or write. Exit 3 means sign in with beam login; exit 2 means a workspace is needed; exit 5 is a network problem (suggest beam doctor). Read the JSON next field on any failure. |
| `graph.webhook-readiness` | — | `beam agent-builder validate-webhook <agentId> [--entry-node-id ID]` | no | — | Run after every webhook create; do not call a webhook working until it passes. |
| `model.catalog` | — | `beam agent-builder models` | no | — | The only valid list of models for this workspace, including the default. Check it before setting or discussing a step's model or its cost. |
