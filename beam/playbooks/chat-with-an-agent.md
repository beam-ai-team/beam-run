# Chat with an agent

## When to use

- "Chat with the Invoice Matcher", "ask Customer Support what it thinks of this
  ticket", "talk to my research agent", then a back-and-forth: follow-up
  questions, "make it shorter", "now do the same for March".
- Beam has no chat feature: every message is a run. This playbook keeps the
  thread together so the user never has to think about runs.
- Not for a single one-off run with no conversation: use `run-an-agent.md`.

## What you need first

- The agent, resolved with `agent.list` and `agent.get`. Ask if more than one
  matches.
- Live or draft. Chat with the live version unless the user asks to try the
  draft. With no live graph, offer the draft.
- Whether the agent can act outside Beam (send, post, write to another system).
  Read it from the agent's steps and integrations, and tell the user once at the start.
- The conversation so far, kept by you: each user message and the agent's reply,
  in a sentence or two each.

## Steps

1. Open the chat: name the agent, live or draft, and anything it can do outside Beam.
2. For each user message, build the run input:
   - first message: the user's words as they are;
   - every later message, including "change your last answer": start with
     "Earlier in this conversation:", one line per earlier message and reply,
     then "My new message:" and the user's words. The agent remembers nothing
     between runs; this block is its only memory.
3. Start the run: `task.create-live`, or `task.create-draft` for the draft.
4. Wait for it with `task.wait`, then act on the status it returns:
   - USER_INPUT_REQUIRED: show the agent's question in plain words. Send the
     user's reply with `task.submit-input`, then `task.wait` again.
   - USER_CONSENT_REQUIRED: show exactly what the agent wants to do. On a yes,
     `task.approve`; on a no, `task.reject`. Then `task.wait` again.
   - COMPLETED: the reply is the output of the last step that has one. Show it
     in plain words, not as raw data. Add it to the conversation.
   - anything else: say the run did not finish and continue with
     `find-out-what-happened.md`.
5. Once per chat, after the first follow-up, use `task.get` to check what the
   agent's first working step received. If it kept only the newest line and dropped the
   earlier conversation, tell the user: this agent handles one message at a
   time, so each message must stand on its own. Offer
   `change-an-agents-flow.md` to make that step take the whole input.
6. "Stop": `task.abort` on a run that is still going.

## Stop and ask

- `task.create-live`: when the agent can act outside Beam, ask before every
  message's run, naming the likely effect. One message can trigger one action.
  A read-and-reply agent needs no extra question.
- `task.submit-input`: if the user has not answered yet, ask them and wait.
  Send the user's reply as they wrote it. If you filled in
  or reworded anything, including reusing an answer from earlier in the chat,
  show the value and wait for a yes.
- `task.approve` and `task.reject`: always, as the agent asked.
- `task.abort`: always; say the run's work so far stops.
- `task.create-draft` needs no extra question.

## Done when

- Each message ends with the agent's reply shown, a question put to the user,
  or a plain statement that the run failed or was stopped.
- The user can keep going without repeating themselves.

## If it goes wrong

- `task.wait` reports the run is still running: say so, wait once more, then
  offer to check back later with `task.get`.
- The answer to a question is rejected: re-read the run with `task.get`; the
  step may already have moved on.
- The reply ignores earlier messages: see step 5.
- Do not re-run a step with feedback to change an answer. Beam stores the
  feedback but the agent does not use it; send a new message as in step 2.

## Actions

Generated from `../contracts/operations.yaml`; do not edit by hand. Run each
action through its MCP tool, or its CLI command when MCP is unavailable (always
the CLI in Codex). Re-read with the re-check action after a change.

| Action | MCP tool | CLI | Needs OK | Re-check | Notes |
| --- | --- | --- | --- | --- | --- |
| `agent.get` | `getAgentGraph` | `beam agents get <agentId>` | no | — | Shows activeGraphId (live) and draftGraphId (unpublished). Report the model token exactly as returned. createdAt is the default start date for analytics. |
| `agent.list` | `listAgents` | `beam agents list` | no | — | When more than one agent matches a name, ask which one; never pick by display name alone. |
| `task.abort` | — | `beam tasks abort <taskId> --confirm <taskId> [--reason <text>]` | always | `task.get` | Stops a running task; different from task.cancel-wait. |
| `task.approve` | `approveTaskExecution` | `beam tasks approve <taskId> <taskNodeId> --confirm <taskNodeId>` | always | `task.get` | Before asking, show what the agent is about to do: the tool and its parameters from the paused step. |
| `task.create-draft` | — | `beam tasks test <agentId> <input>` | no | `task.get` | Runs the unpublished draft. For a batch, check the first task's agentGraphId before sending the rest. |
| `task.create-live` | `createAgentTask` | `beam tasks create <agentId> <input>` | required-if-production-side-effect | `task.get` | Needs a concrete agent id; send the input as an object, not a pre-stringified value. Check the returned graph is the active graph. |
| `task.get` | `getTaskDetails` | `beam tasks get <taskId>` | no | — | Fields are at the top level. agentTaskNodes[] holds each step's status; USER_CONSENT_REQUIRED and USER_INPUT_REQUIRED mark a paused step and carry its taskNodeId; the agent id is agentGraph.agentId. |
| `task.reject` | `rejectTaskExecution` | `beam tasks reject <taskId> <taskNodeId> --confirm <taskNodeId> [--reason <text>]` | always | `task.get` | Ends the task. |
| `task.submit-input` | `submitUserInput` | `beam tasks submit-input <taskId> <taskNodeId> <parameter> <answer>` | confirm-proposed-values | `task.get` | The questions are the paused step's input[] entries with found false; send that entry's exact question text as the question and its name as the parameter; the API rejects any other question text (the CLI looks it up for you). Never guess a value; propose it and get it confirmed. |
| `task.wait` | — | `beam tasks wait <taskId> [--timeout seconds]` | no | — | Re-reads the task every few seconds and returns it once it is no longer queued or running: finished, failed, or paused for consent or input. Beam's live task updates feed sends nothing, so do not use it. Right after an answer or approval the old pause can still show for a moment; if the same step is still paused for the same thing, wait again. |
| `user.current` | `getCurrentUser` | `beam whoami` | no | — | Gives the user id that Learning Hub writes need. Never invent a user id. |
