# Testing Beam Run locally (dev)

`v0.5.0`. API-key login validates a remembered default, auto-sets a sole membership,
or leaves context for the coding agent to resolve. See [`specs/api-key-login.md`](specs/api-key-login.md).

> **Reporting to the user:** this is a dev runbook, but the *message you show the user* should still feel like onboarding. Show `beam setup`'s output (success line + emoji checklist + next steps) — do **not** rewrite it into a "what I did" table or status report. Report their remaining steps, not your actions.

## 1. Point your local install at this working copy
Your `~/.local/bin/beam` forwarder resolves the newest launcher under
`~/.config/beam-plugin/beam`, so install this build there:

```sh
cp -R beam "$HOME/.config/beam-plugin/beam"
chmod +x "$HOME/.config/beam-plugin/beam/bin/beam"
beam --version    # -> beam 0.5.0
```

## 2. Smoke test (read-only — never creates tasks)
```sh
sh test/smoke.sh                       # offline checks
BEAM_API_KEY='<your key>' sh test/smoke.sh   # + authenticated path (key via env, not argv)
```

## 3. Manual end-to-end
```sh
beam doctor            # green/red checklist with plain-language fixes
beam login             # masked API-key prompt
beam whoami
beam workspace         # remembered default, if one is already unambiguous
beam workspace list    # use only when the request needs another workspace
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
