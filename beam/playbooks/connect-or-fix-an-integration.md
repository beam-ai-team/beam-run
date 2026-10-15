# Connect or fix an integration

## When to use

- "Is Gmail connected?", "what can I connect?", "connect Salesforce", "rename this
  connection", "make this the default Slack", "remove the duplicate Gmail",
  "add a custom integration for our internal API".
- Workspace connections. Adding an integration step to a flow uses
  `change-an-agents-flow.md`.

## What you need first

- The provider and, for changes, the exact connection row. Connection actions take
  the connection row id (`providerId`), not the catalog id.
- For a custom integration: name, endpoints (method, URL, parameters), auth type,
  and category.

## Steps

1. Read what is connected with `integration.connected`. Only status `active` counts.
2. Browse the catalog with `integration.list` (filtered, small pages) and categories
   with `integration.categories`.
3. For one provider's connections, use `integration.connections` with the
   integration UUID. For whether a specific tool's integration is connected, use
   `integration.is-connected`.
4. Act:
   - add a credential-based connection: `integration.connect`
   - rename: `integration.update`
   - set the default: `integration.set-default`
   - remove: `integration.remove`
   - custom integration: `integration.custom-create`, then `integration.connect`
     (it is unconnected until then); later `integration.custom-update` (full
     replace) or `integration.custom-remove`
5. Re-read with `integration.connections` or `integration.connected`.

## Stop and ask

- `integration.connect`: confirm the provider and connection name first. Never ask
  for a secret in the chat and never repeat one back; the user puts credentials in a
  local payload file, or finishes OAuth in the browser.
- `integration.remove`, `integration.custom-remove`: always confirm, naming the
  connection; agents using it may stop working.
- `integration.update`, `integration.set-default`: no confirmation needed.

## Done when

- The re-read shows the expected state (for example, the new connection `active`,
  or the duplicate gone), and the user is told which connection is now default.

## If it goes wrong

- OAuth providers (Salesforce, Google and so on) cannot be finished from here: link
  `beam://integrations?provider=<name>`.
- "Which agents use this connection?": there is no lookup for that; say so plainly.
- A slug such as "gmail" returns 400: use the UUID from `integration.connected`.
