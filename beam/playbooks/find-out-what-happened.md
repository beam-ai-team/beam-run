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
