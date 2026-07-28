# Integrations Reference

How to find integration tools, choose between them, and attach them to nodes.

## Contents

- [Searching for tools](#searching-for-tools)
- [Provider priority](#provider-priority)
- [Integration node rules](#integration-node-rules)
- [Attaching at deploy time](#attaching-at-deploy-time)
- [Swapping an integration on a live agent](#swapping-an-integration-on-a-live-agent)
- [Common tool schemas](#common-tool-schemas)

---

## Searching for tools

Find the exact tool for an action before writing the spec. Add `--managed-only`
— it drops prompt-only `custom_gpt_tool`s and keeps every real `beam_tool`
(managed integrations like Gmail/Slack **and** Beam built-ins such as web
search, which have no `integrationProvider`), so the result is short and
trustworthy:

```bash
python3 scripts/beam.py search-tools gmail --managed-only
python3 scripts/beam.py search-tools slack --managed-only
```

If `--managed-only` returns nothing for an action there is no real tool for it
— re-run without the flag to see prompt-only `custom_gpt_tool`s, but ask the
user before using one (see [Provider priority](#provider-priority)).

Search for every integration the agent needs. Each result includes:

| Field | Use |
|-------|-----|
| `toolFunctionName` | Goes into the spec's `integrations[].tool_function_name` (e.g. `GmailAction_SendEmail`). Must match exactly. |
| `toolName` | Display name. |
| `description` | What the tool does. |
| `requiredArgs` / `optionalArgs` | The tool's parameters — informs the `input_params` you write. |
| `requiresConsent` | Whether the tool needs a user consent step. |
| `integrationProvider` | `nango_cloud`, `pipedream`, or `none` — drives the choice below. |
| `integrationIdentifier` | The integration's id (e.g. `google-mail`) — needed for triggers. |
| `isIntegrationConnected` | Whether the workspace has connected this integration. |
| `toolType` | `beam_tool` (managed integration) or `custom_gpt_tool` (prompt-only). |
| `allowWaiting` | Whether a `condition_based` waiting node can await this tool's reply. |

Add `--wait-only` to list only tools a `condition_based` wait node can await:

```bash
python3 scripts/beam.py search-tools slack --wait-only
```

---

## Provider priority

When several tools match, choose by provider — `beam.py` already sorts results
in this order:

1. **`nango_cloud`** — first-party managed integrations with reliable auth.
   Always prefer these.
2. **`pipedream`** — use only if no Nango tool exists for the action.
3. **No managed tool** — if neither exists, do **not** silently use a
   `custom_gpt_tool`. Ask the user:

   > "There's no managed integration for [action]. I can (1) search a different
   > keyword/service, or (2) build it as a prompt-only custom node with no real
   > integration. Which do you want?"

A tool with `toolType: beam_tool` and a real `integrationProvider` is a managed
integration. A tool with `toolType: custom_gpt_tool` and
`integrationProvider: none` is prompt-only — it has no live backend.

---

## Integration node rules

An integration node appears in **both** the `nodes` array and the
`integrations` array. Full schema is in `references/spec-format.md`; the rules
that matter most:

- In `nodes`, the integration node has **empty `input_params` and
  `output_params`** (omit them) and an **empty `prompt`** (omit it). The
  integration supplies its own params. Defining params in both places conflicts.
- Set the node's `model` to a capable extraction model (`GPT4_1_MINI`,
  `GEMINI_3_FLASH`, …) — not the tool's `preferredModel`.
- The node still needs a unique `key`, `name`, `objective`, and correct `edges`.
- Never set `is_exit: true`.
- All the real config — `tool_function_name`, params, links — goes in the
  matching `integrations` array entry.
- A node that **consumes** an integration's result reads it with `ai_fill`,
  not `link`. Beam has no output schema for integration tools, so a `linked`
  name would be a guess — and a guessed name that misses the tool's real
  output fails at run time. Never `link` from an integration output; leave the
  integration's `output_params` empty.

One integration node = one external action. To send to Gmail *and* Slack, that
is two nodes chained sequentially, each with its own integration entry.

---

## Attaching at deploy time

`deploy` handles attachment automatically when the spec has an `integrations`
array. For each entry it:

1. Creates the agent (custom nodes first).
2. Maps spec node keys to the created node IDs.
3. Attaches each tool to its `node_key`.
4. Resolves `linked` integration params: `linked_from_key` +
   `linked_from_param` become the real output-param UUID of the source node.
5. Re-links any downstream node whose source UUIDs shifted during attach.
6. Verifies every linked param resolved.

You never write UUIDs. You reference source nodes by spec key. After deploy,
check `verificationPassed` in the result — if `false`, run `verify-links`.

`create` (as opposed to `deploy`) does **not** attach integrations. Whenever the
spec has integrations, use `deploy`.

---

## Swapping an integration on a live agent

To replace one integration with another (e.g. Gmail → Outlook) without a full
redeploy:

1. `get-nodes <agentId>` — find the node ID and graph ID.
2. `search-tools microsoft` — find the new tool's `toolFunctionName`.
3. `get-node <agentId> <nodeId>` — see current params and links.
4. Write a tool-config JSON file:
   ```json
   {
     "toolFunctionName": "MicrosoftOutlookAction_MessageSend",
     "toolName": "Send Email",
     "description": "Send an email from Outlook",
     "requiresConsent": true,
     "inputParams": [ /* params, with linkParamOutputId UUIDs for linked ones */ ],
     "outputParams": [ /* ... */ ]
   }
   ```
5. `attach-tool <agentId> <graphId> <nodeId> toolconfig.json --objective "..."`.
6. `verify-links <agentId>` — confirm nothing broke.

Attaching a tool **replaces the node's tool configuration and regenerates its
output-param UUIDs.** Any downstream node with a `linked` param pointing at this
node must be re-linked afterward (`deploy` does this automatically; a manual
`attach-tool` does not). For linked input params in the tool-config file, set
`linkParamOutputId` to the actual source output-param UUID from `get-node`.

---

## Common tool schemas

Always confirm the exact `toolFunctionName` and params with `search-tools` —
schemas vary by workspace and change over time. These are typical shapes.

### Gmail — Send Email

- `toolFunctionName`: `GmailAction_SendEmail` · `requiresConsent`: `true`

| paramName | dataType | required | notes |
|-----------|----------|----------|-------|
| `email_address` | string | yes | Comma-separated recipients |
| `subject` | string | yes | |
| `body` | string | yes | HTML or markdown |
| `cc_list` / `bcc_list` | string | no | Comma-separated |
| `sender_name` | string | no | Display name |

Outputs: `message`, `email_address`.

### Slack — Send Message

- `SlackAction_SendMessageToChannel` — params `channel`, `message`
- `SlackAction_SendPersonalMessageToUser` — params `user`, `message`

### Outlook — Send Email

- `toolFunctionName`: `MicrosoftOutlookAction_MessageSend`
- Params: `email_address`, `subject`, `body`.

### Quick reference

| Integration | search keyword | typical toolFunctionName | provider |
|-------------|----------------|--------------------------|----------|
| Gmail send | `gmail` | `GmailAction_SendEmail` | nango_cloud |
| Gmail read | `gmail` | `GmailAction_GetMessageDetails` | nango_cloud |
| Gmail label | `gmail` | `GmailAction_AddLabel` | nango_cloud |
| Slack channel | `slack` | `SlackAction_SendMessageToChannel` | nango_cloud |
| Slack DM | `slack` | `SlackAction_SendPersonalMessageToUser` | nango_cloud |
| Outlook send | `microsoft` | `MicrosoftOutlookAction_MessageSend` | nango_cloud |
| Google Sheets | `google sheet` | varies | varies |
| Airtable | `airtable` | varies | varies |
