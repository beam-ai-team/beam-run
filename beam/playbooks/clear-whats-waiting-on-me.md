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

## Actions

Generated from `../contracts/operations.yaml`; do not edit by hand. Run each
action through its MCP tool, or its CLI command when MCP is unavailable (always
the CLI in Codex). Re-read with the re-check action after a change.

| Action | MCP tool | CLI | Needs OK | Re-check | Notes |
| --- | --- | --- | --- | --- | --- |
| `inbox.delete` | — | `beam inbox delete <notificationId> --confirm <notificationId>` | always | — | Confirm every delete, and especially a sweep of many notifications. |
| `inbox.list` | — | `beam inbox list` | no | — | Each row carries agentId and agentTaskId; resolve the task from those. |
| `inbox.mark-read` | — | `beam inbox mark-read <notificationId>` | no | — | — |
| `inbox.unread-count` | — | `beam inbox unread-count` | no | — | — |
| `task.approve` | `approveTaskExecution` | `beam tasks approve <taskId> <taskNodeId> --confirm <taskNodeId>` | always | `task.get` | Before asking, show what the agent is about to do: the tool and its parameters from the paused step. |
| `task.get` | `getTaskDetails` | `beam tasks get <taskId>` | no | — | Fields are at the top level. agentTaskNodes[] holds each step's status; USER_CONSENT_REQUIRED and USER_INPUT_REQUIRED mark a paused step and carry its taskNodeId; the agent id is agentGraph.agentId. |
| `task.reject` | `rejectTaskExecution` | `beam tasks reject <taskId> <taskNodeId> --confirm <taskNodeId> [--reason <text>]` | always | `task.get` | Ends the task. |
| `task.submit-input` | `submitUserInput` | `beam tasks submit-input <taskId> <taskNodeId> <parameter> <answer>` | confirm-proposed-values | `task.get` | Answer the paused step's userQuestions. Never guess a value; propose it and get it confirmed. |
