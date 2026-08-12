---
name: setup
description: Beam setup — a guided, near-zero-prompt install. Run when the user wants to set up or connect Beam, when `beam` is not found, when `beam whoami`/`beam doctor` fails, or when Beam MCP tools error on auth or don't appear. You drive install + PATH + MCP registration; the user only approves, signs in once, and restarts once.
---

# Beam setup (guided)

Get the user from nothing to "talking to Beam" with the fewest prompts. **You drive.** The user does only three things: (1) gives clear approval to start, (2) enters their API key in their own terminal, (3) restarts once. Narrate each step in plain language with `✓` checkmarks — don't dump raw command output.

**Two rules that must hold:**
- **Never** ask the user to paste an API key into chat or pass it as `--api-key <key>`. They enter it in `beam login`'s masked terminal prompt.
- MCP reads the key only at **startup**, so a full restart is required. Don't skip it or claim success without it.

## Flow

### 1 · Offer (one approval)
> "I'll connect Beam to your agent — about a minute. I'll handle install, PATH, and wiring; you just sign in and restart once. Ready?"

Wait for clear natural-language approval.

### 2 · Run setup
```bash
beam setup
```
It installs `beam`, puts it on PATH (and your shell rc), and, in an interactive terminal, immediately opens the masked sign-in prompt. If the caller has no terminal (as in an agent or CI), it prints the secure next step instead. Once signed in, it registers the Beam MCP server. Branch on the exit code:
- **0** → installed, signed in, registered → go to step 4.
- **3** (non-interactive and not signed in) → do step 3, then re-run `beam setup`.
- **127 / `beam` not found** → resolve the launcher (see Fallbacks) and re-run with its absolute path.

### 3 · Sign in

> "Create a key at **app.beam.ai → Personal settings → API Keys**, then run `beam login` in your terminal and paste it when it asks (it stays hidden as you type). Tell me when it says you're signed in."

```bash
beam login
```

Wait for confirmation — do **not** take the key yourself. The command validates and stores the key, resolves an existing or unambiguous workspace when possible, and registers MCP. Then re-run `beam setup`; it verifies the connection.

`beam login` registers the MCP connection itself — including on the Claude desktop app,
which has no `claude` CLI. Only if it prints **"Could not auto-register"** do you relay the
manual fallback: add a remote HTTP server named `beam`, url `https://api.beamstudio.ai/mcp`,
header `Authorization: Bearer <their key>`.

Workspace choice happens in the coding-agent conversation, not the browser. Resolve it in this order:

1. Use an explicit workspace ID/name or Beam URL in the user's request.
2. Otherwise use a still-accessible default returned by `beam workspace`.
3. If the account has exactly one workspace, `beam login` remembers it automatically.
4. If multiple workspaces remain possible, ask the user once, then remember the answer with `beam workspace <id>`.

If an agent or resource is missing, do not search or switch silently. Name the current workspace and ask whether they want to switch:

```bash
beam workspace list <search>   # e.g. beam workspace list acme
beam workspace <id>
```

### 4 · Restart (the user's one action)
> "Last step — fully quit and reopen your agent so Beam loads."

A reload/soft-restart isn't enough.

### 5 · Confirm
After restart, call `listAgents` (or ask the user to say "list my Beam agents"). On success, tell them plainly what they can now do — list agents, run tasks, monitor progress, pull analytics — in plain English. No need to explain MCP vs CLI; the plumbing stays invisible.

## Presenting it — make it feel like onboarding
**Rule: `beam setup` already prints the onboarding message — a success line, an emoji checklist, and next steps. Show *that* to the user. Never rewrite it into a "what I did" table, a build/status report, or a summary of the steps you performed.** Report the user's remaining steps, not your own actions.

Render it as a warm chat message with **emoji** — never a raw diagnostic dump. Keep the **checklist** in plain text (not a code block): ✅ done, ⬜ pending, 🚀/🎉 to celebrate. But put any **runnable command** in a ```bash block so the app shows a one-click Run button, and make the key page a clickable link. Shape:

🚀 **Beam is installed — almost there!**
✅ Plugin installed
✅ beam on PATH
⬜ Sign in
⬜ Restart your agent

**Next steps:**
🔑 1. Create a key at [app.beam.ai → Personal settings → API Keys](https://app.beam.ai), then run:
```bash
beam login
```
🔄 2. Restart your agent, then ask "list my Beam agents"

When fully connected and a tool call has succeeded, **celebrate** — 🎉 — and name what they can now do (list agents, run tasks, monitor progress, pull analytics). Keep the plumbing (MCP/CLI/paths/headers) out of it.

## Fallbacks (only if needed)
- **`beam` not found** — resolve the bundled launcher, use its absolute path, then re-run:
  ```bash
  sh -c 'ls -1dt "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/plugins/cache/*/beam/*/bin/beam "${CODEX_HOME:-$HOME/.codex}"/plugins/cache/*/beam/*/bin/beam "$HOME"/.cursor/plugins/*/beam/bin/beam "$HOME"/.config/beam-plugin/beam/bin/beam 2>/dev/null | head -n1'
  ```
- **Cursor plugin never appears / org policy** — read `cursor-install.md` (same folder) and follow it.
- **Anything unclear** — `beam doctor` re-runs every check with a plain-language fix for each red.

## Notes
- API keys are global and do not select or scope a workspace. A later user choice is remembered locally as the default. CLI auth uses `x-api-key`; MCP uses `Authorization: Bearer`. `beam` handles both.
- A few Beam MCP tools are temporarily broken server-side (`getCurrentUser`, `getTaskDetails`, `getToolOutputSchema`, `getToolOptimizationStatus`) — see the `mcp` skill for CLI workarounds.
