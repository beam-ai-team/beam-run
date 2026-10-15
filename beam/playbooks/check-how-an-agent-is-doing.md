# Check how an agent is doing

## When to use

- "How is Invoice Matcher doing?", "success rate this month?", "average score and
  run time?", "why did failures jump last week?", "export last month's analytics".
- One agent's performance over time. Individual runs use
  `find-out-what-happened.md`.

## What you need first

- The agent, resolved with `agent.list`.
- The date range. If none is given, use the agent's `createdAt` (from `agent.get`)
  to today — not the current month.

## Steps

1. Read `agent.get` for the agent and its creation date.
2. Read `analytics.get` for the range. Report from the current period: total,
   completed and failed runs, average score, average and total run time, feedback
   and consent counts; and the change against the previous period.
3. To explain a change, list the runs behind it with `task.list` (status and date
   filters) and line them up with `agent.history`.
4. To export, run `analytics.export` for the range and share the link.

## Stop and ask

- Nothing here changes the agent. `analytics.export` creates a file and needs no
  confirmation.

## Done when

- The answer gives the figures exactly as returned, names the date range, and labels
  any cause as supported by the runs and change history, or as a guess.

## If it goes wrong

- No runs in the range: say so, and offer the full history.
- "Which tool fails most?": there is no single figure; it means reading failed runs,
  which takes longer. Offer to do it.
- Across all agents: there is no single figure; offer counts by status from
  `find-out-what-happened.md`.

## Actions

Generated from `../contracts/operations.yaml`; do not edit by hand. Run each
action through its MCP tool, or its CLI command when MCP is unavailable (always
the CLI in Codex). Re-read with the re-check action after a change.

| Action | MCP tool | CLI | Needs OK | Re-check | Notes |
| --- | --- | --- | --- | --- | --- |
| `agent.get` | `getAgentGraph` | `beam agents get <agentId>` | no | — | Shows activeGraphId (live) and draftGraphId (unpublished). Report the model token exactly as returned. createdAt is the default start date for analytics. |
| `agent.history` | `beam_get_graph_history` | `beam agents history <agentId>` | no | — | — |
| `agent.list` | `listAgents` | `beam agents list` | no | — | When more than one agent matches a name, ask which one; never pick by display name alone. |
| `analytics.export` | — | `beam analytics export <agentId> <startDate> <endDate>` | no | — | Returns a shareable file link. |
| `analytics.get` | `getAgentAnalytics` | `beam analytics get <agentId> [startDate] [endDate]` | no | — | Dates as Y-m-d. With no range given, use the agent's createdAt to today, not the current month. Read figures from currentPeriod and changes from metricsDelta. There is no per-tool failure figure; it has to be worked out from failed runs. |
| `task.list` | `listAgentTasks` | `beam tasks list` | no | — | For a count read totalCount, never the number of rows returned. isDraftTask true means test runs and false means real runs; without it the list mixes both. The agent id is at agentGraph.agent.id. Use a small page size. |
| `user.current` | `getCurrentUser` | `beam whoami` | no | — | Gives the user id that Learning Hub writes need. Never invent a user id. |
