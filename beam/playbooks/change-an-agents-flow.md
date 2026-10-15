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
3. Check every link with `graph.verify-links`, and re-read the changed step with
   `graph.node`.
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

- `graph.verify-links` passes, the changed step reads back as intended, and the user
  is told exactly what changed and that the agent is still a draft.
- Offer `test-a-draft.md` when the change affects behaviour.

## If it goes wrong

- The integration being attached is not connected yet: attach it anyway, and tell
  the user that step will fail at run time until they connect it
  (`connect-or-fix-an-integration.md`).
- The change landed on the wrong step: re-read and correct with the same small action.
- Links broke: fix them before reporting; if they cannot be fixed, say which step.
- Detailed rules: `../internal/agent-builder/references/node-authoring.md`,
  `../internal/agent-builder/references/integrations.md`,
  `../internal/agent-builder/references/triggers.md`,
  `../internal/agent-builder/references/cli-reference.md`.
