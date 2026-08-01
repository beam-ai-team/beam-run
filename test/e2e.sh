#!/bin/sh
# End-to-end activation tests: the paths a new user actually walks.
#
# Runs inside a throwaway HOME, so it never touches the developer's real
# ~/.claude.json, ~/.cursor/mcp.json or ~/.config/beam.
#
# Local:  sh test/e2e.sh                      (offline subset)
#         BEAM_API_KEY='<key>' sh test/e2e.sh (+ authenticated subset)
# CI:     same; the authenticated half is skipped when the secret is absent.
# Assertions are intentionally written as `cond && ok || bad` — `ok`/`bad` always
# succeed, so the else-branch caveat does not apply here.
# shellcheck disable=SC2015
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BEAM="${BEAM_BIN:-$ROOT/beam/bin/beam}"
PROXY="$ROOT/beam/bin/mcp_proxy.py"
FAKE="${TMPDIR:-/tmp}/beam-e2e-$$"
KEY="${BEAM_API_KEY:-}"

pass=0; fail=0
ok()    { pass=$((pass+1)); printf '  ok   %s\n' "$1"; }
bad()   { fail=$((fail+1)); printf '  FAIL %s\n' "$1"; }
group() { printf '\n=== %s ===\n' "$1"; }
# Always run beam against the throwaway HOME.
sandbox() { env HOME="$FAKE" BEAM_CONFIG_DIR="$FAKE/.config/beam" "$@"; }

cleanup() { rm -rf "$FAKE"; }
trap cleanup EXIT INT TERM

rm -rf "$FAKE"; mkdir -p "$FAKE"
printf '{\n  "numStartups": 7,\n  "mcpServers": {}\n}\n' > "$FAKE/.claude.json"

command -v python3 >/dev/null 2>&1 || { echo "python3 required for e2e"; exit 1; }

# --- 1. Fresh install: the host spawns the bridge BEFORE the user has logged in.
# This must serve a live session that explains itself, not die.
group "fresh install (no credentials)"
REQ='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"beam_setup_status","arguments":{}}}'
OUT="$(printf '%s\n' "$REQ" | env BEAM_API_KEY= python3 "$PROXY" 2>/dev/null)"
[ "$(printf '%s\n' "$OUT" | grep -c .)" -eq 3 ] && ok "3 replies, notification stays silent" || bad "wrong reply count"
printf '%s' "$OUT" | grep -q '"protocolVersion"'  && ok "initialize succeeds unauthenticated" || bad "no initialize result"
printf '%s' "$OUT" | grep -q 'beam_setup_status'  && ok "exposes the setup-status tool"       || bad "missing status tool"
printf '%s' "$OUT" | grep -q 'beam login'         && ok "names the next step"                 || bad "no next step"
printf '%s' "$OUT" | python3 -c 'import sys,json;[json.loads(l) for l in sys.stdin if l.strip()]' 2>/dev/null \
  && ok "all replies are valid JSON-RPC" || bad "emitted invalid JSON"

OUT2="$(printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}' \
  | sandbox BEAM_API_KEY= sh "$BEAM" mcp 2>&1)"
printf '%s' "$OUT2" | grep -q '"result"'    && ok "'beam mcp' serves a live session"   || bad "'beam mcp' died"
printf '%s' "$OUT2" | grep -q 'auth_missing' && bad "still exits with auth_missing"    || ok "no auth_missing death"

# --- 2. Registration must work with no `claude` CLI (Claude desktop app).
group "host registration (no claude CLI)"
REG="$(sandbox BEAM_API_KEY=sk-test-key sh "$BEAM" register 2>/dev/null)"
printf '%s' "$REG" | grep -q '"ok":true' && ok "register succeeds" || bad "register failed: $REG"
python3 - "$FAKE/.claude.json" <<'PY' && ok "valid http+Bearer entry, unrelated keys preserved" || bad "bad host config"
import json, sys
d = json.load(open(sys.argv[1]))
b = d["mcpServers"]["beam"]
assert b["type"] == "http", b
assert b["url"].endswith("/mcp"), b
assert b["headers"]["Authorization"].startswith("Bearer "), b
assert d["numStartups"] == 7, "clobbered unrelated config"
PY
[ -f "$FAKE/.claude.json.beam-backup" ] && ok "original config backed up" || bad "no backup"
[ "$(stat -f '%Lp' "$FAKE/.claude.json" 2>/dev/null || stat -c '%a' "$FAKE/.claude.json" 2>/dev/null)" = "600" ] \
  && ok "key-bearing config is chmod 600" || bad "wrong permissions"

