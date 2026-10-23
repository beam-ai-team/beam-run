# Use test mode

## When to use

- "Turn on test mode", "run it in test mode with these five emails", "how many test
  runs are left?", "which connections are missing?", "use the test inbox for testing",
  "replay last week's failed tasks in test mode".
- A test session: the draft runs a set number of times on test connections, so the
  live agent and its live connections are left alone.
- A single trial of a draft with no session is `test-a-draft.md`; it runs on LIVE
  connections. A real run is `run-an-agent.md`.

## What you need first

- The agent id from `agent.get`.
- How many runs (2 to 200; default 2), and which test connection each step and
  trigger should use. Never suggest a live connection (`isLive: true`) as a test
  connection; when it is the only candidate, ask the user to add a separate one.
- Test mode runs the draft graph and test connections are read from it; live
  connections are read from the published graph. A connection id is the connection
  row id (`integrationProviderId`), not the integration id.

## Steps

1. Read `testmode.status` first. If it is on, reuse that session and skip step 4;
   if it is off and `exhausted`, every run of the last session is used.
2. Read `connection.missing` with mode test. For each missing row show its step, the
   integration and its non-live candidates and ask which to use; when its `nextStep`
   is a `beam://integrations` link, give that link. LLM-step tools without a test
   connection fall back to live until INT-11779 (`usesLiveInTest`). For every live
   and test connection, not only the missing ones, read `connection.summary`.
3. Set each chosen step or LLM-step tool with `connection.set`, mode test, or pass it
   as a tool override on `testmode.start`. List choices with `connection.options`.
   Trigger test connections go on start as trigger overrides.
4. Only when status was off, start the session with `testmode.start`, then re-read
   `connection.missing`. Never start again while it is on.
5. Run the inputs with `task.create-test`, at most `runsRemaining` of them. Read each
   with `task.get` and check its `agentGraphId` is the draft.
6. To replay past tasks instead, run `task.replay-test` with `--dry-run` first. Show
   each row's task id and the input it will send, and every `leftOut` id with its
   reason. After a yes, run it again without `--dry-run`; it uses one run per row.
7. End with `testmode.stop` when the user is done.

## Stop and ask

- `testmode.start`: confirm the agent, the number of runs and every override first;
  they cannot be changed while the session runs.
- `connection.set`: name the step, the mode and the connection. Mode live changes the
  published agent and its draft: get a yes before repeating it with `--confirm-live`,
  and report `nextPublishReverts` if it is true. A trigger's test connection restarts
  test mode: say runsUsed goes back to 0 and get a yes before `--confirm-restart`.
- `testmode.stop`: confirm; it ends the session and resets runsUsed.
- `task.create-test`: always confirm the agent, the inputs and the runs they use
  first. Test runs may still reach real integrations until INT-11779 enforces
  test-only connections, and MCP integrations always use their live connection.
- `task.replay-test`: the dry run starts nothing. Before the real replay, confirm the
  agent, the rows from the dry run and the runs they use; never replay a left-out id.

## Done when

- Status, runs used and runs remaining are reported from a fresh `testmode.status`.
- No missing test connection is left, or the user chose to go ahead with the rest.
- Each run is reported with its task id, status and a plain verdict; a replay also
  names the past task it came from and every task it left out.

## If it goes wrong

- Exit 6 `test_mode_active`: options are fixed at start; stop, then start again.
- Exit 7 `test_mode_inactive`: start test mode first.
- Exit 8 `test_runs_exhausted`: tell the user and offer a new session.
- A replay with every id left out exits 2 and starts nothing; read `leftOut`. Until
  beam-api #3943 is live, Beam rejects a replayed input with no `query` (exit 2).
- Exit 9 `permission_denied`: the role lacks access; ask an admin.
- Exit 10 `connections_missing`: work through each row's `nextStep`.
- Exit codes: `../internal/agent-builder/references/cli-reference.md`.

## Actions

Generated from `../contracts/operations.yaml`; do not edit by hand. Run each
action through its MCP tool, or its CLI command when MCP is unavailable (always
the CLI in Codex). Re-read with the re-check action after a change.

