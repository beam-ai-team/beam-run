# Cursor plugin install: resolving which path applies

On Cursor, Teams/Enterprise org policy can silently block the naive "copy the plugin folder
into `~/.cursor/plugins/local/beam`" approach: the plugin never appears in Settings → Plugins
no matter how many times you restart, because the org disabled local sideloading. Detect the
actual policy before choosing a path.

## Read the signal

Cursor caches resolved org policy in SQLite. Prefer reading it over guessing:

```bash
case "$(uname -s)" in
  Darwin) cursor_appsup="$HOME/Library/Application Support/Cursor" ;;
  *)      cursor_appsup="$HOME/.config/Cursor" ;;
esac
statedb="$cursor_appsup/User/globalStorage/state.vscdb"

python3 - "$statedb" <<'PY'
import json, sqlite3, sys

path = sys.argv[1]
row = None
try:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    row = conn.execute(
        "SELECT value FROM ItemTable WHERE key LIKE '%adminSettings.cached%' "
        "ORDER BY length(value) DESC LIMIT 1"
    ).fetchone()
except sqlite3.Error:
    pass

if not row:
    print("no cached admin settings — not on a Cursor team, or Cursor hasn't run yet; "
          "prefer path 3 (local sideload), fall back to path 4 if it never appears")
    sys.exit(0)

try:
    cached = json.loads(row[0])
except ValueError:
    print("invalid cached admin settings; prefer path 3 then path 4")
    sys.exit(0)

if isinstance(cached, str):
    try:
        cached = json.loads(cached)
    except ValueError:
        pass
if not isinstance(cached, dict):
    print("cached admin settings weren't an object; prefer path 3 then path 4")
    sys.exit(0)

def allowed(flag):
    return cached.get(flag) is not False

local_ok = allowed("allowUserLocalPluginImports")
marketplace_ok = allowed("allowThirdPartyPluginImports")

if local_ok and marketplace_ok:
    print("path 3 (local sideload): allowed. path 1/2 (marketplace import): also allowed.")
elif local_ok:
    print("path 3 (local sideload): allowed. marketplace import: blocked.")
elif marketplace_ok:
    print("path 1/2 (marketplace import): allowed. local sideload: blocked.")
else:
    print("path 4 (direct mcp.json): use this — local sideload and marketplace imports blocked.")
PY
```

## Paths

### Path 1 — Team marketplace (admin)

Admin adds `beam-ai-team/beam-run` as a team marketplace, then users install **beam** from Settings → Plugins.

### Path 2 — Personal marketplace import

Settings → Plugins → Add Marketplace → Import from Repo → `beam-ai-team/beam-run`, then install **beam**.

### Path 3 — Local sideload (default for unrestricted users)

```bash
git clone --depth 1 https://github.com/beam-ai-team/beam-run.git /tmp/beam-run
mkdir -p "$HOME/.cursor/plugins/local"
rm -rf "$HOME/.cursor/plugins/local/beam"
cp -R /tmp/beam-run/beam "$HOME/.cursor/plugins/local/beam"
chmod +x "$HOME/.cursor/plugins/local/beam/bin/beam"
rm -rf /tmp/beam-run
```

Fully quit and reopen Cursor (Cmd/Ctrl+Q). Confirm **beam** appears under Settings → Plugins.

### Path 4 — Direct MCP registration (Option A)

When plugins are blocked entirely, register MCP only — skills won't auto-load, but tools will:

1. Install the PATH forwarder from the setup skill (step 3) after copying `beam/bin/beam` somewhere durable, e.g.:

```bash
mkdir -p "$HOME/.config/beam-plugin/beam/bin"
curl -fsSL https://raw.githubusercontent.com/beam-ai-team/beam-run/main/beam/bin/beam \
  -o "$HOME/.config/beam-plugin/beam/bin/beam"
chmod +x "$HOME/.config/beam-plugin/beam/bin/beam"
```

2. Merge into `~/.cursor/mcp.json`:

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

3. Run `beam login --api-key …`, then fully restart Cursor.

## Don't run two paths at once

If both a plugin install and a manual `~/.cursor/mcp.json` `beam` entry exist, remove the
manual entry so tools aren't duplicated.
