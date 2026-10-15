# Improve an agent from feedback

## When to use

- "What issues are open on my agent?", "why is this tool failing?", "has this been
  optimised before?", "which tool is worst?", "accuracy trend?", "run the tuner on
  this", "approve the last job", "merge these issues", "discard this",
  "send feedback on this run", "turn on auto-apply".
- The agent's Learning Hub. Hand edits to a prompt use `change-an-agents-flow.md`.

## What you need first

- The agent, resolved with `agent.list`.
- For writes that need it: the user id from `user.current`. Never invent one.

## Steps

1. Read, as asked:
   - open issues by tab: `learning.issues`; issues for one tool:
     `learning.list-issues`; one issue: `learning.issue`; its feedback:
     `learning.feedbacks`; its jobs: `learning.issue-jobs`
   - feedback for one step of a run: `learning.feedback-summary`
   - one job (status, score change, prompt before and after, failure reason):
     `learning.job`; what it did step by step: `learning.job-activity`
   - accuracy: `learning.trend`, then `learning.tools` for a per-tool ranking, and
     `learning.tool` for one tool
   - tuner settings: `learning.config`
2. Send feedback (no confirmation): `learning.submit-feedback` for one step,
   `learning.submit-task-feedback` for a whole run; correct earlier feedback with
   `learning.update-feedback`.
3. Act on issues and jobs:
   - optimise an issue: `learning.optimize`; merge: `learning.merge`;
     discard: `learning.discard`
   - approve, reject, re-optimise, cancel or run a job: `learning.approve-job`,
     `learning.reject-job`, `learning.reoptimize-job`, `learning.cancel-job`,
     `learning.run-job`
   - resume on-hold jobs: `learning.resume`
   - change tuner settings: `learning.set-config`
4. Re-read the issue or job afterwards.

## Stop and ask

- `learning.optimize`, `learning.merge`, `learning.discard`, `learning.approve-job`,
  `learning.reject-job`, `learning.reoptimize-job`, `learning.cancel-job`,
  `learning.run-job`, `learning.resume` and `learning.set-config` all use a
  proposal followed by a clear yes before execution, even when the user's first
  message already named the action. Anything else is not consent.
- **CLI (always in Codex):** read the target, show the exact proposed change and
  its impact, then wait. After approval, use the Actions table's command with
  `--confirm` and its exact target id (or `merge` for merging). For example,
  `beam learning approve-job <threadId> --confirm <threadId>`. Never pass
  `confirmed` or `--confirmed` to the CLI. Calling without `--confirm` only returns
  a local safety error; it does not generate a server-side proposal. A yes to an
  unchanged proposal proceeds without another approval question.
- **MCP on other hosts:** actions marked `always-two-turn` first run without
  `confirmed`, returning a confirmation message. Relay that message without
  softening the impact; after a clear yes, repeat the same arguments with
  `confirmed: true`. For `learning.optimize` (marked `always`), show the issue and
  credit cost, obtain approval, then call its mapped tool.
- `learning.approve-job` changes the live prompt: show the before and after first.
- `learning.optimize`, `learning.reoptimize-job`, `learning.run-job`,
  `learning.resume` cost credits.

## Done when

- The re-read shows the new state, and the user is told the job status and, when
  complete, its score change.

## If it goes wrong

- No issues, jobs or feedback: say so plainly; never invent a score change.
- Merging issues on different tools is not possible: say so.
- Feedback mapping is ambiguous: name the steps it could belong to and ask.

## Actions

Generated from `../contracts/operations.yaml`; do not edit by hand. Run each
action through its MCP tool, or its CLI command when MCP is unavailable (always
the CLI in Codex). Re-read with the re-check action after a change.