| Action | MCP tool | CLI | Needs OK | Re-check | Notes |
| --- | --- | --- | --- | --- | --- |
| `agent.get` | `getAgentGraph` | `beam agents get <agentId>` | no | — | Shows activeGraphId (live) and draftGraphId (unpublished). Report the model token exactly as returned. createdAt is the default start date for analytics. |
| `agent.list` | `listAgents` | `beam agents list` | no | — | When more than one agent matches a name, ask which one; never pick by display name alone. |
| `connection.missing` | — | `beam connections missing <agentId> [--mode live\|test]` | no | — | Only the missing rows; exit 0 when none, 10 (connections_missing) when any. A test connection that is not set is missing even where staging still falls back to live. MCP integrations show testConnection 'not settable yet (INT-11779)', usesLiveInTest true, and are not counted. Run each row's nextStep: a beam connections set command, or a beam://integrations link when the workspace has no connection for it. Test mode runs the draft graph and test connections are read from the draft; live connections are read from the active (published) graph. integrationProviderId and --connection are a connection row id, not an integration id. |
| `connection.options` | — | `beam connections options <agentId> --node <nodeId> [--tool <toolId>] \| --trigger <triggerId>` | no | — | Lists the active connections that can fill one slot. Pass --tool for an LLM-step tool. Test mode runs the draft graph and test connections are read from the draft; live connections are read from the active (published) graph. integrationProviderId and --connection are a connection row id, not an integration id. |
| `connection.set` | — | `beam connections set <agentId> --node <nodeId> [--tool <toolId>] \| --trigger <triggerId> --mode live\|test --connection <connectionId> [--confirm-live\|--confirm-restart]` | always | `connection.summary` | Sends only the connection field (PATCH /agent-graphs/:agentId/nodes/:nodeId/connection) and re-reads it; input params and output examples are untouched and no empty connection is sent. --mode live changes the published agent: the first call explains and changes nothing; repeat with --confirm-live only after the user agrees. It also writes the same connection to the draft so the next publish keeps it, and says nextPublishReverts: true when it could not. Never suggest the live connection as a test connection. A trigger's test connection restarts test mode and resets runsUsed to 0: the first call explains and changes nothing; repeat with --confirm-restart only after the user agrees. A trigger's live connection is changed in Beam, not here. Test mode runs the draft graph and test connections are read from the draft; live connections are read from the active (published) graph. integrationProviderId and --connection are a connection row id, not an integration id. |
| `connection.summary` | — | `beam connections summary <agentId> [--mode live\|test]` | no | — | One row per step tool, LLM-step tool, custom API tool, MCP integration and trigger, with liveConnection, testConnection, candidates, missing and nextStep, plus missingCount. Test mode runs the draft graph and test connections are read from the draft; live connections are read from the active (published) graph. integrationProviderId and --connection are a connection row id, not an integration id. |
| `task.create-test` | — | `beam test-mode run <agentId> --input <text>... \| --inputs-file <file>` | always | `task.get` | One test-mode run per input against the draft graph; needs test mode on. Returns the task ids, runsUsed and runsRemaining, and refuses before starting when the inputs exceed the runs left. Exit 7 when test mode is off, 8 when its runs are used. Test runs can still reach real integrations, and LLM-step tools without a test connection fall back to live until INT-11779. |
| `task.get` | `getTaskDetails` | `beam tasks get <taskId>` | no | — | Fields are at the top level. agentTaskNodes[] holds each step's status; USER_CONSENT_REQUIRED and USER_INPUT_REQUIRED mark a paused step and carry its taskNodeId; the agent id is agentGraph.agentId. |
| `task.replay-test` | — | `beam test-mode replay <agentId> --task <taskId>... \| --tasks-file <file> [--dry-run]` | always | `task.get` | Replays past tasks of this agent as test-mode runs, one per task. The input is each task's originalTaskQuery as stored, minus the top-level beamAgentOSTaskID, beamTaskId and beamTaskTimestamp (both spellings of beamAgentOSTaskID); every other key and anything nested is sent unchanged, and query is not required. Ids of another agent's task, a task not found, or one with no stored input or an input that is not a JSON object are listed under leftOut with the reason, never dropped. Repeated ids count once. --dry-run returns the dataset and leftOut and starts nothing; it needs no test mode. Otherwise it needs test mode on (exit 7), refuses before starting when the tasks exceed the runs left, and returns started (sourceTaskId, taskId), leftOut, runsUsed and runsRemaining. Needs beam-api #3943. |
| `testmode.start` | — | `beam test-mode start <agentId> [--max-runs N] [--trigger-connection triggerId=connectionId]... [--tool-connection nodeOrToolId=connectionId]...` | always | `testmode.status` | Default 2 runs, 2-200. Trigger and tool overrides can only be set here; a second start fails (test_mode_active, exit 6) while a session runs. Both override flags repeat. Test mode runs the draft graph and test connections are read from the draft; live connections are read from the active (published) graph. integrationProviderId and --connection are a connection row id, not an integration id. Test runs may still reach real integrations until INT-11779. |
| `testmode.status` | — | `beam test-mode status <agentId>` | no | — | Reports testMode on/off, runsUsed, maxRuns, runsRemaining and startedAt. A session that used every run switches itself off and shows exhausted: true. |
| `testmode.stop` | — | `beam test-mode stop <agentId>` | always | `testmode.status` | Ends the session, removes its test triggers and resets runsUsed to 0. Exit 7 (test_mode_inactive) when it is already off. |
| `user.current` | `getCurrentUser` | `beam whoami` | no | — | Gives the user id that Learning Hub writes need. Never invent a user id. |
