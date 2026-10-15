# Find out what happened

## When to use

- "Why did the last run fail?", "what has Invoice Matcher done today?",
  "how many tasks failed this week?", "which agents have been running?",
  "compare these two runs", "show my test runs".
- One agent or across the whole workspace. Reading only.
- Not for "how is it doing over time" with rates and scores: use
  `check-how-an-agent-is-doing.md`.

## What you need first

- The scope: one agent (resolve with `agent.list`), a named task id, or the whole
  workspace.
- Whether the user means real runs or test runs. Filter on it; never mix them in
  a count.

## Steps

1. If a task id is given, go straight to `task.get`.
2. For "latest runs" on one agent, use `task.latest`.
3. For counts by status, use `task.statuses` (pass agent ids to narrow).
   For "which agents are running", use `task.agents`.
4. To find specific runs, use `task.list` with status, date, agent, search text and
   the test-or-real filter. For a count, report `totalCount`.
5. Read the chosen run with `task.get`. Walk its steps in order and name the one
   that failed or paused, with its input, output and error.
6. When it helps, read that step's setup with `graph.nodes` and `graph.node`, and
   check `agent.history` for a recent change that lines up with the failure.

## Stop and ask

- Nothing here changes anything. No confirmation is needed.

## Done when

- The answer names the run (task id), its status, the step that matters, and the
  cause as far as the data shows it. Anything inferred is labelled as such.

## If it goes wrong

- No runs match: say so plainly; check whether the user meant tests or real runs, or
  another workspace.
- The user wants a fix: continue with `change-an-agents-flow.md` (fix the flow) or
  `retry-stop-or-clean-up-runs.md` (retry the run).
- "What's the overall success rate across all agents?": there is no single figure.
  Offer counts by status, or per-agent analytics.

## Actions

Generated from `../contracts/operations.yaml`; do not edit by hand. Run each
action through its MCP tool, or its CLI command when MCP is unavailable (always
the CLI in Codex). Re-read with the re-check action after a change.

| Action | MCP tool | CLI | Needs OK | Re-check | Notes |
| --- | --- | --- | --- | --- | --- |
| `agent.history` | `beam_get_graph_history` | `beam agents history <agentId>` | no | — | — |
| `agent.list` | `listAgents` | `beam agents list` | no | — | When more than one agent matches a name, ask which one; never pick by display name alone. |
| `graph.node` | `getAgentGraph` | `beam agent-builder get-node <agentId> <nodeId>` | no | — | — |
| `graph.nodes` | `getAgentGraph` | `beam agent-builder get-nodes <agentId>` | no | — | Light list of node id and objective. The entry node has the objective 'Entry Node'. |
| `task.agents` | `beam_list_task_agents` | `beam tasks agents` | no | — | — |
| `task.get` | `getTaskDetails` | `beam tasks get <taskId>` | no | — | Fields are at the top level. agentTaskNodes[] holds each step's status; USER_CONSENT_REQUIRED and USER_INPUT_REQUIRED mark a paused step and carry its taskNodeId; the agent id is agentGraph.agentId. |
| `task.latest` | `beam_get_latest_task_executions` | `beam tasks latest <agentId> [pageSize]` | no | — | Preferred over task.list for 'show me the latest runs' on one agent. |
| `task.list` | `listAgentTasks` | `beam tasks list` | no | — | For a count read totalCount, never the number of rows returned. isDraftTask true means test runs and false means real runs; without it the list mixes both. The agent id is at agentGraph.agent.id. Use a small page size. |
| `task.statuses` | `beam_get_task_statuses` | `beam tasks statuses [agentIds]` | no | — | Counts by status; pass agent ids to narrow. There is no single success rate across all agents, so never invent one. |
