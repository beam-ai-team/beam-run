# CLI Reference — `beam.py`

Every command of the bundled script. `beam` resolves the script itself, so these
run from any directory:

```bash
beam agent-builder <command> [args]
```

## Conventions

- **Credentials** resolve automatically: environment variables first, then
  `~/.config/beam/credentials` (written by `beam login`); `BEAM_API_URL`
  defaults to the public API. A loopback URL is accepted only with
  `BEAM_LOCAL_DEV=1`, so inherited developer-shell settings cannot redirect a
  production install. There is no `.env` file. Never ask the user to
  paste a key into the chat — if nothing resolves, the fix is `beam login`.
- **Output**: every command prints one JSON object to **stdout**. Success →
  `{"ok": true, "command": "...", ...}`. Failure → `{"ok": false, "code": "...",
  "error": "...", "next": "..."}` plus a categorical exit code: 1 internal,
  2 validation, 3 auth, 5 network. `next` names the command to run.
  Progress and diagnostics go to **stderr** — never merge them into stdout
  with `2>&1` before parsing, or the JSON will not parse.
- **Files**: structured inputs (specs, node payloads, trigger configs) are
  passed as JSON file paths. Simple values are flags or positionals.
- `beam agent-builder <command> --help` prints usage for any command.

---

## Setup & inspection

### `validate`
Check that the credentials reach the Beam API. Run this first, every session.
```bash
beam agent-builder validate
```
→ `{"valid": true, "baseUrl": "..."}` or `{"valid": false, "error": "..."}`.

### `search-tools <keyword> [--wait-only] [--managed-only]`
Search integration tools. `--managed-only` drops prompt-only `custom_gpt_tool`s
and keeps every real `beam_tool` (managed integrations and Beam built-ins like
web search) — use it by default; it keeps the result short. `--wait-only` keeps
only tools a `condition_based` wait node can await.
```bash
beam agent-builder search-tools gmail --managed-only
```
→ `{"tools": [{toolFunctionName, integrationProvider, allowWaiting, ...}], "total": N}`.
Results are sorted nango → pipedream → other.

### `search-agents <keyword>`
Find existing agents by name.
```bash
beam agent-builder search-agents "Blog Writer"
```
→ `{"agents": [{"id": "...", "name": "..."}], "total": N}`.

### `get-nodes <agentId>`
List an agent's nodes (id + objective) and the graph ID.
```bash
beam agent-builder get-nodes AGENT_ID
```
→ `{"agentName": "...", "graphId": "...", "nodes": [{"id", "objective"}]}`.

### `get-node <agentId> <nodeId> [nodeId ...] [--full]`
Get one or more nodes. Default output is a compact summary (params with
`linkParamOutputId`, output params with `id`, edges with `id`) — the fields you
need to wire links and edges. `--full` returns the raw node JSON.
```bash
beam agent-builder get-node AGENT_ID NODE_ID_1 NODE_ID_2
```
→ `{"node": {...}}` for one ID, `{"nodes": [...]}` for several.

### `get-graph <agentId> [--full]`
Get the whole agent graph (compact summary, or raw JSON with `--full`).
```bash
beam agent-builder get-graph AGENT_ID
```

### `verify-links <agentId>`
Check that every `linked` input param across the graph has a valid
`linkParamOutputId`.
```bash
beam agent-builder verify-links AGENT_ID
```
→ `{"allOk": true/false, "links": [{status, nodeName, paramName, linkId}]}`.

---

## Create & deploy

### `deploy <specFile> [--agent-id ID] [--publish] [--dry-run]`
The main command. Creates or updates the agent, attaches every integration in
the spec, re-links downstream params, and verifies — in one call. **Deploys as
a draft** unless `--publish` is given.
```bash
beam agent-builder deploy spec.json                  # create, draft
beam agent-builder deploy spec.json --agent-id ID    # update existing
beam agent-builder deploy spec.json --dry-run        # show payload only
beam agent-builder deploy spec.json --publish        # create + go live
```
→ `{"agentId", "graphId", "published", "verificationPassed", "steps": [...], "note"}`.

`--dry-run` shows the **pre-attach** graph. Integration tools attach in a step
*after* graph creation, so a dry-run lists them under a top-level
`integrationsToAttach` array — not inside `payload.nodes`, where the integration
node still shows a placeholder config. That is expected; the integration is not
missing.

### `create <specFile> [--agent-id ID] [--dry-run]`
Create or update the agent graph **without** attaching integrations. Use
`deploy` instead whenever the spec has an `integrations` array.
```bash
beam agent-builder create spec.json
```
→ `{"agentId", "agentName", "draftGraphId", "activeGraphId"}`.

### `publish <graphId>`
Publish a draft graph — makes the agent live. Only run this when the user
explicitly asked to publish.
```bash
beam agent-builder publish GRAPH_ID
```

---

