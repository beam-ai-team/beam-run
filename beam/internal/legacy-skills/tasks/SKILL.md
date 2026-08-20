---
name: tasks
description: Beam tasks — create agent tasks, monitor progress, submit user input, and approve or reject consent steps. Use when running or operating Beam agent work from the coding agent.
---

# Beam tasks

This is a compatibility entry point. Load `supervisor` first, then use
`agent-tasks` for one resolved agent, `global-tasks` for workspace-wide work, or
`inbox` for consent and requested input. Those specialists own the Copilot-aligned
prompt and the MCP-to-CLI completion rule.

Prefer **MCP tools** for interactive task operations.

Before the first call, resolve the workspace from an explicit request/URL, then
`beam workspace`, then a sole membership. If multiple remain and no context decides,
ask the user once and remember the answer with `beam workspace <id>`. Pass that ID to every MCP tool.
If an agent/task is missing or a list is empty, name the current workspace and ask
whether the user wants to switch with `beam workspace list <search>` and
`beam workspace <id>`. Never scan or switch all workspaces silently.

## Create

- **Choose the graph before creating anything.** Inspect the agent's active and
  draft graph IDs. A task is either a live run or a draft test; never assume the
  two are interchangeable.
- Infer the target from the strongest available context, without burdening the
  user with a routine choice: explicit “draft/unpublished/current changes” means
  draft; explicit “live/production” means live; a test requested after relevant
  draft work in the current conversation means draft; and a normal task request
  with no relevant unpublished-work context means live. The mere existence of an
  old or unrelated draft does not make a normal task ambiguous.
- If the user explicitly selects the draft, use `beam tasks test <agentId>
  <input>`. This sends `isDraftTask: true`; `createAgentTask` cannot select a
  draft graph.
- If the user explicitly selects the live agent, or asks to run a normal task
  without relevant unpublished work, use MCP: `createAgentTask`.
- Ask one focused question only when the coding agent cannot resolve a genuine
  conflict or missing fact after using the conversation and graph state—for
  example, the request explicitly refers to both live and draft behavior, or it
  cannot identify which unpublished change the test should cover. Do not ask
  merely because both graph versions exist.
- For multiple cases, create one task first and confirm its returned
  `agentGraphId` matches the selected graph before creating the rest. State the
  selected mode and graph in the result: “draft test” or “live task.”
- When the user has clearly named the agent and supplied the input, treat that as
  authorization to create the task; do not ask them to repeat it. Ask only when
  the agent, input, **graph target**, or immediate external side effect is
  ambiguous.
- Return the task id and a one-line status, plus a link/path if the tool provides one.

## Monitor

- MCP: `listAgentTasks`, `getTaskDetails`, `getTaskUpdates`
- Narrate status changes; don't stream raw SSE payloads to the user.

## Human-in-the-loop

When a task pauses for consent or input:

- MCP: `submitUserInput`, `approveTaskExecution`, `rejectTaskExecution`
- **Always** get explicit user approval before approving a consent step.
- For reject, confirm reason/intent with the user first.

## Retry / rate

- MCP: `retryTaskExecution`, `rateTaskOutput` when the user asks to retry or give feedback.

## Transport fallback

Before assuming a tool exists, use `beam mcp check --tool <toolName>` when the
host's tool inventory is uncertain. On a missing tool, malformed result, transport
failure, or a known MCP defect, run the mapped `beam tasks ...` command from
`../../../contracts/operations.yaml`. Do not repeat an ambiguous write: read the task
first and retry only when the prior write is known not to have applied.

## Safety

Creating and approving tasks can trigger real side effects (email, CRM, tickets).
State the side-effect risk in one sentence and obtain clear natural-language
authorization when the action touches production systems.
