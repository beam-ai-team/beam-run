# Run an agent

## When to use

- "Run the Invoice Matcher on this file", "start a task on Customer Support:
  summarise today's tickets", "kick off the weekly report".
- A real run of the published (live) version.
- Not for trying unpublished changes: use `test-a-draft.md`.

## What you need first

- The agent, resolved by id or by `agent.list` (ask if more than one matches).
- Its live graph: `agent.get` shows `activeGraphId`. If the agent has no live
  graph, it has never been published — offer `test-a-draft.md` or
  `publish-a-draft.md` instead.
- The input the user wants to send.

## Steps

1. Resolve the agent and its live graph with `agent.list` and `agent.get`.
2. If the flow could touch the outside world (send email, post, update a
   record), say what it is likely to do and get the user's OK.
3. Start the run with `task.create-live`.
4. Read it back with `task.get`; report the task id and status, and any step that
   is waiting for consent or input.

## Stop and ask

- `task.create-live`: confirm first when the agent can send, post, write to another
  system or otherwise act outside Beam. Name the agent, the input and the likely
  effect. A run that only reads and summarises needs no extra question when the user
  asked for it directly.

## Done when

- `task.get` shows the run exists on the active graph, with its current status.
- If it paused for consent or input, the user is told, and offered
  `clear-whats-waiting-on-me.md`.

## If it goes wrong

- The returned graph is the draft, not the active graph: stop, say so, and do not
  start more runs.
- The run fails: continue with `find-out-what-happened.md` for that task id.
- The create call times out: check `task.list` for a new run before trying again.