## Quick updates (existing agent)

Each prefers a dedicated endpoint — faster and safer than a full redeploy.

### `update-node-prompt <agentId> <nodeId> <promptFile> [--publish]`
Replace a node's prompt. `promptFile` is a text/markdown file. Fetches the node,
sets the prompt, updates it, and **re-reads to confirm it persisted** — it fails
loudly rather than reporting a false success. Returns `verified: true`.
```bash
beam agent-builder update-node-prompt AGENT_ID NODE_ID new-prompt.md
```

### `update-node-params <agentId> <nodeId> [--input-params-file F] [--output-params-file F] [--publish]`
Replace a node's input and/or output params. Each file is a JSON array of param
objects (camelCase: `paramName`, `fillType`, `dataType`, …).
```bash
beam agent-builder update-node-params AGENT_ID NODE_ID --input-params-file ip.json
```

### `update-edge <edgeId> [--condition TEXT] [--condition-groups-file F]`
Update an edge. `--condition` sets an `llm_based` condition (`""` =
unconditional); `--condition-groups-file` sets `rule_based` groups. Get edge IDs
from `get-node` (`childEdges[].id`).
```bash
beam agent-builder update-edge EDGE_ID --condition "score is above 80"
```

### `update-metadata <agentId> [--name] [--description] [--personality] [--restrictions] [--prompts-file F] [--publish]`
Change agent-level metadata without touching nodes. Only the flags you pass are
changed.
```bash
beam agent-builder update-metadata AGENT_ID --name "New Name"
```

### `add-node <agentId> <nodeFile> [--source-node-id ID] [--target-node-id ID] [--integration-file F] [--publish]`
Add one node. `nodeFile` is a single node spec (same shape as a `nodes[]` entry).
`--source-node-id` wires an edge into the new node; `--target-node-id` wires one
out. `--integration-file` attaches an integration after adding.
```bash
beam agent-builder add-node AGENT_ID node.json --source-node-id SRC --target-node-id TGT
```

### `remove-node <agentId> <nodeId> [--rewire-to ID] [--publish]`
Remove a node. By default its parents are rewired to its children; with
`--rewire-to` they are pointed at the given node instead.
```bash
beam agent-builder remove-node AGENT_ID NODE_ID
```

### `attach-tool <agentId> <graphId> <nodeId> <toolConfigFile> [--objective TEXT]`
Attach (or swap) an integration tool on an existing node. `toolConfigFile` holds
`toolFunctionName`, `toolName`, `inputParams`, `outputParams`, etc.
```bash
beam agent-builder attach-tool AGENT_ID GRAPH_ID NODE_ID toolconfig.json
```

### `update-node <agentId> <graphId> <nodeFile>`
Update a node from a full node payload (use for model changes or other config
that the lighter commands above don't cover). `nodeFile` is the complete node
object — fetch it with `get-node --full`, edit, pass it back.
```bash
beam agent-builder update-node AGENT_ID GRAPH_ID node.json
```

---

## Triggers & webhooks

### `trigger-actions <integrationIdentifier>`
List available trigger actions for an integration (e.g. `google-mail`, `slack`,
`github`, `timer`). The list is dynamic — always check it.
```bash
beam agent-builder trigger-actions google-mail
```

### `create-trigger <triggerFile>`
Create a trigger from a JSON file (see `references/triggers.md` for the shape).
```bash
beam agent-builder create-trigger trigger.json
```

### `get-triggers <agentId> <entryNodeId>`
List an agent's triggers.

### `update-trigger <triggerId> <triggerFile>`
Update a trigger from a JSON file (only the fields present are changed).

### `delete-trigger <triggerId>`
Delete a trigger.

### `toggle-trigger <triggerId>`
Activate or deactivate a trigger.

### `create-webhook <agentId> [--entry-node-id ID]`
Create a webhook endpoint. Returns `webhookUrl` — the URL external systems POST
JSON to (`<BEAM_API_URL>/<agentId>/webhook`).

### `get-webhook <agentId>`
Get an agent's existing webhook (returns `webhookUrl`).

### `delete-webhook <agentId>`
Remove an agent's webhook.

---

## Smoke testing

### `test-node <agentId> <graphId> <nodeId> '<paramsJson>'`
Run a single node against a task context string. Use when the user requests a
focused test or when diagnosis needs to isolate a representative node. Executes
only that node — not the rest of the graph.
```bash
beam agent-builder test-node AGENT_ID GRAPH_ID NODE_ID '{"message":"Realistic input for this node"}'
```
→ `{"result": { ...node output... }}`.

Pick nodes that: (a) do the core reasoning or extraction, (b) have the most complex prompt, (c) feed linked outputs to downstream nodes.

---

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success (`"ok": true`). |
| `1` | A handled error — see the `error` field in the JSON output. |
| `2` | No command given (help is printed). |
| `130` | Interrupted. |
