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
  two-turn confirmation. First call it without
  `confirmed`: it returns a message describing the impact. Send that message to the
  user as is — do not soften it or add a second question. Only after a clear yes,
  call the same action again with the same values and `confirmed: true`. Anything
  other than a clear yes is not consent. This applies even when the user's first
  message already named the action.
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
