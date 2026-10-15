# Beam Run: one agent with playbooks

Built 15 October 2026 (version 0.7.0). Replaces the earlier "one skill that sorts requests into
12 screen areas" design.

## Outcome

When someone asks Beam Run for something in Claude Code, Codex or Cursor, one Beam agent picks
the playbook for that situation and follows it: what to check first, the steps, where to stop
and ask, and how to prove the job is done.

Nothing a user can do today goes away, and every safety stop stays.

## Why change

- Today's instructions are organised by Beam screen (Tasks, Inbox, Integrations and so on),
  because they were copied from Copilot, which lives inside those screens. People don't ask by
  screen. "Why did this fail, fix it and test it" crosses three screens, and the agent has to
  stitch them together on its own.
- The copied text describes things that don't exist in a coding tool: "the page you are on", a
  hidden context line at the top of each message, handing off to a "coordinator". The agent has
  to work around them on every request.
- The screen instructions list what tools exist, but not the order of steps for a job or what
  "finished" looks like. The flow-building instructions are already written as short playbooks
  (understand, design, approve, build, check, repair). This plan does the same for everything
  else.

## Before and after

| | Today | After |
| --- | --- | --- |
| Entry point | One public "Beam" skill that sorts requests into 12 screen areas | The same public "Beam" skill, rewritten as the agent's brief: who it is, its standing rules, and the list of playbooks |
| Instructions | 12 screen instructions plus 12 action tables, generated automatically from Copilot's text | 16 playbooks, one per situation, written by hand |
| Actions and safety | A list of 102 Beam actions, each with its backup route and whether it needs the user's OK; the flow-building actions were missing from it | 124 actions: the same list, the 13 flow-building actions (search tools, attach, triggers, webhooks and so on), the 9 actions main added for docs, models, readiness checks and Learning Hub, and the practical details for each action moved in from the screen instructions |
| Link to Copilot | Instructions are regenerated from a saved copy of Copilot and must match it word for word | The saved copy is kept only to warn us when Copilot's rules change; we decide what to carry over |
| Old specialist skills | Kept in a hidden folder for reference | Deleted once the playbooks are live |
| Setup and sign-in | Separate setup skill | Unchanged |

## The agent

One agent, carried by the existing public skill, so it behaves the same on every tool we support.
Its brief holds only the rules that apply to every request:

- **Workspace:** take it from the request, a Beam link, the remembered default, or the user's only
  workspace. Never switch silently.
- **Route:** use the direct Beam connection first. If a tool is missing or broken, use the
  command-line backup for the same action.
