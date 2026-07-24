---
name: setup
description: Beam setup — authenticate both the `beam` CLI and the Beam MCP server (both are required to use the plugin). Use when `beam` is not found on PATH, `beam whoami` fails, MCP tools error on auth or don't appear, the Cursor plugin never appears after a local install, or the user wants to configure Beam.
---

# Beam setup

**Two things must be authenticated to use this plugin:**

1. **The `beam` CLI** — whoami, workspace, agents list, scripting.
2. **The Beam MCP server** — in-editor tools (`listAgents`, `createAgentTask`, `getCurrentUser`, …).

Both authenticate the same way: a Beam **API key** (`x-api-key`). The CLI stores it under
`~/.config/beam/credentials` (or reads `BEAM_API_KEY`). `beam mcp` is a long-running stdio
proxy the agent's harness spawns once — it only reads the key at startup. So signing in is
not enough by itself: the agent (Claude Code / Codex / Cursor) must be **restarted** for an
already-running MCP server to see a key saved after it launched. `beam whoami` succeeding
does **not** by itself prove the MCP is authenticated.

## 1. Check current state

```bash
beam whoami; echo "exit_code=$?"
```

- **exit_code=0** → CLI authenticated. Also confirm MCP subcommand works:

  ```bash
  beam mcp --help >/dev/null 2>&1; echo "exit_code=$?"
  ```

  (`beam mcp` with no args starts the proxy — don't leave it running during setup checks.
  Prefer confirming the binary exists and `beam --help` lists `mcp`.)

  On Cursor, also check for dual registration (plugin **and** `~/.cursor/mcp.json`):

  ```bash
  grep -q '"beam"' "$HOME/.cursor/mcp.json" 2>/dev/null \
    && sh -c 'ls -d "$HOME"/.cursor/plugins/cache/*/beam/* "$HOME"/.cursor/plugins/local/beam 2>/dev/null' | grep -q . \
    && echo "dual registration"
  ```

  If that prints `dual registration`, remove the `beam` entry from `~/.cursor/mcp.json` and
  fully restart Cursor. Otherwise tell the user which workspace you're on and stop —
  unless the symptom was "Cursor plugin never appears," in which case still do step 2.

- **`beam: command not found`** (or exit 127) → CLI not on PATH.
  - **Claude Code**: if the plugin was just installed this session, resolve the bundled
    launcher and use its absolute path for the rest of this skill (Claude only adds plugin
    `bin/` to PATH on the *next* session):

    ```bash
    shim="$(sh -c 'ls -1dt "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/plugins/cache/*/beam/*/bin/beam 2>/dev/null | head -n1')"
    [ -x "$shim" ] || { echo "could not locate bundled beam launcher; reinstall the plugin"; exit 1; }
    "$shim" whoami; echo "exit_code=$?"
    ```

  - **Codex**: skip step 2 → step 3 → step 4 (Codex does not auto-PATH plugin bins).
  - **Cursor**: do step 2 first, then step 3, then step 4.

- **exit_code=3** (`auth_*`) → CLI present but not authenticated. Skip to step 4.
- **exit_code=5** (`network_*`) → connection problem. Check `BEAM_API_URL` / network; do not
  restart the sign-in flow.

## 2. Cursor only: resolve which install path applies

Skip on Claude Code and Codex.

On Cursor, Teams/Enterprise org policy can silently block copying into
`~/.cursor/plugins/local/beam`. Read `cursor-install.md` (same directory as this SKILL.md)
in full and follow it — then continue to step 3.

If `cursor-install.md` is missing or policy is unrestricted, the default path is:

```bash
git clone --depth 1 https://github.com/beam-ai-team/beam-run.git /tmp/beam-run
mkdir -p "$HOME/.cursor/plugins/local"
rm -rf "$HOME/.cursor/plugins/local/beam"
cp -R /tmp/beam-run/beam "$HOME/.cursor/plugins/local/beam"
chmod +x "$HOME/.cursor/plugins/local/beam/bin/beam"
```

Then fully quit and reopen Cursor (Cmd/Ctrl+Q — Reload Window is not enough for a new local plugin).

## 3. Put `beam` on PATH

Confirm a launcher exists:

