# Troubleshooting

When a command fails it prints `{"ok": false, "code": "...", "error": "...",
"next": "..."}` on **stdout** and exits 1 internal / 2 validation / 3 auth /
5 network. **Do the `next` field first** — it names the command to run. Come here
only when `next` is absent or did not resolve it.

Parse stdout alone: `2>&1` merges the human `[beam.py] ERROR:` line into the JSON
and makes it unparseable.

## Credentials & connectivity

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Not signed in to Beam.` (`auth_error`, exit 3) | No API key in the environment or in `~/.config/beam/credentials`. | Run `beam login`; the user approves in the browser. **Never** ask them for a key. |
| `No Beam workspace selected.` (`validation_error`, exit 2) | A key resolved but no workspace is set. | Use explicit request context; otherwise ask once, then remember it with `beam workspace <id>`. Do not guess — the wrong workspace looks empty. |
| `beam: command not found` | The CLI is not on PATH. | Run the plugin's `setup` skill, or `beam setup`. Open a new terminal afterwards. |
| `bundled agent builder not found` | Plugin files are incomplete. | Reinstall the plugin, then `beam setup`. |
| `the agent builder needs python3` | No Python 3.8+. | Install Python 3, then retry. |
| `Authentication failed (401)` / `(403)` | The API key was revoked, the workspace is inaccessible, or the user lacks permission. | Run `beam login` again. If it persists, verify the active workspace and the user's permissions. |
| `cannot reach the Beam API` | `BEAM_API_URL` is wrong, or the API is down. | Confirm the URL with the user — it must point at their Beam API instance. |
| `auth/access-token did not return an idToken` | Trigger/webhook auth exchange failed. | The API key may be invalid, or the server has no `/auth/access-token`. Verify with `validate` first. |

## Spec validation (caught before any API call)

| Error | Fix |
|-------|-----|
| `Spec is missing 'agentName'` | Add a top-level `agentName`. |
| `A parameter is missing its 'name'` | Every input/output param needs `name`. `position` is optional — it defaults to list order. |
| `Duplicate node 'objective' values: [...]` | Integrations map to nodes by exact objective text, so duplicates attach the tool to the wrong node. Make each objective distinct. |
| `Nodes derive the same toolFunctionName: ...` | Two nodes reduce to the same `GPTAction_Custom_<Name>`, so a re-deploy would collide. Give them distinct `name`/`tool_name`. |
| `Spec must contain a non-empty 'nodes' array` | Add at least one node. |
| `Duplicate node keys: [...]` | Every node `key` must be unique within the spec. |
| `Spec must have exactly one entry node` | Exactly one node needs `is_entry: true`. |
| `Node 'X' has an edge to unknown node 'Y'` | An edge `target` does not match any node `key`. Fix the typo. |
| `Linked param 'node.param' not found` | A `linked` input param's `linked_node`/`linked_param` does not match a real node key + output param name. The error lists the valid keys. |
| `condition_groups: sourceNodeKey 'X' is not a node key` | A `rule_based` rule references a node key that is not in the spec. |
| `waitingNode: linkedNodeKey 'X' is not a node key` | A `condition_based` wait node's `linkedNodeKey` must be an upstream node's spec key. |

## Deploy & API errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| `POST /agent-graphs/complete failed (400)` | Malformed payload. | Run `deploy --dry-run` and inspect the payload. Check node types, params, and edges against `references/spec-format.md`. |
| `PATCH /agent-graphs/update-node failed (400)` | Bad linked-param UUID, or a missing field on a manual attach. | Use `get-node` to read the real output-param UUIDs; make sure `linkParamOutputId` values exist. |
| `verificationPassed: false` in a deploy result | One or more `linked` params did not resolve. | Run `verify-links <agentId>` to see which. Usually a downstream node links to a node whose UUIDs changed during integration attach — re-run `deploy` (it re-links), or fix the `linked_node`/`linked_param` names. |
| Deploy succeeded but a node is **missing** after `deploy --agent-id` | A full redeploy drops any existing node not present in the spec. | Include **every** node you want to keep in the spec. For small edits use the quick-update commands instead. |
| An integration node maps to the wrong node, or `map_nodes` count is low | `deploy` matches spec nodes to created nodes by **objective text**. Two nodes shared an objective. | Give every node a unique `objective`. |
| A node-targeted command (`update-node-prompt`, `update-node-params`, …) errors with "invalid node id" or seems to hit the wrong node | The node id is stale — a full-graph write (`deploy --agent-id`, `add-node`, `remove-node`, `update-metadata`) reassigned every node id. | Re-run `get-nodes` to get current ids after any full-graph write, then retry. |
| Triggers disappeared after a redeploy | A trigger binds to a node id; a full-graph write reassigns ids and cascade-deletes triggers. | Finalize the graph first, then add triggers last (re-create them after a redeploy). |
| Agent created but the integration "does nothing" | The integration was not attached. | The spec's `integrations` array was empty, or you used `create` instead of `deploy`. Re-run `deploy` with the `integrations` array populated. |
| `linkParamOutputId` is `null` on a downstream node | Attaching a tool regenerated the source node's output-param UUIDs. | `deploy` re-links automatically. After a manual `attach-tool`, re-link the downstream node (`update-node`) and run `verify-links`. |

## Behaviour checks

| Symptom | Likely cause |
|---------|--------------|
| Only one of several actions runs | Multiple unconditional edges fan out from one node. Beam runs sequentially — chain the nodes (A → B → C) instead. |
| A condition node always takes the same branch | Edges are evaluated in order, first match wins. Re-order them, or tighten the earlier conditions. A too-broad first condition swallows the rest. |
| A `condition_based` wait never resumes | The linked tool's `allowWaiting` is `false`, the wait node is not directly downstream of the linked tool, or another node sits between them. Use `time_based`, or restructure so the wait node immediately follows the linked tool. |
| Changes are not live | The graph is still a draft. Publishing is a separate, explicit step — run `publish <graphId> --agent-id <agentId>` only when the user asks and `readiness` passes. |

## Inspecting state

- `get-nodes <agentId>` — node IDs, objectives, the graph ID.
- `get-node <agentId> <nodeId>` — params, `linkParamOutputId`s, output-param
  UUIDs, edge IDs.
- `get-graph <agentId> --full` — the entire raw graph.
- `verify-links <agentId>` — every linked param and whether it resolved.
- `readiness <agentId>` — every publish-required field and graph contract.
- `deploy <spec> --dry-run` — the exact payload, with no API call.
