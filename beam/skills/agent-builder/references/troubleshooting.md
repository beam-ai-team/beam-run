# Troubleshooting

When a `beam.py` command fails it prints `{"ok": false, "error": "..."}` and
exits non-zero. Match the message below.

## Credentials & connectivity

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Missing credentials: ...` | One or more credential env vars were not passed on the command. | Ask the user for the missing value(s). Prefix the command with all three: `BEAM_API_KEY=... BEAM_WORKSPACE_ID=... BEAM_API_URL=... python3 scripts/beam.py ...` |
| `Authentication failed (401)` / `(403)` | API key or workspace ID is wrong, expired, or revoked. | Ask the user for fresh credentials. A 403 can also mean the key lacks access to that workspace. |
| `cannot reach the Beam API` | `BEAM_API_URL` is wrong, or the API is down. | Confirm the URL with the user — it must point at their Beam API instance. |
| `auth/access-token did not return an idToken` | Trigger/webhook auth exchange failed. | The API key may be invalid, or the server has no `/auth/access-token`. Verify with `validate` first. |

## Spec validation (caught before any API call)

| Error | Fix |
|-------|-----|
| `Spec is missing 'agentName'` | Add a top-level `agentName`. |
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
| Changes are not live | The graph is still a draft. Publishing is a separate, explicit step — run `publish <graphId>` only when the user asks. |

## Inspecting state

- `get-nodes <agentId>` — node IDs, objectives, the graph ID.
- `get-node <agentId> <nodeId>` — params, `linkParamOutputId`s, output-param
  UUIDs, edge IDs.
- `get-graph <agentId> --full` — the entire raw graph.
- `verify-links <agentId>` — every linked param and whether it resolved.
- `deploy <spec> --dry-run` — the exact payload, with no API call.
