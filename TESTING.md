# Testing Beam Run locally (dev)

`v0.7.0`. `beam login <instance or workspace URL>` derives the instance, connects through the
browser, then selects and locks one workspace for the session. See
[`specs/browser-connect.md`](specs/browser-connect.md); the key flow it falls back to
is in [`specs/api-key-login.md`](specs/api-key-login.md).

> **Reporting to the user:** this is a dev runbook, but the *message you show the user* should still feel like onboarding. Show `beam setup`'s output (success line + emoji checklist + next steps) — do **not** rewrite it into a "what I did" table or status report. Report their remaining steps, not your actions.

## 1. Point your local install at this working copy
Point the local launcher at this working copy:

```sh
ln -sfn "$(pwd)/beam/bin/beam" "$HOME/.local/bin/beam"
beam --version    # -> beam 0.7.0
```

## 2. Smoke test (read-only — never creates tasks)
```sh
sh test/smoke.sh                       # offline checks
sh test/playbook-contract.sh            # brief, playbooks and action list agree; safety stops intact
python3 beam/scripts/check_playbooks.py --write   # refresh each playbook's Actions table after editing operations.yaml
sh test/cross-host-contract.sh          # same public skill surface on every host
sh test/activity-ux-contract.sh         # grouped, user-facing operation narration
sh test/supervisor-contract.sh          # CLI fallback and safety contracts
sh test/connect.sh                      # browser Connect against a fake Beam (offline)
sh test/no-real-config.sh               # guard: no suite edits a real ~/.claude.json or ~/.cursor config
BEAM_WORKSPACE_URL='<url>' BEAM_API_KEY='<your key>' sh test/smoke.sh
```

The complete module-by-module review is in
[`specs/supervisor-testing-plan.md`](specs/supervisor-testing-plan.md). It covers
the normal MCP path, forced CLI fallback, ambiguous-write reconciliation,
confirmation gates, context continuity, and response quality.

### Playbook evals

`test/evals/playbook-evals.json` holds 36 realistic requests covering all 17
playbooks, multi-step work, safety traps and a non-Beam request. Each records the
actions a correct plan must include, must never do, and must stop before.

1. Give each request (with its `situation`) to a coding agent with this plugin
   loaded, using the eval file's `runner_prompt` (Beam stays disconnected; the agent
   writes down the plan it would carry out). Collect the JSON objects into one array.
2. Score it:

   ```sh
   python3 test/evals/score_playbook_evals.py plans.json
   ```

   Use `--no-playbooks` to score a version that predates playbooks. The summary
   counts missing steps, wrong turns, unsafe actions (no stop where one is
   required), unneeded questions, and ordering mistakes.

### Activity UX review — each supported host

For Codex, Claude Code, and Cursor, run the same four prompts and inspect the
conversation rather than the host's native tool-row labels:

| Scenario | Expected Beam message before work | Expected result message |
| --- | --- | --- |
| Read an agent | Names the agent and says no changes | Names the facts found; no technical command narration |
| Inspect a draft flow | Names graph, trigger, and integration checks; says no changes | States draft/published state and link health |
| Start a draft test | Names the draft target and says no external action will occur without consent | States task ID/status and whether consent or input is required |
| Propose a change | Names the target and intended effect before confirmation | On approval, names the changed entity, resulting state, and verification |

The host may still render a generic terminal/MCP activity row. That is host UI;
the two Beam messages above and below it are the portable visibility contract.

## 3. Manual end-to-end
```sh
beam doctor            # green/red checklist with plain-language fixes
beam login app               # or staging, enterprise, a region such as anz, or a workspace URL; prints the Connect link
beam login --wait app        # repeat until it says connected
beam whoami
beam checkout          # choose and lock this session
beam workspace list    # narrow by name or ID when needed
beam agents list
```

## 4. Tier A — direct HTTP MCP (no proxy, no Node/uv) on Claude Code
```sh
claude mcp add --transport http beam https://api.beamstudio.ai/mcp \
  --header "Authorization: Bearer <your key>"
```
Then ask *"list my Beam agents."* (restart Claude Code only if the entry was just added and the tools do not appear).

## Notes
- **Never** pass the key as `beam login --api-key <key>` — it leaks to shell history. Connect needs no key; for the older flow use the masked prompt (`--api-key`), `BEAM_API_KEY`, or `--api-key -`.
- No restart is required after connecting: the MCP bridge re-reads the saved connection on every message. It is needed only when the plugin itself was just installed.
- Local dev: `BEAM_LOCAL_DEV=1 beam login http://localhost:3000` (API from `BEAM_LOCAL_API_URL`, default `http://localhost:4000`).
- The committed `beam/.mcp.json` uses the stdio bridge, now backed by the vendored
  `beam/bin/mcp_proxy.py` (stdlib only — no npx/uvx). Signed out, it serves a live
  `beam_setup_status` tool instead of failing to start. `beam register` additionally wires
  the direct-HTTP entry, which is preferred where the host supports it.
- Telemetry is a **local placeholder** (`~/.config/beam/events.log`), disabled with `BEAM_TELEMETRY=0`; no network sink yet (SPEC-00).