- **Narrate:** one line before (what it's about to do, and whether anything changes), one line
  after (what changed and how it checked).
- **Report:** only what Beam returned: exact names, counts and statuses.
- **Stop:** ask before anything the action list marks as needing the user's OK.
- **Chain:** pick a playbook. If the request spans several, run them in order, carrying the same
  workspace, agent and task between them.
- **No playbook fits:** read freely to answer. For any change, follow the action list's rules.

It does not pretend to be the in-product Copilot. It is also not a separate background helper:
a background helper cannot stop mid-job to ask before publishing or approving, so it would break
the safety stops.

## What a playbook is

One short file per situation, under one screen in length, always with the same six parts:

1. **When to use:** the situations and typical ways people ask, and where the boundary with
   neighbouring playbooks is.
2. **What you need first:** workspace, agent, run, and whether this is the draft or live version.
3. **Steps:** in order, each naming an action from the action list.
4. **Stop and ask:** the points that need the user's OK, and what to show them first.
5. **Done when:** what to re-check to prove it worked.
6. **If it goes wrong:** common failures, what to do next, and which playbook to continue with.

A playbook names the actions it uses. It never repeats how an action is carried out, its backup
route or its safety rule. Those live once, in the action list, so a safety rule cannot end up
different in two playbooks.

## The 16 playbooks

| Playbook | Handles | Replaces today's |
| --- | --- | --- |
| Get oriented | Who am I, which workspace, what agents exist; switch or create a workspace | General workspace |
| Run an agent | Start a real run with the user's input | Agent tasks (part) |
| Test a draft | Run unpublished changes without touching the live version | Agent tasks (part) |
| Find out what happened | Look up runs for one agent or across agents; explain a failure | Agent tasks (part), all-tasks view |
| Retry, stop or clean up runs | Retry from a failed step, stop a run, cancel a wait, rate, delete | Agent tasks (part) |
| Clear what's waiting on me | Notifications; approve or reject a consent request; answer a question a run is waiting on | Inbox |
| Explain how an agent works | Walk through a flow from trigger to finish, with no changes | Flow reader |
| Build a new agent | Understand the ask, propose a diagram, wait for OK, build as a draft, check it | Agent builder (part) |
| Change an agent's flow | Make the smallest change to an existing flow, show before and after when it matters, keep it as a draft | Agent builder (part) |
| Publish a draft | Make a draft live, only when clearly asked | Agent builder (part) |
| Connect or fix an integration | Check, connect, set the default, remove; custom integrations | Integrations |
| Start from a template | Find, check what it needs, create | Templates |
| Manage an agent's settings and files | Name, description, starter prompts, tools, files; delete an agent | Agent configuration |
| Check how an agent is doing | Volume, success rate, score, run time, export; link a dip to a change | Analytics |
| Improve an agent from feedback | Learning Hub issues, feedback, improvement jobs, approve or reject | Learning Hub |
| Work with Views | Saved Views, columns, records, export | Views |

Every one of the 124 actions is used by at least one playbook. An automatic check enforces this.

## What stays the same

- Setup, sign-in, choosing a workspace during onboarding, and the connection doctor.
- The command-line tool and the direct Beam connection.
- The original 102 actions, their backup routes and their confirmation rules.
- The plugin's name, and how people install and update it.

## Steps

Each step ends in something you can try for yourself.

1. **Pilot three playbooks (about 3 days).** Write the agent's brief plus "Find out what
   happened", "Clear what's waiting on me" and "Build a new agent": one that only reads, one with
   consent stops, and one long build. Run them side by side with today's skill on the same
   requests. Done when they handle those requests at least as well as today.
2. **Write the other 13 (about 1 week).** Move each action's practical details from the old
   screen instructions into the action list. Replace the automatic checks that look for exact
   sentences in today's skill with checks that every playbook names real actions, every action is
   covered, and every safety stop is still in place. Done when the checks pass and every old
   screen instruction has been gone through line by line with nothing dropped.
3. **Switch over (2 to 3 days).** Rewrite the public skill as the agent's brief, remove the 24
   generated instruction files and the step that generates them, and move the version to 0.7.0.
   Run the full request list on Claude Code, Codex and Cursor. Done when every request finishes
   correctly on all three, and setup behaves exactly as before.
4. **Clean up (half a day).** Delete the hidden old specialist skills. Update the README, the
   testing guide and the product promise document so they describe the agent and playbooks.

The day counts assume one engineer working with a coding agent. They are estimates, not
commitments.

## How we'll know it worked

Use one fixed list of about 20 real requests, taken from the existing testing plan, including
multi-step ones such as "find the failing run, explain why, fix the draft, test it, then show me
the numbers". Run every request on today's version and on the new one, in all three tools.

- **Nothing lost:** every request that works today still works.
- **Safety held:** every publish, approval, delete and live run still stops for the user's OK.
- **Better:** fewer wrong turns and unneeded questions on multi-step requests. We count them on
  both versions rather than promise a number now.

## Risks

| Risk | What you would notice | How we handle it |
| --- | --- | --- |
| Hard-won details in today's instructions get lost in the rewrite, such as "the task count is the total, not the number of rows shown" | A wrong count or a wrong first step on a request that used to work | Move every such detail into the action list next to the action it belongs to; check each old instruction line by line during step 2 |
| Beam Run drifts away from Copilot | Copilot and Beam Run give different answers about the same product rule | Keep comparing against Copilot; when its rules change we are warned and decide what to carry over |
| Two playbooks both seem to fit | The agent follows the wrong one | Each playbook's "When to use" states the boundary; the evals deliberately include unclear requests |
| A request fits no playbook | The agent improvises | The brief's fallback: read freely, and make changes only under the action list's rules |

## Decisions

Decided 15 October 2026: stop copying Copilot word for word (the saved copy stays as
a change warning), keep the 16 playbooks as listed, and build all of them in one go
rather than pausing after a three-playbook pilot. Whoever owns Copilot should be told
that Beam Run no longer mirrors its structure.

## For the engineer

- **New:** `beam/playbooks/<name>.md`, one per playbook above, each with the six headings.
- **Rewrite:** `beam/skills/beam/SKILL.md` becomes the agent brief with the playbook index inside
  it. Keep the skill name `beam` so installs and host discovery are unaffected. Absorb the useful
  rules from `beam/references/host-adapter.md` and `beam/contracts/fallback-policy.yaml`, and
  drop the Copilot-only parts of `beam/runtime/common.md` (page context line, `out-of-scope:`
  coordinator handoff, "never reveal the model").
- **Change:** `beam/contracts/operations.yaml` gains a `notes` field per operation for gotchas
  moved out of the domain cards. Playbooks reference operations by id (for example `task.retry`).
  The `specialist` field goes.
- **Fold:** `beam/internal/agent-builder/SKILL.md` and `phases/` become the build, change and
  publish playbooks. `references/`, `patterns/`, `templates/`, `assets/` and `scripts/` stay as
  reference material those playbooks link to.
- **Remove:** `beam/runtime/` (routes, common, 12 domain cards, 12 operations cards, manifest),
  `beam/scripts/compile_runtime_policy.py`, `beam/scripts/verify_runtime_policy.py`,
  `beam/internal/legacy-skills/`, `beam/references/host-adapter.md`. Update or remove
  `beam/contracts/copilot-parity.yaml`.
- **Keep untouched:** `beam/skills/setup/`, `beam/bin/beam`, `beam/bin/mcp_proxy.py`,
  `beam/contracts/context.yaml`, `GETTING_STARTED.md`. Keep `beam/references/copilot-baseline/`,
  its hash file and `test/copilot-source-drift.sh` as a change warning only.
- **Checks:** replace `test/runtime-policy-contract.sh` with a playbook check: every operation id
  named in a playbook exists; every operation is named by at least one playbook; every playbook
  has the six headings; every operation whose confirmation is not `none` appears under that
  playbook's "Stop and ask". Update the sentence checks in `test/supervisor-contract.sh`,
  `test/cross-host-contract.sh` and `test/activity-ux-contract.sh`. Move all four plugin
  manifests to 0.7.0 (Codex keeps its `+codex` suffix).
- **Docs:** update the Copilot-source invariant in `specs/supervisor-product-contract.md`, the
  module table in `specs/supervisor-testing-plan.md`, `README.md` and `TESTING.md`.
