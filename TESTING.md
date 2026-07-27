# Testing Beam Run locally (dev)

`v0.2.0` (branch `activation-v3`). API-key auth; OAuth is a future iteration.

## 1. Point your local install at this working copy
Your `~/.local/bin/beam` forwarder resolves the newest launcher under
`~/.config/beam-plugin/beam`, so install this build there:

```sh
cp -R beam "$HOME/.config/beam-plugin/beam"
chmod +x "$HOME/.config/beam-plugin/beam/bin/beam"
beam --version    # -> beam 0.2.0
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
- The committed `beam/.mcp.json` still uses the stdio bridge (safe default); flipping the shipped default to direct HTTP is pending per-host verification (see `specs/` in the Nexus project).
- Telemetry is a **local placeholder** (`~/.config/beam/events.log`), disabled with `BEAM_TELEMETRY=0`; no network sink yet (SPEC-00).
