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
   Before a retry, refresh the agent's graph with `agent.get`, its tools and consent
   with `agent.tools`, and workspace connections with `integration.connected`.
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

## Actions

Generated from `../contracts/operations.yaml`; do not edit by hand. Run each
action through its MCP tool, or its CLI command when MCP is unavailable (always
the CLI in Codex). Re-read with the re-check action after a change.

| Action | MCP tool | CLI | Needs OK | Re-check | Notes |
| --- | --- | --- | --- | --- | --- |
| `agent.get` | `getAgentGraph` | `beam agents get <agentId>` | no | — | Shows activeGraphId (live) and draftGraphId (unpublished). Report the model token exactly as returned. createdAt is the default start date for analytics. |
| `agent.list` | `listAgents` | `beam agents list` | no | — | When more than one agent matches a name, ask which one; never pick by display name alone. |
| `agent.tools` | `beam_get_agent_tools` | `beam agents tools <agentId>` | no | — | Report toolName, description and requiresConsent per tool. Each tool's toolFunctionName is the key for integration.is-connected. |
| `integration.connected` | — | `beam integrations connected` | no | — | Only status 'active' counts as connected; pending and inactive do not. |
| `task.abort` | — | `beam tasks abort <taskId> --confirm <taskId> [--reason <text>]` | always | `task.get` | Stops a running task; different from task.cancel-wait. |
| `task.cancel-wait` | `task_cancel_wait_node` | `beam tasks cancel-wait <taskNodeId> <agentId> --confirm <taskNodeId>` | always | `task.get` | Only for a step whose status is WAITING. The agent id is agentGraph.agentId from task.get. |
| `task.delete` | — | `beam tasks delete <taskId> --confirm <taskId>` | always | `task.list` | — |
| `task.get` | `getTaskDetails` | `beam tasks get <taskId>` | no | — | Fields are at the top level. agentTaskNodes[] holds each step's status; USER_CONSENT_REQUIRED and USER_INPUT_REQUIRED mark a paused step and carry its taskNodeId; the agent id is agentGraph.agentId. |
| `task.latest` | `beam_get_latest_task_executions` | `beam tasks latest <agentId> [pageSize]` | no | — | Preferred over task.list for 'show me the latest runs' on one agent. |
| `task.list` | `listAgentTasks` | `beam tasks list` | no | — | For a count read totalCount, never the number of rows returned. isDraftTask true means test runs and false means real runs; without it the list mixes both. The agent id is at agentGraph.agent.id. Use a small page size. |
| `task.rate` | `rateTaskOutput` | `beam tasks rate <taskId> <up\|down> [feedback]` | no | — | — |
| `task.retry` | `retryTaskExecution` | `beam tasks retry <taskId> [--task-node-id <taskNodeId> --feedback <text>]` | required-if-production-side-effect | `task.get` | Retry from a step needs one task id plus the taskNodeId and feedback text. Confirm before retrying more than five. |
| `user.current` | `getCurrentUser` | `beam whoami` | no | — | Gives the user id that Learning Hub writes need. Never invent a user id. |
