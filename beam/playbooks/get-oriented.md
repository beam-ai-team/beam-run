# Get oriented

## When to use

- "Who am I signed in as?", "which workspace am I in?", "what agents do I have?",
  "switch to the Acme workspace", "create a workspace called Ops".
- "How does a loop node work?", "what does publishing do?": questions about how a
  Beam feature works.
- Any broad question about the workspace that no other playbook owns.
- Not for one agent's runs (find out what happened) or one agent's setup
  (explain how an agent works).

## What you need first

- A session checkout (see the brief). The instance and workspace it picks are locked
  for this conversation.

## Steps

1. Read the signed-in user and current workspace with `user.current`.
2. If the user wants another workspace, explain that it needs a new conversation,
   started with `beam checkout <instance> [workspace]`. Never switch this one.
3. List agents with `agent.list` when the question is about agents. Group or filter
   by what was asked; report the total.
4. To create a workspace, run `workspace.create` with the exact name (and domain or
   icon if given). It does not change the current workspace.
5. For how a Beam feature works, search the live docs with `docs.search` and answer
   from the page it returns.

## Stop and ask

- `workspace.create`: confirm the exact name before creating; a workspace is
  visible to the account and is not deleted from here.
- If more than one workspace matches a name, ask which one.

## Done when

- The answer names the workspace it came from.
- After `workspace.create`, `user.current` shows the new workspace in the list, and
  the user is told whether they want to switch to it.

## If it goes wrong

- Sign-in fails (exit 3): use the `setup` skill, then resume this request.
- No workspace selected (exit 2): ask the user to pick from a short list.
- No agents found: say so plainly and offer `start-from-a-template.md` or
  `build-a-new-agent.md`.

## Actions

Generated from `../contracts/operations.yaml`; do not edit by hand. Run each
action through its MCP tool, or its CLI command when MCP is unavailable (always
the CLI in Codex). Re-read with the re-check action after a change.

| Action | MCP tool | CLI | Needs OK | Re-check | Notes |
| --- | --- | --- | --- | --- | --- |
| `agent.get` | `getAgentGraph` | `beam agents get <agentId>` | no | — | Shows activeGraphId (live) and draftGraphId (unpublished). Report the model token exactly as returned. createdAt is the default start date for analytics. |
| `agent.list` | `listAgents` | `beam agents list` | no | — | When more than one agent matches a name, ask which one; never pick by display name alone. |
| `docs.search` | — | `beam docs <query> [--page url]` | no | — | Check the live product docs before relying on how a feature works (loops, automation modes, publishing, triggers, evaluation); the live docs outrank any vendored note. |
| `user.current` | `getCurrentUser` | `beam whoami` | no | — | Gives the user id that Learning Hub writes need. Never invent a user id. |
| `workspace.create` | — | `beam workspace create <name> [--domain domain] [--icon-src url]` | explicit-workspace-create-intent | `user.current` | Creating a workspace does not switch to it. |
