#!/bin/sh
# End-to-end activation tests. Runs inside a throwaway HOME.
# Local: sh test/e2e.sh
# Authenticated: BEAM_API_KEY='<key>' sh test/e2e.sh
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BEAM="${BEAM_BIN:-$ROOT/beam/bin/beam}"
PROXY="$ROOT/beam/bin/mcp_proxy.py"
FAKE="${TMPDIR:-/tmp}/beam-e2e-$$"
KEY="${BEAM_API_KEY:-}"

pass=0; fail=0
ok() { pass=$((pass+1)); printf '  ok   %s\n' "$1"; }
bad() { fail=$((fail+1)); printf '  FAIL %s\n' "$1"; }
group() { printf '\n=== %s ===\n' "$1"; }
sandbox() { env HOME="$FAKE" BEAM_CONFIG_DIR="$FAKE/.config/beam" "$@"; }
cleanup() { rm -rf "$FAKE"; }
trap cleanup EXIT INT TERM

rm -rf "$FAKE"; mkdir -p "$FAKE"
printf '{\n  "numStartups": 7,\n  "mcpServers": {}\n}\n' > "$FAKE/.claude.json"
command -v python3 >/dev/null 2>&1 || { echo "python3 required for e2e"; exit 1; }

group "fresh install (no credentials)"
REQ='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"beam_setup_status","arguments":{}}}'
OUT="$(printf '%s\n' "$REQ" | env BEAM_API_KEY= python3 "$PROXY" 2>/dev/null)"
[ "$(printf '%s\n' "$OUT" | grep -c .)" -eq 3 ] && ok "3 replies, notification stays silent" || bad "wrong reply count"
printf '%s' "$OUT" | grep -q '"protocolVersion"' && ok "initialize succeeds unauthenticated" || bad "no initialize result"
printf '%s' "$OUT" | grep -q 'beam_setup_status' && ok "exposes setup-status tool" || bad "missing status tool"
printf '%s' "$OUT" | grep -q 'beam login' && ok "names the next step" || bad "no next step"
printf '%s' "$OUT" | python3 -c 'import sys,json;[json.loads(l) for l in sys.stdin if l.strip()]' 2>/dev/null && ok "all replies are valid JSON-RPC" || bad "emitted invalid JSON"

OUT2="$(printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}' | sandbox BEAM_API_KEY= sh "$BEAM" mcp 2>&1)"
printf '%s' "$OUT2" | grep -q '"result"' && ok "beam mcp serves a live session" || bad "beam mcp died"
printf '%s' "$OUT2" | grep -q 'auth_missing' && bad "MCP exited with auth_missing" || ok "no auth_missing death"

group "host registration (no claude CLI)"
REG="$(sandbox BEAM_API_KEY=sk-test-key sh "$BEAM" register 2>/dev/null)"
printf '%s' "$REG" | grep -q '"ok":true' && ok "register succeeds" || bad "register failed"
python3 - "$FAKE/.claude.json" <<'PY' && ok "valid HTTP Bearer entry, unrelated keys preserved" || bad "bad host config"
import json, sys
d = json.load(open(sys.argv[1]))
b = d["mcpServers"]["beam"]
assert b["type"] == "http"
assert b["url"].endswith("/mcp")
assert b["headers"]["Authorization"].startswith("Bearer ")
assert d["numStartups"] == 7
PY
[ -f "$FAKE/.claude.json.beam-backup" ] && ok "original config backed up" || bad "no backup"
[ "$(stat -f '%Lp' "$FAKE/.claude.json" 2>/dev/null || stat -c '%a' "$FAKE/.claude.json" 2>/dev/null)" = "600" ] && ok "key-bearing config is chmod 600" || bad "wrong permissions"

printf 'not json at all' > "$FAKE/.claude.json"
sandbox BEAM_API_KEY=sk-test-key sh "$BEAM" register >/dev/null 2>&1
grep -q 'not json at all' "$FAKE/.claude.json" && ok "unparseable config left untouched" || bad "clobbered a bad config"
printf '{\n  "numStartups": 7,\n  "mcpServers": {}\n}\n' > "$FAKE/.claude.json"
sandbox BEAM_API_KEY=sk-test-key sh "$BEAM" register >/dev/null 2>&1

group "uninstall"
sandbox sh "$BEAM" uninstall >/dev/null 2>&1
python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));sys.exit(0 if "beam" not in d.get("mcpServers",{}) else 1)' "$FAKE/.claude.json" && ok "removes the entry it created" || bad "entry left behind"