| Action | MCP tool | CLI | Needs OK | Re-check | Notes |
| --- | --- | --- | --- | --- | --- |
| `agent.get` | `getAgentGraph` | `beam agents get <agentId>` | no | — | Shows activeGraphId (live) and draftGraphId (unpublished). Report the model token exactly as returned. createdAt is the default start date for analytics. |
| `agent.list` | `listAgents` | `beam agents list` | no | — | When more than one agent matches a name, ask which one; never pick by display name alone. |
| `learning.approve-job` | `lh_approve_job` | `beam learning approve-job <threadId> --confirm <threadId>` | always-two-turn | `learning.job` | Applies the proposed prompt to the live tool; not directly reversible. Show the prompt before and after first. |
| `learning.cancel-job` | `lh_cancel_job` | `beam learning cancel-job <threadId> --confirm <threadId>` | always-two-turn | `learning.job` | Releases the feedback back to its issue. |
| `learning.config` | `lh_get_tuner_config` | `beam learning config <agentId>` | no | — | — |
| `learning.discard` | `lh_discard_issue` | `beam learning discard <agentId> <issueId> --confirm <issueId>` | always-two-turn | — | Archives the feedback and closes the issue. Needs workspaceId and userId (from user.current). |
| `learning.feedback-summary` | `lh_get_feedback_node_summary` | `beam learning feedback-summary <agentId> <taskNodeId>` | no | — | Feedback summary for one step of a run (taskNodeId from task.get). |
| `learning.feedbacks` | `lh_get_issue_feedbacks` | `beam learning feedbacks <agentId> <issueId>` | no | — | — |
| `learning.issue` | `getToolOptimizationStatus` | `beam learning issue <agentId> <issueId>` | no | — | Name the tool and its bucket when reporting an issue. |
| `learning.issue-jobs` | `lh_get_issue_jobs` | `beam learning issue-jobs <agentId> <issueId>` | no | — | — |
| `learning.issues` | `optimizeTool` | `beam learning issues <agentId>` | no | — | Tabs: issues (active), review (completed jobs awaiting a decision), archived. Default to issues. |
| `learning.job` | `getToolOptimizationStatus` | `beam learning job <threadId>` | no | — | Always report the job status, and scoreChange when completed. |
| `learning.job-activity` | `lh_get_job_activity` | `beam learning job-activity <agentId> <threadId>` | no | — | What a job did, step by step; use it to explain a failed or slow job. |
| `learning.list-issues` | `lh_list_issues` | `beam learning list-issues <agentId> [toolFunctionName] [sortBy]` | no | — | Issues for one tool, optionally sorted; use learning.issues for the tabbed overview. |
| `learning.merge` | `lh_merge_issues` | `beam learning merge <payloadFile> --confirm merge` | always-two-turn | — | Only issues on the same tool can be merged. |
| `learning.optimize` | `optimizeTool` | `beam learning optimize <agentId> <issueId> --confirm <issueId>` | always | — | Costs credits. Needs workspaceId and userId (from user.current). |
| `learning.reject-job` | `lh_reject_job` | `beam learning reject-job <threadId> --keep-feedbacks <true\|false> --confirm <threadId>` | always-two-turn | `learning.job` | keepFeedbacks true reuses the feedback; false archives it. |
| `learning.reoptimize-job` | `lh_reoptimize_job` | `beam learning reoptimize-job <threadId> --feedback <text> --confirm <threadId>` | always-two-turn | `learning.job` | Costs credits. |
| `learning.resume` | `lh_resume_on_hold_jobs` | `beam learning resume <agentId> --confirm <agentId>` | always-two-turn | `learning.issues` | Costs credits: starts one on-hold job per tool. |
| `learning.run-job` | `lh_run_job` | `beam learning run-job <threadId> --confirm <threadId>` | always-two-turn | `learning.job` | Costs credits. |
| `learning.set-config` | `lh_set_tuner_config` | `beam learning set-config <agentId> <payloadFile> --confirm <agentId>` | always-two-turn | `learning.config` | autoApply true means future jobs skip manual review. |
| `learning.submit-feedback` | `lh_submit_feedback` | `beam learning submit-feedback <payloadFile>` | no | — | — |
| `learning.submit-task-feedback` | `lh_submit_task_feedback` | `beam learning submit-task-feedback <payloadFile>` | no | — | May return isAmbiguous true; if so, say which steps it could apply to. |
| `learning.tool` | `lh_get_tool_detail` | `beam learning tool <agentId> <toolFunctionName> <startDate> <endDate> [nodesFilter]` | no | — | — |
| `learning.tools` | `lh_get_learning_tools` | `beam learning tools <agentId> <startDate> <endDate> [nodesFilter]` | no | — | — |
| `learning.trend` | `lh_get_accuracy_trend` | `beam learning trend <agentId> [startDate endDate]` | no | — | The default answer to 'how accurate is it?'. |
| `learning.update-feedback` | `lh_update_feedback` | `beam learning update-feedback <feedbackId> <payloadFile>` | no | — | — |
| `user.current` | `getCurrentUser` | `beam whoami` | no | — | Gives the user id that Learning Hub writes need. Never invent a user id. |
