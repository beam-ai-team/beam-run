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
