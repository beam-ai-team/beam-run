# Start from a template

## When to use

- "What templates are there?", "what should I build?", "show me sales templates",
  "what does this template need connected?", "compare these two", "create an agent
  from the invoice template".
- Not for building from a description: use `build-a-new-agent.md`.

## What you need first

- For browsing: nothing. For a category, its id from `template.categories`.
- For creating: the exact template id.

## Steps

1. Browse:
   - recommendations for this workspace: `template.recommend`
   - the library, by category or search: `template.categories`, then
     `template.list`. Report the full total and page through rather than presenting
     one page as everything.
2. Read one template with `template.get` (flow, tools, description). To compare two,
   read both and set the differences side by side.
3. Check what must be connected first with `template.prerequisites`.
4. Create the agent with `template.create-agent`, passing the template's graph as is.
5. Read the new agent with `agent.get`.

## Stop and ask

- `template.create-agent` needs no extra confirmation when the user asked for it:
  the new agent is a draft and does not run. Name the template and the new agent's
  name before creating.

## Done when

- `agent.get` shows the new draft agent; the user gets its name, a
  `beam://agent.flow?agentId=<id>` link, and the integrations still missing.

## If it goes wrong

- Missing integrations: offer `connect-or-fix-an-integration.md`.
- "Which agents came from this template?": there is no lookup for that; offer a name
  search with `agent.list` instead.
- Next steps after creating: `test-a-draft.md`, `change-an-agents-flow.md`, then
  `publish-a-draft.md`.