# A malformed host config must never be clobbered.
printf 'not json at all' > "$FAKE/.claude.json"
sandbox BEAM_API_KEY=sk-test-key sh "$BEAM" register >/dev/null 2>&1
grep -q 'not json at all' "$FAKE/.claude.json" && ok "unparseable config left untouched" || bad "clobbered a bad config"
printf '{\n  "numStartups": 7,\n  "mcpServers": {}\n}\n' > "$FAKE/.claude.json"
sandbox BEAM_API_KEY=sk-test-key sh "$BEAM" register >/dev/null 2>&1

group "uninstall"
sandbox sh "$BEAM" uninstall >/dev/null 2>&1
python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));sys.exit(0 if "beam" not in d.get("mcpServers",{}) else 1)' \
  "$FAKE/.claude.json" && ok "removes the entry it created" || bad "entry left behind"

group "doctor catches an unregistered host"
printf '{"mcpServers":{}}\n' > "$FAKE/.claude.json"
DOC="$(sandbox BEAM_API_KEY="${KEY:-sk-test-key}" sh "$BEAM" doctor 2>&1)"
printf '%s' "$DOC" | grep -q 'not registered with any agent' && ok "flags missing registration" || bad "missed it"
printf '%s' "$DOC" | grep -q 'All good' && bad "false 'All good' while broken" || ok "no false 'All good'"

if [ -z "$KEY" ]; then
  printf '\n%s passed, %s failed (offline subset).\nSet BEAM_API_KEY to run the authenticated checks.\n' "$pass" "$fail"
  [ "$fail" -eq 0 ] || exit 1
  exit 0
fi

# --- 3. Authenticated: real endpoint, real account shape.
group "authenticated bridge"
OUT3="$(printf '%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | env BEAM_API_KEY="$KEY" python3 "$PROXY" 2>/dev/null)"
printf '%s' "$OUT3" | grep -q 'serverInfo' && ok "proxies initialize upstream" || bad "no serverInfo"
NT="$(printf '%s' "$OUT3" | python3 -c 'import sys,json
for l in sys.stdin:
    d=json.loads(l)
    if d.get("id")==2: print(len(d.get("result",{}).get("tools",[])))' 2>/dev/null)"
[ -n "$NT" ] && [ "$NT" -gt 5 ] && ok "tools/list returns $NT tools" || bad "tools/list failed"

group "auth failure is actionable"
# Beam replies HTTP 200 + isError:true with terse text; the bridge appends the fix.
OUT4="$(printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"getCurrentUser","arguments":{}}}' \
  | env BEAM_API_KEY=sk-definitely-invalid python3 "$PROXY" 2>/dev/null)"
printf '%s' "$OUT4" | grep -q '"isError": *true' && ok "flagged as an error"  || bad "not flagged"
printf '%s' "$OUT4" | grep -q 'beam login'       && ok "enriched with the fix" || bad "not actionable"
OUT4B="$(printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"getCurrentUser","arguments":{}}}' \
  | env BEAM_API_KEY="$KEY" python3 "$PROXY" 2>/dev/null)"
printf '%s' "$OUT4B" | grep -q 'beam login' && bad "enriched a non-auth reply" || ok "valid replies untouched"

group "workspace is never guessed"
LOGIN="$(sandbox BEAM_API_KEY="$KEY" sh "$BEAM" login 2>/dev/null)"
WSN="$(printf '%s' "$LOGIN" | python3 -c 'import sys,json;print(json.load(sys.stdin)["workspaceCount"])' 2>/dev/null)"
WSID="$(printf '%s' "$LOGIN" | python3 -c 'import sys,json;print(json.load(sys.stdin)["workspaceId"])' 2>/dev/null)"
if [ -n "$WSN" ] && [ "$WSN" -gt 1 ]; then
  [ "$WSID" = "None" ] && ok "left unset across $WSN workspaces" || bad "auto-picked $WSID"
  sandbox BEAM_API_KEY="$KEY" sh "$BEAM" login 2>&1 >/dev/null | grep -q 'pick one' \
    && ok "tells the user to pick one" || bad "no guidance"
else
  [ "$WSID" != "None" ] && ok "single workspace auto-set (unambiguous)" || bad "should auto-set when there is exactly one"
fi

group "workspace list is bounded"
WL="$(sandbox BEAM_API_KEY="$KEY" sh "$BEAM" workspace list 2>/dev/null | grep -c .)"
[ "$WL" -le 25 ] && ok "capped at $WL rows" || bad "dumped $WL rows"

printf '\n%s passed, %s failed.\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
