---
name: setup
description: Beam setup — a guided, near-zero-prompt install. Run when the user wants to set up or connect Beam, when `beam` is not found, when `beam whoami`/`beam doctor` fails, or when Beam MCP tools error on auth or don't appear. You drive install + PATH + MCP registration; the user only approves and signs in once.
---

# Beam setup (guided)

Get the user from nothing to "talking to Beam" with the fewest prompts. **You drive.** The user gives clear approval, shares any URL from their Beam workspace, approves a Connect link in their browser, then selects or creates a workspace. Narrate each step in plain language with `✓` checkmarks — don't dump raw command output.

Setup is a user-facing initialization flow, not a narration of agent mechanics.
Never add an explanation, file link, or citation for a setup question. Keep skill,
tool, and fallback mechanics out of the user-facing reply. Show one compact
checklist and one clear next action at a time.

**Two rules that must hold:**
- **Never** ask the user to paste an API key into chat or pass it as `--api-key <key>`. On Connect there is no key to handle at all.
- **No restart** is needed after connecting. Restart the agent only when the plugin itself was just installed and its tools or skills do not appear.

## Flow

### 1 · Offer (one approval)
> "I'll connect Beam to your agent — about a minute. I'll handle install, PATH, and wiring; you just sign in once. Ready?"

Wait for clear natural-language approval.

### 2 · Run setup
```bash
beam setup
```
It installs `beam`, puts it on PATH (and your shell rc), and, in an interactive terminal, immediately starts sign-in. If the caller has no terminal (as in an agent or CI), it prints the next step instead. Once signed in, it registers the Beam MCP server. Branch on the exit code:
- **0** → installed, signed in, registered → go to step 4.
- **3** (non-interactive and not signed in) → do step 3, then re-run `beam setup`.
- **127 / `beam` not found** → resolve the launcher (see Fallbacks) and re-run with its absolute path.

### 3 · Connect

> "Open Beam and copy any URL from your workspace, then paste it here. I'll send you a link to approve in your browser."

A workspace URL is not secret; it can go in the chat. Run:

```bash
beam login <workspace URL>
```

It returns at once with `"status":"waiting"` and a `connectUrl`. Show that link to the
user as a clickable link and ask them to approve it in their browser. Then run
`beam login --wait` every few seconds (each call returns within about two seconds) and
branch on `status`:

- `waiting` → keep polling. After about five minutes the link expires; run `beam login <workspace URL>` again.
- `connected` → go to step 4.
- `choose_workspace` → ask which workspace from `workspaces`, then run `beam checkout <instanceId> <workspace>`.
- `no_workspace` → the connection is kept. Tell the user to create a workspace in Beam first (the `message` has the link), then run `beam checkout <instanceId> <workspace>`.
- `failed` → say sign-in did not complete and offer to run `beam login <workspace URL>` again. For `api_keys_manage_required`, ask them to request API key access from a workspace admin.
- `sandbox_blocked` (command exit 2) → this environment blocks the local listener. Re-run the same `beam login <workspace URL>` with network access approved (escalated permissions). If that is not possible, run it with `--paste`, have the user approve the link, then paste the address the browser ends on (it may show "can't connect"; that is expected) and run `beam login --callback '<address>'`. Never loop.

To reconnect an instance run `beam login <workspace URL> --replace` (the old key is deleted in Beam first). `beam logout` disconnects the instance and deletes its key in Beam.

`beam login` registers the MCP connection itself, including on the Claude desktop app, which has no `claude` CLI. Only if it prints **"Could not auto-register"** do you relay the manual local-command fallback printed by the CLI. Never put the key in host configuration.

Instance and workspace choice happen per coding-agent conversation:

1. If only one instance is saved, use it and select a workspace.
2. If multiple instances are saved, let the user choose one or add another.
3. Let the user choose an existing workspace or create one in the selected instance.
4. State the selected instance and workspace before work begins. Checkout locks
   immediately; use a new conversation to work elsewhere.