```bash
sh -c 'ls -1dt \
  "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/plugins/cache/*/beam/*/bin/beam \
  "${CODEX_HOME:-$HOME/.codex}"/plugins/cache/*/beam/*/bin/beam \
  "$HOME"/.cursor/plugins/cache/*/beam/*/bin/beam \
  "$HOME"/.cursor/plugins/local/beam/bin/beam \
  "$HOME"/.config/beam-plugin/beam/bin/beam \
  2>/dev/null | head -n1'
```

If this prints nothing, **stop** — reinstall the plugin (Cursor: redo step 2).

If it printed a path, install a forwarder that resolves the newest launcher at runtime:

```bash
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/beam" <<'EOF'
#!/bin/sh
launcher="$(ls -1dt \
  "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/plugins/cache/*/beam/*/bin/beam \
  "${CODEX_HOME:-$HOME/.codex}"/plugins/cache/*/beam/*/bin/beam \
  "$HOME"/.cursor/plugins/cache/*/beam/*/bin/beam \
  "$HOME"/.cursor/plugins/local/beam/bin/beam \
  "$HOME"/.config/beam-plugin/beam/bin/beam \
  2>/dev/null | head -n1)"
[ -x "$launcher" ] || {
  printf '{"error":{"code":"internal_error","message":"no bundled beam launcher found — reinstall the Beam plugin"}}\n' >&2
  exit 127
}
exec "$launcher" "$@"
EOF
chmod +x "$HOME/.local/bin/beam"

case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *)
    echo "Add $HOME/.local/bin to PATH (e.g. in ~/.zshrc): export PATH=\"\$HOME/.local/bin:\$PATH\""
    export PATH="$HOME/.local/bin:$PATH"
    ;;
esac
```

Verify: `beam --help` should list `login`, `whoami`, `mcp`.

## 4. Authenticate

Create an API key in Beam if needed:

1. Open https://app.beam.ai
2. Workspace icon (top left) → **Personal settings** → **API Keys**
3. **Create New API Key** → copy it

Then:

```bash
beam login --api-key '<PASTE_KEY>'
# optional if whoami didn't auto-pick a workspace:
# beam workspace '<WORKSPACE_ID>'
beam whoami; echo "exit_code=$?"
```

Exit 0 → CLI is good. Tell the user which user/workspace you're on.

**Do not** print the API key back to the user or commit it.

### Register MCP when the plugin didn't

If the host didn't pick up the plugin's `mcp.json` / `.mcp.json`, register manually:

**Claude Code:**

```bash
claude mcp add --transport http beam-server https://api.beamstudio.ai/mcp --header "x-api-key: $(
  # shellcheck disable=SC1090
  . "$HOME/.config/beam/credentials"; printf '%s' "$BEAM_API_KEY"
)"
```

Prefer the plugin's stdio path (`beam mcp`) when the plugin is installed — HTTP add is the fallback.

**Cursor (Option A fallback — only if plugin install paths failed):** merge into `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "beam": {
      "command": "beam",
      "args": ["mcp"]
    }
  }
}
```

(`beam` must already be on PATH from step 3.)

## 5. Restart the agent (required)

MCP only reads the key at process start.

| Host | Restart |
| --- | --- |
| Claude Code | Fully exit the CLI/session and start a new one |
| Codex | Restart the Codex app / session so MCP respawns |
| Cursor | Settings → MCP: toggle Beam off/on, then **Reload Window**. If tools still fail auth, fully quit (Cmd/Ctrl+Q) and reopen |

After restart, verify MCP: ask the agent to call `getCurrentUser` or `listAgents`, or ask
"Can you list my Beam AI agents?"

Setup is complete only when **both** `beam whoami` and an MCP tool succeed.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| Plugin never appears in Cursor Settings → Plugins | Local sideload blocked by org policy | Use marketplace import or Option A MCP registration — see `cursor-install.md` |
| MCP auth error after `beam login` | Agent not restarted | Restart per table above |
| `beam whoami` exit 3 | Missing/invalid key | `beam login --api-key …` |
| `beam mcp` fails needing npx/uvx | No Node/uv | Install Node.js (npx) or uv (`uvx`) |
| Dual beam MCP entries in Cursor | Plugin + manual `mcp.json` | Remove the manual `beam` entry from `~/.cursor/mcp.json` |
| Tools missing but whoami works | MCP not connected / wrong workspace | Check MCP panel; set `beam workspace <id>`; restart |
