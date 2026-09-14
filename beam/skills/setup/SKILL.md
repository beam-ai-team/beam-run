---
name: setup
description: Beam setup — a guided, near-zero-prompt install. Run when the user wants to set up or connect Beam, when `beam` is not found, when `beam whoami`/`beam doctor` fails, or when Beam MCP tools error on auth or don't appear. You drive install + PATH + MCP registration; the user only approves and signs in once.
---

# Beam setup (guided)

Get the user from nothing to "talking to Beam" with the fewest prompts. **You drive.** The user gives clear approval, enters their API key in their own terminal, and chooses a workspace only when their account has more than one. Narrate each step in plain language with `✓` checkmarks — don't dump raw command output.

**Two rules that must hold:**
- **Never** ask the user to paste an API key into chat or pass it as `--api-key <key>`. They enter it in `beam login`'s masked terminal prompt.

## Flow

### 1 · Offer (one approval)
> "I'll connect Beam to your agent — about a minute. I'll handle install, PATH, and wiring; you just sign in once. Ready?"

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

Wait for confirmation — do **not** take the key yourself. The command detects
whether the key belongs to Beam Cloud or Beam Enterprise, names the detected
instance, saves it locally, and registers the local Beam bridge. If that instance
already has a key, it changes nothing; use `beam login --replace` only when the
user intends to replace it. Then re-run `beam setup` to verify the connection.

`beam login` registers the MCP connection itself — including on the Claude desktop app,
which has no `claude` CLI. Only if it prints **"Could not auto-register"** do you relay the
manual local-command fallback printed by the CLI. Never put the key in host configuration.

Instance and workspace choice happen in the coding-agent conversation, not the browser:

1. If only one instance is saved, keep the existing low-friction behavior.
2. If multiple instances are saved, show `beam instance list`, ask once which
   instance and workspace this conversation should use, then run
   `beam checkout <instance> [workspace]`.
3. State the selected instance and workspace before work begins. After the first
   scoped operation, the checkout is locked; use a new conversation to work elsewhere.

Do not list every workspace automatically: accounts can have thousands. If the user asks to see them, use `beam workspace list <search>` to narrow by name or ID; the CLI shows a bounded set of matches.

If an agent or resource is missing, do not search or switch silently. Name the
current context and offer to continue in a new conversation:

```bash
beam instance list
beam checkout <instance> [workspace]
```

### 4 · Confirm
Once a workspace is selected, call `listAgents` (or ask the user to say "list my Beam agents"). On success, tell them plainly what they can now do — list agents, run tasks, monitor progress, pull analytics — in plain English. No need to explain MCP vs CLI; the plumbing stays invisible.

## Presenting it — make it feel like onboarding
**Rule: `beam setup` already prints the onboarding message — a success line, an emoji checklist, and next steps. Show *that* to the user. Never rewrite it into a "what I did" table, a build/status report, or a summary of the steps you performed.** Report the user's remaining steps, not your own actions.

Render it as a warm chat message with **emoji** — never a raw diagnostic dump. Keep the **checklist** in plain text (not a code block): ✅ done, ⬜ pending, 🚀/🎉 to celebrate. But put any **runnable command** in a ```bash block so the app shows a one-click Run button, and make the key page a clickable link. Shape:

🚀 **Beam is installed — almost there!**
✅ Plugin installed
✅ beam on PATH
⬜ Sign in

**Next steps:**
🔑 1. Create a key at [app.beam.ai → Personal settings → API Keys](https://app.beam.ai), then run:
```bash
beam login
```
🚀 2. If Beam selected a workspace automatically, ask "list my Beam agents." If you have multiple workspaces, choose one first — Beam can show a short, searchable list.

When fully connected and a tool call has succeeded, **celebrate** — 🎉 — and name what they can now do (list agents, run tasks, monitor progress, pull analytics). Keep the plumbing (MCP/CLI/paths/headers) out of it.

## Fallbacks (only if needed)
- **`beam` not found** — resolve the bundled launcher, use its absolute path, then re-run:
  ```bash
  sh -c 'ls -1dt "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/plugins/cache/*/beam/*/bin/beam "${CODEX_HOME:-$HOME/.codex}"/plugins/cache/*/beam/*/bin/beam "$HOME"/.cursor/plugins/*/beam/bin/beam "$HOME"/.config/beam-plugin/beam/bin/beam 2>/dev/null | head -n1'
  ```
- **Cursor plugin never appears / org policy** — read `cursor-install.md` (same folder) and follow it.
- **Anything unclear** — `beam doctor` re-runs every check with a plain-language fix for each red.

## Notes
- API keys are detected against Beam's supported Cloud and Enterprise origins
  and stored locally by instance. A conversation uses exactly one checked-out
  instance/workspace; the CLI and MCP bridge share that context.
- A few Beam MCP tools are temporarily broken server-side (`getCurrentUser`, `getTaskDetails`, `getToolOutputSchema`, `getToolOptimizationStatus`) — use the matching Beam Run CLI fallback after setup completes.
