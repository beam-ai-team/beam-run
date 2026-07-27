---
name: setup
description: Beam setup — a guided, near-zero-prompt install. Run when the user wants to set up or connect Beam, when `beam` is not found, when `beam whoami`/`beam doctor` fails, or when Beam MCP tools error on auth or don't appear. You drive install + PATH + MCP registration; the user only approves, signs in once, and restarts once.
---

# Beam setup (guided)

Get the user from nothing to "talking to Beam" with the fewest prompts. **You drive.** The user does only three things: (1) says yes to start, (2) signs in once, (3) restarts once. Narrate each step in plain language with `✓` checkmarks — don't dump raw command output.

**Two rules that must hold:**
- **Never** ask the user to paste their API key into the chat, and never pass it as `--api-key <key>`. They type it into `beam login`'s hidden prompt — it stays out of the chat and out of shell history.
- MCP reads the key only at **startup**, so a full restart is required. Don't skip it or claim success without it.

## Flow

### 1 · Offer (one yes/no)
> "I'll connect Beam to your agent — about a minute. I'll handle install, PATH, and wiring; you just sign in and restart once. Ready?"

Wait for yes.

### 2 · Run setup
```bash
beam setup
```
It installs `beam`, puts it on PATH (and your shell rc), and — if you're already signed in — registers the Beam MCP server and runs `beam doctor`. Branch on the exit code:
- **0** → installed, signed in, registered → go to step 4.
- **3** (not signed in) → do step 3, then re-run `beam setup`.
- **127 / `beam` not found** → resolve the launcher (see Fallbacks) and re-run with its absolute path.

### 3 · Sign in (the user's one data step)
> "Create a key at **app.beam.ai → Personal settings → API Keys**, then run `beam login` in your terminal and paste it when it asks (it stays hidden as you type). Tell me when it says you're signed in."

Wait for confirmation — do **not** take the key yourself. Then re-run `beam setup`; it now registers MCP and verifies.

If `beam setup` prints **"No 'claude' CLI found"** (e.g. the Claude desktop app), relay its one-time instruction: in the agent's MCP settings, add a remote HTTP server named `beam`, url `https://api.beamstudio.ai/mcp`, header `Authorization: Bearer <their key>`.

### 4 · Restart (the user's one action)
> "Last step — fully quit and reopen your agent so Beam loads."

A reload/soft-restart isn't enough.

### 5 · Confirm
After restart, call `listAgents` (or ask the user to say "list my Beam agents"). On success, tell them plainly what they can now do — list agents, run tasks, monitor progress, pull analytics — in plain English. No need to explain MCP vs CLI; the plumbing stays invisible.

## Presenting it — make it feel like onboarding
Render setup results as a warm chat message with **emoji** — **not** raw command output and **not inside a code block** (a fenced block of ASCII checkboxes is the thing to avoid). Use ✅ for done, ⬜ for pending, and 🚀 / 🎉 to celebrate. Don't paste `beam setup`'s terminal text verbatim — translate it into this shape:

🚀 **Beam is installed — almost there!**
✅ Plugin installed
✅ beam on PATH
⬜ Sign in
⬜ Restart your agent

**Next:**
1. `beam login` — create a key at app.beam.ai, paste it when it asks (it stays hidden as you type)
2. Restart your agent, then ask "list my Beam agents"

When fully connected and a tool call has succeeded, **celebrate** — 🎉 — and name what they can now do (list agents, run tasks, monitor progress, pull analytics). Keep the plumbing (MCP/CLI/paths/headers) out of it.

## Fallbacks (only if needed)
- **`beam` not found** — resolve the bundled launcher, use its absolute path, then re-run:
  ```bash
  sh -c 'ls -1dt "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/plugins/cache/*/beam/*/bin/beam "${CODEX_HOME:-$HOME/.codex}"/plugins/cache/*/beam/*/bin/beam "$HOME"/.cursor/plugins/*/beam/bin/beam "$HOME"/.config/beam-plugin/beam/bin/beam 2>/dev/null | head -n1'
  ```
- **Cursor plugin never appears / org policy** — read `cursor-install.md` (same folder) and follow it.
- **Anything unclear** — `beam doctor` re-runs every check with a plain-language fix for each red.

## Notes
- CLI auth = `x-api-key` (stored by `beam login`); the MCP endpoint uses `Authorization: Bearer`. `beam` handles both — you never set headers by hand.
- A few Beam MCP tools are temporarily broken server-side (`getCurrentUser`, `getTaskDetails`, `getToolOutputSchema`, `getToolOptimizationStatus`) — see the `mcp` skill for CLI workarounds.