Do not list every workspace automatically: accounts can have thousands. If the user asks to see them, use `beam workspace list <search>` to narrow by name or ID; the CLI shows a bounded set of matches.

If an agent or resource is missing, do not search or switch silently. Name the
current context and offer to continue in a new conversation:

```bash
beam instance list
beam checkout <instance> [workspace]
```

### 4 · Confirm
Once a workspace is selected, first send the exact four-line checklist printed by
Beam as its own user-facing message. This confirmation is mandatory and must not
be compressed, reworded, combined with agent results, or skipped:

```text
🚀 Beam session ready
✅ Instance: {instance name}
✅ Workspace: {workspace name}
🔒 Locked for this session
```

Then run `beam agents list` in Codex; on other hosts, call `listAgents` or use the
CLI. On success, tell them plainly what they can now do — list agents, run tasks,
monitor progress, pull analytics — in plain English. No need to explain the
transport; the plumbing stays invisible.

## Presenting it — make it feel like onboarding
**Rule: `beam setup` already prints the onboarding message — a success line, an emoji checklist, and next steps. Show *that* to the user. Never rewrite it into a "what I did" table, a build/status report, or a summary of the steps you performed.** Report the user's remaining steps, not your own actions.

Render it as a warm chat message with **emoji** — never a raw diagnostic dump. Keep the **checklist** in plain text (not a code block): ✅ done, ⬜ pending, 🚀/🎉 to celebrate. But put any **runnable command** in a ```bash block so the app shows a one-click Run button, and make the Connect link a clickable link. Shape:

🚀 **Beam is installed — almost there!**
✅ Plugin installed
✅ beam on PATH
⬜ Sign in

**Next steps:**
🔑 1. Copy a URL from your Beam workspace and run:
```bash
beam login <that URL>
```
🚀 2. Approve the link in your browser, select or create a workspace, then ask "list my Beam agents."

When fully connected and a tool call has succeeded, **celebrate** — 🎉 — and name what they can now do (list agents, run tasks, monitor progress, pull analytics). Keep the plumbing (MCP/CLI/paths/headers) out of it.

## Fallbacks (only if needed)
- **`beam` not found** — resolve the bundled launcher, use its absolute path, then re-run:
  ```bash
  sh -c 'ls -1dt "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/plugins/cache/*/beam/*/bin/beam "${CODEX_HOME:-$HOME/.codex}"/plugins/cache/*/beam/*/bin/beam "$HOME"/.cursor/plugins/*/beam/bin/beam "$HOME"/.config/beam-plugin/beam/bin/beam 2>/dev/null | head -n1'
  ```
- **Instance without Connect** — `beam login` answers `auth_missing`. Tell the user to run `beam login` in their own terminal and enter the key at its hidden prompt, then re-run `beam setup` to verify. Do not take the key yourself.
- **Cursor plugin never appears / org policy** — read `cursor-install.md` (same folder) and follow it.
- **Anything unclear** — `beam doctor` re-runs every check with a plain-language fix for each red.

## Notes
- A workspace URL routes the key to exactly one instance. Regional hosts use
  `app.{region}.beam.ai`, from which Beam Run derives
  `api.{region}.beamstudio.ai`; no static region registry is used. Each saved
  instance also stores its app address, where the Connect link opens. Connections
  are stored locally. Users upgrading from the old single-instance connection
  reconnect once. A conversation uses exactly one locked instance/workspace;
  hosts with conversation-scoped MCP processes share that context with the CLI.
- Codex Beam work stays on the CLI after checkout because that path is scoped to
  the current task. Do not mix it with the shared Beam MCP process.
- A few Beam MCP tools are temporarily broken server-side (`getCurrentUser`, `getTaskDetails`, `getToolOutputSchema`, `getToolOptimizationStatus`) — use the matching Beam Run CLI fallback after setup completes.
