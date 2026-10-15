# Triggers & Webhooks Reference

A deployed agent runs when something starts it. By default that is a manual
run; a **trigger** makes it run automatically. Triggers are optional — offer to
set one up after deploying, but never assume one.

## Contents

- [Trigger types](#trigger-types)
- [Workflow](#workflow)
- [The trigger file](#the-trigger-file)
- [Schedule (Timer) triggers](#schedule-timer-triggers)
- [Webhooks](#webhooks)
- [Filters](#filters)
- [Managing triggers](#managing-triggers)

Trigger and webhook commands authenticate with a Bearer JWT, which `beam.py`
obtains automatically from your `BEAM_API_KEY` — there is nothing extra to do.

---

## Trigger types

The available actions are **dynamic per workspace** — always discover them with
`trigger-actions` rather than hardcoding names.

| Category | Example action | Integration identifier |
|----------|----------------|------------------------|
| Email | `GmailFetchEmails` | `google-mail` |
| Email | `OutlookFetchEmails` | `microsoft-outlook` |
| Chat | `GetSlackChannelMessages` | `slack` |
| Files | `GoogleDriveUpdates` | `google-drive` |
| Code | `GithubFetchPullRequests` | `github` |
| Files | `SharePointUpdates` | `microsoft-sharepoint` |
| Schedule | `Timer` | `timer` (no integration) |
| HTTP | Webhook | none — use `create-webhook` |

---

## Workflow

1. **Discover actions** for the integration:
   ```bash
   beam agent-builder trigger-actions google-mail
   ```
   For an integration (Gmail, Slack, …) the response includes the
   `integrationProviderId` to put in the trigger file. For `timer` the response
   is empty — a schedule trigger needs no provider id.

2. **Get the entry node ID** — triggers attach to the entry node:
   ```bash
   beam agent-builder get-nodes <agentId>
   ```
   The entry node is the one with objective `Entry Node`.

3. **Create the trigger** from a JSON file:
   ```bash
   beam agent-builder create-trigger trigger.json
   ```

---

## The trigger file

> **Finalize the agent graph before adding triggers.** A trigger binds to a
> node id, and any later full-graph rewrite (`deploy --agent-id`, `add-node`,
> `remove-node`, `update-metadata`) regenerates node ids and cascade-deletes the
> trigger. Build and settle the graph first; add the trigger last.

`create-trigger` takes one JSON file. Required for every timer or integration
trigger: `agentId`, `agentGraphNodeId` (the entry node ID), `title`, `prompt`,
and `configuration`. The prompt is the concrete instruction delivered when the
trigger fires; never leave it blank. `integrationProviderId` is required for an
integration trigger (Gmail, Slack, …) — take it from the `trigger-actions`
response — but a `Timer` (schedule) trigger has no provider, so omit it. An
agent supports **one trigger at a time**; creating a second returns a 400, so
delete the existing trigger first.

```json
{
  "agentId": "AGENT_UUID",
  "agentGraphNodeId": "ENTRY_NODE_UUID",
  "title": "New Gmail Email",
  "prompt": "Process the matching email according to this agent's workflow.",
  "integrationProviderId": "PROVIDER_UUID_FROM_TRIGGER_ACTIONS",
  "configuration": {
    "beamAction": "GmailFetchEmails",
    "integrationIdentifier": "google-mail",
    "hasAttachment": false,
    "shouldTriggerOnReply": false,
    "filters": []
  },
  "timezone": "America/New_York",
  "onlyOnce": false
}
```

When the trigger fires, the event payload becomes the task input for the
agent's first node.

---

## Schedule (Timer) triggers

To run on a recurring schedule with no integration event:

```json
{
  "agentId": "AGENT_UUID",
  "agentGraphNodeId": "ENTRY_NODE_UUID",
  "title": "Daily Report",
  "prompt": "Generate and post the scheduled report.",
  "configuration": {
    "beamAction": "Timer",
    "integrationIdentifier": "timer",
    "hasAttachment": false,
    "shouldTriggerOnReply": false
  },
  "userDefinedFrequency": "hour",
  "userDefinedFrequencyValue": 24,
  "userDefinedFrequencyDateTime": "1788418800000",
  "timezone": "America/New_York"
}
```

`userDefinedFrequency` is `minute`, `hour`, `week`, or `month`;
`userDefinedFrequencyValue` is the multiplier (every 5 minutes →
`"minute"`, `5`). Every recurring Timer needs a concrete
`userDefinedFrequencyDateTime` start instant, expressed as epoch milliseconds
or ISO 8601 with an offset. For a one-time run, set `onlyOnce: true` and use
that field for the moment it should fire.

Beam's `Timer` has no weekday-only or cron mode — only `minute` / `hour` /
`week` / `month` intervals. "Every weekday morning" can only be approximated
(e.g. a 24-hour timer); if you approximate, tell the user it will also fire on
weekends.

---

## Trigger state and going live

A newly created trigger is **on by default**: `isDeactivated` is `false`, so it
is enabled — do not call `toggle-trigger` on a fresh trigger (it flips
`isDeactivated` and would turn the trigger *off*). The separate `isActive` flag
reads `false` on a freshly created trigger / draft agent — that is expected,
not a failure. `toggle-trigger` takes no on/off argument, so always check
`get-triggers` before using it.

Publishing is separate from the trigger. `deploy` leaves the agent as a
**draft**; publishing is what makes the agent live. After configuring a
trigger, tell the user it is set, and remind them to publish the agent if they
want it running.

---

## Webhooks

To let an external system start the agent over HTTP:

```bash
beam agent-builder create-webhook <agentId> --entry-node-id <entryNodeId>
beam agent-builder get-webhook <agentId>
beam agent-builder delete-webhook <agentId>
```

`create-webhook` and `get-webhook` return a `webhookUrl` field — the URL
external systems `POST` JSON to (`<BEAM_API_URL>/<agentId>/webhook`); the
request body becomes the task input available to all nodes. A webhook and a
schedule/integration trigger can both be attached to the same agent.

---

## Filters

A trigger's `configuration.filters` narrows which events fire it — e.g. only
emails from a specific sender:

```json
"filters": [
  {
    "operator": "AND",
    "conditions": [
      { "property": "from", "condition": "is", "value": "boss@company.com" }
    ]
  }
]
```

Condition operators: `is`, `is_not`, `contain`, `does_not_contain`, `any`,
`all`, `less_than`, `GREATER_than`, `exist`, `does_not_exist`. Group operators:
`AND`, `OR`.

---

## Managing triggers

| Action | Command |
|--------|---------|
| List an agent's triggers | `get-triggers <agentId> <entryNodeId>` |
| Update config / frequency | `update-trigger <triggerId> trigger.json` |
| Turn a trigger off / on (flips `isDeactivated`) | `toggle-trigger <triggerId>` |
| Delete | `delete-trigger <triggerId>` |

For `update-trigger`, the JSON file **must include `title`** (the API rejects an
update without it) plus any of `agentId`, `prompt`, `configuration`, `timezone`,
`userDefinedFrequency`, `userDefinedFrequencyValue`,
`userDefinedFrequencyDateTime`, `isActive`, `onlyOnce` that you are changing.

## Trigger readiness (mandatory)

`create-trigger` and `update-trigger` automatically read the saved payload and
return `triggerReadiness`. Treat `verificationPassed: false` as a failed
configuration, not a successful schedule. You can run the same inspection at
any time:

```bash
beam agent-builder validate-trigger AGENT_ID ENTRY_NODE_ID
```

The check verifies every trigger's agent, entry node, title, prompt, action,
and configuration booleans. It then applies type-specific checks:

- **Timer:** `Timer`/`timer` pairing, no provider, supported cadence, positive
  interval, timezone, concrete start time, and a persisted, cadence-aligned
  next execution time.
- **Integration:** non-timer action, connected provider, action support from
  `trigger-actions`, and supported filters when configured.
- **Webhook:** use `validate-webhook` after creation; it verifies the persisted
  endpoint, `triggered: true`, agent scope, HTTPS URL, and optional entry-node
  binding.

An inactive trigger on a draft graph is reported as a warning, not a payload
failure: it will activate only when the graph is published.
