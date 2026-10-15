# Clear what's waiting on me

## When to use

- "What's waiting on me?", "why was I pinged?", "approve the email it wants to
  send", "reject that", "answer what it's asking", "mark everything read",
  "clear my read notifications", "how many unread?"
- Not for retrying or stopping runs: use `retry-stop-or-clean-up-runs.md`.

## What you need first

- The notification or task. Start from the feed unless the user named a task id.
- For a consent or input decision: the paused step, read from the task itself.

## Steps

1. For a count only, use `inbox.unread-count`. Otherwise list with `inbox.list`
   (unread, read or all; optionally by agent).
2. For each relevant row, read the task with `task.get` (using the row's
   `agentTaskId`) and find the paused step:
   - status USER_CONSENT_REQUIRED: the agent wants to run a tool; show which tool
     and with which values.
   - status USER_INPUT_REQUIRED: the agent is asking `userQuestions`; propose
     answers only from what the user has said or the run already contains.
3. Act:
   - let the tool run: `task.approve`
   - refuse it (ends the task): `task.reject`
   - supply the requested values: `task.submit-input`
   - mark read: `inbox.mark-read`
   - delete notifications: `inbox.delete`
4. Re-read the task with `task.get` after an approve, reject or input.

## Stop and ask

- `task.approve`: always. Show exactly what the agent will do, then wait for a
  clear yes.
- `task.reject`: always; say that it ends the task.
- `task.submit-input`: confirm the proposed values. Never guess a value.
- `inbox.delete`: always, and name how many notifications a sweep removes.
- `inbox.mark-read` needs no confirmation.

## Done when

- After a decision, `task.get` shows the step moved on (running, completed or
  rejected). After clean-up, the feed or unread count reflects it.

## If it goes wrong

- The value needed for an input is not known: ask the user; do not invent it.
- The feed is empty: say so plainly.
- The approved run then fails: continue with `find-out-what-happened.md`.
