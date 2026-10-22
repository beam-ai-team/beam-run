# Connect or fix an integration

## When to use

- "Is Gmail connected?", "what can I connect?", "connect Salesforce", "rename this
  connection", "make this the default Slack", "remove the duplicate Gmail",
  "add a custom integration for our internal API".
- Workspace connections. Adding an integration step to a flow uses
  `change-an-agents-flow.md`. Which live or test connection each step of one agent
  uses, and which are missing, is `use-test-mode.md`.

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

## Actions

Generated from `../contracts/operations.yaml`; do not edit by hand. Run each
action through its MCP tool, or its CLI command when MCP is unavailable (always
the CLI in Codex). Re-read with the re-check action after a change.

| Action | MCP tool | CLI | Needs OK | Re-check | Notes |
| --- | --- | --- | --- | --- | --- |
| `agent.get` | `getAgentGraph` | `beam agents get <agentId>` | no | — | Shows activeGraphId (live) and draftGraphId (unpublished). Report the model token exactly as returned. createdAt is the default start date for analytics. |
| `agent.list` | `listAgents` | `beam agents list` | no | — | When more than one agent matches a name, ask which one; never pick by display name alone. |
| `integration.categories` | `beam_list_integration_categories` | `beam integrations categories` | no | — | — |
| `integration.connect` | — | `beam integrations connect <payloadFile>` | required-if-credentials-or-external-effect | — | OAuth providers must be finished by the user in the browser: link beam://integrations?provider=<name>. Never ask for a secret in chat or echo one back; credentials go only in a local payload file. A custom integration uses provider custom with identifier httpCustomAuth (token) or httpBasicAuth (basic). |
| `integration.connected` | — | `beam integrations connected` | no | — | Only status 'active' counts as connected; pending and inactive do not. |
| `integration.connections` | — | `beam integrations connections <integrationId>` | no | — | Needs the integration UUID from integration.connected, not a slug such as 'gmail' (that returns 400). Offer to tidy up when a provider has two or more active connections. |
| `integration.custom-create` | — | `beam integrations custom-create <payloadFile>` | no | — | Creates an unconnected definition; follow with integration.connect. authType is none, token, basic or oauth (there is no 'apiKey'); token also needs apiKeyType. Resolve the category with integration.categories; never invent its id. |
| `integration.custom-remove` | — | `beam integrations custom-remove <id> --confirm <id>` | always | — | — |
| `integration.custom-update` | — | `beam integrations custom-update <id> <payloadFile>` | no | — | A full replace, not a partial change. |
| `integration.is-connected` | `beam_is_integration_connected` | `beam integrations is-connected <toolFunctionName>` | no | — | Workspace connection state. A step's own isIntegrationConnected is per-agent wiring; never infer one from the other. |
| `integration.list` | — | `beam integrations list` | no | — | The catalog can be large; filter and use a small page size. |
| `integration.remove` | — | `beam integrations remove <providerId> --confirm <providerId>` | always | — | providerId is the connection row id, not the catalog integrationId. |
| `integration.set-default` | — | `beam integrations set-default <providerId> <integrationId>` | no | — | providerId is the connection row id, not the catalog integrationId. |
| `integration.update` | `integration_update_connection` | `beam integrations update <payloadFile>` | no | `integration.connections` | providerId is the connection row id, not the catalog integrationId. |
| `user.current` | `getCurrentUser` | `beam whoami` | no | — | Gives the user id that Learning Hub writes need. Never invent a user id. |
