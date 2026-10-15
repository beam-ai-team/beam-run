# Retry, stop or clean up runs

## When to use

- "Retry the last failure", "retry from step 4 with this feedback", "stop that run",
  "cancel the wait", "thumbs-down that output", "delete my old test runs".
- Not for answering a paused run's question or consent request: use
  `clear-whats-waiting-on-me.md`.

## What you need first

- The exact task ids. "The latest failure" means listing first; never act on a
  guess.
- For a retry from a step: the step's `taskNodeId` from `task.get`, and the feedback
  text.
- For cancelling a wait: the step must have status WAITING.

## Steps

1. Resolve the target runs with `task.list` (small page, newest first) or
   `task.latest`, then read each with `task.get`.
2. Act with the matching action:
   - retry the whole run, or from one step: `task.retry`
   - stop a running task: `task.abort`
   - cancel a step that is waiting: `task.cancel-wait`
   - rate the output: `task.rate`
   - delete runs: `task.delete`
3. Re-read with `task.get` (or `task.list` after a delete).

## Stop and ask

- `task.retry`: confirm when the run can act outside Beam (send, post, write), and
  always when retrying more than five runs.
- `task.abort`, `task.cancel-wait`, `task.delete`: always confirm, naming each task
  id. These cannot be undone.
- `task.rate` needs no confirmation.

## Done when

- The re-read shows the new state: a new or resumed run with its status, a stopped
  run, a cancelled wait, or the deleted runs gone from the list.

## If it goes wrong

- A retry fails the same way: stop retrying after the second attempt and continue
  with `find-out-what-happened.md`, then `change-an-agents-flow.md`.
- A delete or abort times out: re-read before trying again.
