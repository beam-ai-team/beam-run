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
2. Search every named integration with `graph.search-tools` and confirm its
   `toolFunctionName`, required inputs, provider and consent behaviour. Never invent
   a tool. Check the workspace has it connected with `integration.connected`.
3. Design the flow: execution steps for processing, a condition step for exclusive
   routing, a waiting step for delayed work, a loop for a collection. Beam runs
   steps one after another; each non-condition step has one outgoing link. Prefer
   the cheapest model that does the job reliably.
4. Show the flow proposal and wait for approval (see "Stop and ask").
5. After approval, write the spec using `../internal/agent-builder/references/spec-format.md`,
   `../internal/agent-builder/references/node-authoring.md`, the closest example in
   `../internal/agent-builder/assets/example-specs/`, and check it against
   `../internal/agent-builder/templates/lint-checklist.md`.
6. Dry-run, then create the draft with `graph.deploy` (no `--publish`).
7. Check every link with `graph.verify-links`.
8. Add a trigger or webhook only if the user asked for one, and only after the graph
   is settled: `graph.trigger-actions`, then `graph.create-trigger`, or
   `graph.create-webhook`.

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

- `graph.verify-links` passes, the agent exists as a draft, and the user is told its
  name, that it is a draft, and what they can do next (test it, change it, publish).
- Test only if the user asks, or to diagnose a failed check.

## If it goes wrong

- Sign-in or workspace problems from `graph.validate`: follow the action's notes,
  then resume.
- An integration is not connected: build the draft anyway if the user agrees, and
  offer `connect-or-fix-an-integration.md`.
- Dry-run or link check fails: fix the spec and retry once; then report the exact
  problem. Guides: `../internal/agent-builder/references/troubleshooting.md`,
  `../internal/agent-builder/patterns/flow-patterns.md`.
- Response shapes for proposals, blockers and results:
  `../internal/agent-builder/references/conversation-flow.md`.
