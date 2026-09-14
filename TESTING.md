# Testing Beam Run locally (dev)

`v0.6.0`. API-key login derives the instance from a Beam workspace URL, then
selects and locks one workspace for the session. See
[`specs/api-key-login.md`](specs/api-key-login.md).

> **Reporting to the user:** this is a dev runbook, but the *message you show the user* should still feel like onboarding. Show `beam setup`'s output (success line + emoji checklist + next steps) — do **not** rewrite it into a "what I did" table or status report. Report their remaining steps, not your actions.

## 1. Point your local install at this working copy
Point the local launcher at this working copy:

```sh
ln -sfn "$(pwd)/beam/bin/beam" "$HOME/.local/bin/beam"
beam --version    # -> beam 0.6.0
```

## 2. Smoke test (read-only — never creates tasks)
```sh
sh test/smoke.sh                       # offline checks
sh test/runtime-policy-contract.sh      # generated policy cards and high-risk guardrails
sh test/cross-host-contract.sh          # same public skill surface on every host
sh test/activity-ux-contract.sh         # grouped, user-facing operation narration
sh test/supervisor-contract.sh          # CLI fallback and safety contracts
sh test/copilot-source-drift.sh         # byte-for-byte comparison when Copilot checkout exists
BEAM_WORKSPACE_URL='<url>' BEAM_API_KEY='<your key>' sh test/smoke.sh
```

The complete module-by-module review is in
[`specs/supervisor-testing-plan.md`](specs/supervisor-testing-plan.md). It covers
the normal MCP path, forced CLI fallback, ambiguous-write reconciliation,
confirmation gates, context continuity, and response quality. The universal
runtime adds generated-card and cross-host contract checks before any manual test.

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
beam login             # workspace URL, masked key, workspace selection
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
Then **fully restart Claude Code** and ask *"list my Beam agents."*

## Notes
- **Never** pass the key as `beam login --api-key <key>` — it leaks to shell history. Use the masked prompt, `BEAM_API_KEY`, or `--api-key -`.
- MCP reads the key at **startup** — any auth/config change needs a full agent restart.
- The committed `beam/.mcp.json` uses the stdio bridge, now backed by the vendored
  `beam/bin/mcp_proxy.py` (stdlib only — no npx/uvx). Signed out, it serves a live
  `beam_setup_status` tool instead of failing to start. `beam register` additionally wires
  the direct-HTTP entry, which is preferred where the host supports it.
- Telemetry is a **local placeholder** (`~/.config/beam/events.log`), disabled with `BEAM_TELEMETRY=0`; no network sink yet (SPEC-00).
