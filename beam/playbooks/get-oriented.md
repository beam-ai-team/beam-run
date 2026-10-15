# Get oriented

## When to use

- "Who am I signed in as?", "which workspace am I in?", "what agents do I have?",
  "switch to the Acme workspace", "create a workspace called Ops".
- Any broad question about the workspace that no other playbook owns.
- Not for one agent's runs (find out what happened) or one agent's setup
  (explain how an agent works).

## What you need first

- Nothing beyond a signed-in CLI. The workspace comes from the request, a Beam URL,
  the remembered default, or the user's only workspace.

## Steps

1. Read the signed-in user and current workspace with `user.current`.
2. If the user names another workspace, resolve it with `beam workspace list <name>`
   and set it with `beam workspace <id>`. Never switch on a guess.
3. List agents with `agent.list` when the question is about agents. Group or filter
   by what was asked; report the total.
4. To create a workspace, run `workspace.create` with the exact name (and domain or
   icon if given). It does not change the current workspace.

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
