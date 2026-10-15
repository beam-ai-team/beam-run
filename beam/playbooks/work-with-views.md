# Work with Views

## When to use

- "What Views do I have?", "show me the Support Runs view", "filter rows where status
  is failed", "follow this linked record", "export it to CSV", "add a column",
  "rename that column", "delete this view".

## What you need first

- The view id, from `view.list` (filter by agent or search) unless the user gave it.
- For a new non-link column: the feeding agent's step and parameter. Read the
  view's agent with `view.get`, then its steps with `graph.nodes` and `graph.node`.

## Steps

1. Read the schema with `view.get` before explaining any records.
2. Read rows with `view.records` (filter, sort, choose fields; at most 100 per page),
   and follow link columns with `view.linked-records`.
3. Act:
   - export: `view.export`
   - create a view: `view.create`; delete it: `view.delete`
   - add a column: `view.add-column`; change one: `view.update-column`; delete one:
     `view.delete-column`
4. Re-read with `view.get` (or `view.list` after deleting a view).

## Stop and ask

- `view.delete`, `view.delete-column`: always confirm, naming the view or column.
- Creating, exporting and editing columns need no confirmation.

## Done when

- The re-read shows the new schema or the view gone; an export returns the CSV.

## If it goes wrong

- Rows cannot be added, edited or deleted here — only the agent's runs write them.
  Say so and link `beam://agent.flow?agentId=<id>`.
- A non-link column's step and parameter cannot be resolved with confidence: do not
  guess; link `beam://views?viewId=<id>` to finish it in the column builder.
- No views or rows: say so plainly.

## Actions

Generated from `../contracts/operations.yaml`; do not edit by hand. Run each
action through its MCP tool, or its CLI command when MCP is unavailable (always
the CLI in Codex). Re-read with the re-check action after a change.

| Action | MCP tool | CLI | Needs OK | Re-check | Notes |
| --- | --- | --- | --- | --- | --- |
| `agent.get` | `getAgentGraph` | `beam agents get <agentId>` | no | — | Shows activeGraphId (live) and draftGraphId (unpublished). Report the model token exactly as returned. createdAt is the default start date for analytics. |
| `agent.list` | `listAgents` | `beam agents list` | no | — | When more than one agent matches a name, ask which one; never pick by display name alone. |
| `graph.node` | `getAgentGraph` | `beam agent-builder get-node <agentId> <nodeId>` | no | — | — |
| `graph.nodes` | `getAgentGraph` | `beam agent-builder get-nodes <agentId>` | no | — | Light list of node id and objective. The entry node has the objective 'Entry Node'. |
| `graph.validate` | — | `beam agent-builder validate` | no | — | Run before the first builder read or write. Exit 3 means sign in with beam login; exit 2 means a workspace is needed; exit 5 is a network problem (suggest beam doctor). Read the JSON next field on any failure. |
| `user.current` | `getCurrentUser` | `beam whoami` | no | — | Gives the user id that Learning Hub writes need. Never invent a user id. |
| `view.add-column` | `view_create_column` | `beam views add-column <viewId> <payloadFile>` | no | `view.get` | Name: letters, numbers and underscore, up to 60 characters. A non-link column needs the feeding agent's node id and parameter; if they cannot be resolved with confidence, do not guess: link beam://views?viewId=<id>. |
| `view.create` | `view_create` | `beam views create <payloadFile>` | no | — | — |
| `view.delete` | `view_delete` | `beam views delete <viewId> --confirm <viewId>` | always | `view.list` | — |
| `view.delete-column` | `view_delete_column` | `beam views delete-column <viewId> <columnId> --confirm <columnId>` | always | `view.get` | — |
| `view.export` | — | `beam views export <viewId>` | no | — | — |
| `view.get` | — | `beam views get <viewId>` | no | — | Read the column schema before explaining records. |
| `view.linked-records` | `beam_list_linked_records` | `beam views linked-records <viewId> <columnId> <numericRecordId>` | no | — | Needs the link column id and the numeric record id. |
| `view.list` | — | `beam views list` | no | — | — |
| `view.records` | — | `beam views records <viewId>` | no | — | pageSize at most 100; supports where, sort and fields. |
| `view.update-column` | `view_update_column` | `beam views update-column <viewId> <columnId> <fullPayloadFile>` | no | `view.get` | Send the full column, keeping the required mapping fields. |
