# Explain how an agent works

## When to use

- "Walk me through the Invoice Matcher", "what triggers it?", "is its Gmail step
  connected?", "what's its webhook URL?", "what changed recently?", "are its links
  healthy?"
- Reading only. Any change goes to `change-an-agents-flow.md`.

## What you need first

- The agent, resolved with `agent.list` (ask if more than one matches).
- Whether the user means the live or the draft version, when both exist.

## Steps

1. Read the agent with `agent.get`: name, model, live and draft graph ids.
2. Read the structure with `graph.nodes`. Use `graph.node` for the steps that
   matter; fetch `graph.get` only when the full graph is truly needed.
3. Explain in order: how it starts (trigger or manual) → each step and what it
   does → branches, waits and loops → how it finishes.
4. As asked:
   - trigger: `graph.triggers` with the entry node id
   - webhook: `graph.webhook`
   - tools and whether their integrations are connected: `agent.tools`, then
     `integration.is-connected` per tool
   - sub-agents: `agent.sub-agents`
   - link health: `graph.verify-links`; whether it is ready to publish:
     `graph.readiness`
   - recent changes: `agent.history`

## Stop and ask

- Nothing here changes anything. No confirmation is needed.

## Done when

- The explanation follows the flow from start to finish, uses the real step names,
  and says which version (live or draft) it describes. Offer a short diagram when the
  flow has branches.

## If it goes wrong

- The user asks to change something: continue with `change-an-agents-flow.md`.
- A webhook URL is shown: remind the user that anyone with it can start runs.

## Actions

Generated from `../contracts/operations.yaml`; do not edit by hand. Run each
action through its MCP tool, or its CLI command when MCP is unavailable (always
the CLI in Codex). Re-read with the re-check action after a change.

| Action | MCP tool | CLI | Needs OK | Re-check | Notes |
| --- | --- | --- | --- | --- | --- |
| `agent.get` | `getAgentGraph` | `beam agents get <agentId>` | no | — | Shows activeGraphId (live) and draftGraphId (unpublished). Report the model token exactly as returned. createdAt is the default start date for analytics. |
| `agent.history` | `beam_get_graph_history` | `beam agents history <agentId>` | no | — | — |
| `agent.list` | `listAgents` | `beam agents list` | no | — | When more than one agent matches a name, ask which one; never pick by display name alone. |
| `agent.sub-agents` | `beam_list_sub_agents` | `beam agents sub-agents <agentId>` | no | — | — |
| `agent.tools` | `beam_get_agent_tools` | `beam agents tools <agentId>` | no | — | Report toolName, description and requiresConsent per tool. Each tool's toolFunctionName is the key for integration.is-connected. |
| `graph.get` | `getAgentGraph` | `beam agent-builder get-graph <agentId>` | no | — | Large (around 136 KB). Prefer graph.nodes for structure; fetch the full graph only for a node id or when the user asks for the whole thing. |
| `graph.node` | `getAgentGraph` | `beam agent-builder get-node <agentId> <nodeId>` | no | — | — |
| `graph.nodes` | `getAgentGraph` | `beam agent-builder get-nodes <agentId>` | no | — | Light list of node id and objective. The entry node has the objective 'Entry Node'. |
| `graph.readiness` | — | `beam agent-builder readiness <agentId>` | no | — | Every graph change returns this report. Resolve every failure before testing or publishing. |
| `graph.triggers` | `getAgentGraph` | `beam agent-builder get-triggers <agentId> <entryNodeId>` | no | — | Needs the entry node id from graph.nodes as well as the agent id. |
| `graph.validate` | — | `beam agent-builder validate` | no | — | Run before the first builder read or write. Exit 3 means sign in with beam login; exit 2 means a workspace is needed; exit 5 is a network problem (suggest beam doctor). Read the JSON next field on any failure. |
| `graph.verify-links` | `getAgentGraph` | `beam agent-builder verify-links <agentId>` | no | — | Report any broken link by node. Changes are checked with graph.readiness, which includes links. |
| `graph.webhook` | `getAgentGraph` | `beam agent-builder get-webhook <agentId>` | no | — | — |
| `integration.is-connected` | `beam_is_integration_connected` | `beam integrations is-connected <toolFunctionName>` | no | — | Workspace connection state. A step's own isIntegrationConnected is per-agent wiring; never infer one from the other. |
| `user.current` | `getCurrentUser` | `beam whoami` | no | — | Gives the user id that Learning Hub writes need. Never invent a user id. |
