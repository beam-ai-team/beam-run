# Testing Beam Run locally (dev)

`v0.4.1` (branch `fix-UX`). API-key auth. Browser login is specified in
[`specs/browser-login.md`](specs/browser-login.md) — it removes the only step that
forces the user out of their coding agent.

> **Reporting to the user:** this is a dev runbook, but the *message you show the user* should still feel like onboarding. Show `beam setup`'s output (success line + emoji checklist + next steps) — do **not** rewrite it into a "what I did" table or status report. Report their remaining steps, not your actions.

## 1. Point your local install at this working copy
Your `~/.local/bin/beam` forwarder resolves the newest launcher under
`~/.config/beam-plugin/beam`, so install this build there:

```sh
cp -R beam "$HOME/.config/beam-plugin/beam"
chmod +x "$HOME/.config/beam-plugin/beam/bin/beam"
beam --version    # -> beam 0.4.1
```

## 2. Smoke test (read-only — never creates tasks)
```sh
sh test/smoke.sh                       # offline checks
BEAM_API_KEY='<your key>' sh test/smoke.sh   # + authenticated path (key via env, not argv)
```

## 3. Manual end-to-end
```sh
beam doctor            # green/red checklist with plain-language fixes
beam login             # hidden prompt  (or:  BEAM_API_KEY=… beam login)
beam whoami
beam workspace list
beam agents list
```

## 4. Tier A — direct HTTP MCP (no proxy, no Node/uv) on Claude Code
```sh
claude mcp add --transport http beam https://api.beamstudio.ai/mcp \
  --header "Authorization: Bearer <your key>"
```
Then **fully restart Claude Code** and ask *"list my Beam agents."*

## Notes
- **Never** pass the key as `beam login --api-key <key>` — it leaks to shell history. Use the hidden prompt, `BEAM_API_KEY`, or `--api-key -` (stdin).
- MCP reads the key at **startup** — any auth/config change needs a full agent restart.
- The committed `beam/.mcp.json` uses the stdio bridge, now backed by the vendored
  `beam/bin/mcp_proxy.py` (stdlib only — no npx/uvx). Signed out, it serves a live
  `beam_setup_status` tool instead of failing to start. `beam register` additionally wires
  the direct-HTTP entry, which is preferred where the host supports it.
- Telemetry is a **local placeholder** (`~/.config/beam/events.log`), disabled with `BEAM_TELEMETRY=0`; no network sink yet (SPEC-00).
