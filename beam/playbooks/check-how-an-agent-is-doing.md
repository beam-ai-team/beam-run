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
