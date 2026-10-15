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

## Actions

Generated from `../contracts/operations.yaml`; do not edit by hand. Run each
action through its MCP tool, or its CLI command when MCP is unavailable (always
the CLI in Codex). Re-read with the re-check action after a change.

| Action | MCP tool | CLI | Needs OK | Re-check | Notes |
| --- | --- | --- | --- | --- | --- |
| `agent.get` | `getAgentGraph` | `beam agents get <agentId>` | no | — | Shows activeGraphId (live) and draftGraphId (unpublished). Report the model token exactly as returned. createdAt is the default start date for analytics. |
| `agent.list` | `listAgents` | `beam agents list` | no | — | When more than one agent matches a name, ask which one; never pick by display name alone. |
| `template.categories` | `beam_list_template_categories` | `beam templates categories` | no | — | Resolve a category name to its id before filtering. |
| `template.create-agent` | — | `beam templates create-agent <templateId>` | no | `agent.get` | Read the full template first and pass its graph as is (a nested graph-and-tools object). The new agent is a draft. |
| `template.get` | — | `beam templates get <templateId>` | no | — | — |
| `template.list` | — | `beam templates list` | no | — | Rows use title and shortDescription. count is the full library total: page with pageNum and never present one page as the whole library. |
| `template.prerequisites` | `beam_get_template_with_prerequisites` | `beam templates get <templateId> + beam integrations connected` | no | — | missingIntegrations is the 'what do I connect first' answer. |
| `template.recommend` | — | `beam templates recommend [categoryId]` | no | — | Prefer this over keyword search for 'what should I build?'. |