group "doctor catches an unregistered host"
printf '{"mcpServers":{}}\n' > "$FAKE/.claude.json"
DOC="$(sandbox BEAM_API_KEY="${KEY:-sk-test-key}" sh "$BEAM" doctor 2>&1)"
printf '%s' "$DOC" | grep -q 'not registered with any agent' && ok "flags missing registration" || bad "missed it"
printf '%s' "$DOC" | grep -q 'All good' && bad "false All good while broken" || ok "no false All good"

group "API-key login guidance"
if NO_KEY="$(sandbox BEAM_API_KEY= sh "$BEAM" login </dev/null 2>&1)"; then no_key_rc=0; else no_key_rc=$?; fi
[ "$no_key_rc" -eq 3 ] && printf '%s' "$NO_KEY" | grep -q 'BEAM_API_KEY' && ok "non-interactive login gives secure options" || bad "missing API-key login guidance"
printf '%s' "$(sh "$BEAM" --help)" | grep -q 'masked prompt' && ok "help documents masked API-key login" || bad "help still describes browser login"

group "draft test-task CLI"
printf '%s' "$(sh "$BEAM" --help)" | grep -q 'beam tasks test' && ok "help documents draft test tasks" || bad "missing draft test command"
printf '%s' "$(sh "$BEAM" --help)" | grep -q 'beam tasks get' && ok "help documents task inspection" || bad "missing task inspect command"
printf '%s' "$(sh "$BEAM" --help)" | grep -q 'beam tasks submit-input' && ok "help documents paused task input" || bad "missing task input command"
if sandbox BEAM_API_KEY= sh "$BEAM" tasks test test-agent >/dev/null 2>&1; then test_rc=0; else test_rc=$?; fi
[ "$test_rc" -eq 2 ] && ok "missing task input exits validation" || bad "missing task input should exit 2"
if sandbox BEAM_API_KEY= sh "$BEAM" tasks get >/dev/null 2>&1; then get_rc=0; else get_rc=$?; fi
[ "$get_rc" -eq 2 ] && ok "missing task ID exits validation" || bad "missing task ID should exit 2"
if sandbox BEAM_API_KEY= sh "$BEAM" tasks submit-input test-task test-node work_item >/dev/null 2>&1; then submit_rc=0; else submit_rc=$?; fi
[ "$submit_rc" -eq 2 ] && ok "tasks submit-input validates its arguments" || bad "tasks submit-input missing argument should exit 2"

if [ -z "$KEY" ]; then
  printf '\n%s passed, %s failed (offline subset).\nSet BEAM_API_KEY to run the authenticated checks.\n' "$pass" "$fail"
  [ "$fail" -eq 0 ] || exit 1
  exit 0
fi

group "authenticated bridge"
OUT3="$(printf '%s\n%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}' '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | env BEAM_API_KEY="$KEY" python3 "$PROXY" 2>/dev/null)"
printf '%s' "$OUT3" | grep -q 'serverInfo' && ok "proxies initialize upstream" || bad "no serverInfo"
NT="$(printf '%s' "$OUT3" | python3 -c 'import sys,json
for l in sys.stdin:
 d=json.loads(l)
 if d.get("id")==2: print(len(d.get("result",{}).get("tools",[])))' 2>/dev/null)"
[ -n "$NT" ] && [ "$NT" -gt 5 ] && ok "tools/list returns $NT tools" || bad "tools/list failed"

group "auth failure is actionable"
OUT4="$(printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"getCurrentUser","arguments":{}}}' | env BEAM_API_KEY=sk-definitely-invalid python3 "$PROXY" 2>/dev/null)"
printf '%s' "$OUT4" | grep -q '"isError": *true' && ok "flagged as an error" || bad "not flagged"
printf '%s' "$OUT4" | grep -q 'beam login' && ok "enriched with the fix" || bad "not actionable"

group "workspace is never guessed"
LOGIN="$(sandbox BEAM_API_KEY="$KEY" sh "$BEAM" login 2>/dev/null)"
WSN="$(printf '%s' "$LOGIN" | python3 -c 'import sys,json;print(json.load(sys.stdin)["workspaceCount"])' 2>/dev/null)"
WSID="$(printf '%s' "$LOGIN" | python3 -c 'import sys,json;print(json.load(sys.stdin)["workspaceId"])' 2>/dev/null)"
if [ -n "$WSN" ] && [ "$WSN" -gt 1 ]; then
  [ "$WSID" = "None" ] && ok "left unset across $WSN workspaces" || bad "auto-picked $WSID"
else
  [ "$WSID" != "None" ] && ok "single workspace auto-set" || bad "should auto-set when unambiguous"
fi

group "workspace list is bounded"
WL="$(sandbox BEAM_API_KEY="$KEY" sh "$BEAM" workspace list 2>/dev/null | grep -c .)"
[ "$WL" -le 25 ] && ok "capped at $WL rows" || bad "dumped $WL rows"

printf '\n%s passed, %s failed.\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
