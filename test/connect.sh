#!/bin/sh
# Browser Connect (beam login) against a fake Beam: real curl, real local listener,
# a simulated browser. Offline. See specs/browser-connect.md.
# shellcheck disable=SC2012,SC2015,SC2016
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BEAM="$ROOT/beam/bin/beam"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/beam-connect-test.XXXXXX")"
fake="$tmp/fake"
mkdir -p "$fake" "$tmp/bin" "$tmp/config"
REAL_CURL="$(command -v curl)"

python3 "$ROOT/test/fake_beam.py" "$fake" &
FAKE_PID=$!
trap 'kill "$FAKE_PID" 2>/dev/null || true; pkill -f "login_listener.py start $tmp" 2>/dev/null || true; rm -rf -- "$tmp"' EXIT HUP INT TERM

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  if [ -f "$tmp/out" ]; then cat "$tmp/out" "$tmp/err" >&2; fi
  exit 1
}
ok() { printf '  ok   %s\n' "$1"; }

n=0
while [ ! -s "$fake/port" ]; do
  n=$((n + 1)); [ "$n" -lt 100 ] || fail "fake Beam did not start"; sleep 0.1
done
PORT="$(cat "$fake/port")"

# curl that sends every Beam host to the fake; `open` records the link instead of opening a browser.
cat > "$tmp/bin/curl" <<SH
#!/bin/sh
[ -z "\${FAKE_OFFLINE:-}" ] || exit 7
n=\$#
while [ "\$n" -gt 0 ]; do
  a="\$1"; shift
  case "\$a" in
    https://*) a="http://127.0.0.1:$PORT/\${a#https://}" ;;
    http://localhost:*) a="http://127.0.0.1:$PORT/\${a#http://}" ;;
  esac
  set -- "\$@" "\$a"; n=\$((n - 1))
done
exec "$REAL_CURL" --noproxy '*' "\$@"
SH
printf '#!/bin/sh\nprintf "%%s\\n" "$1" >> "%s/opened"\n' "$tmp" > "$tmp/bin/open"
cp "$tmp/bin/open" "$tmp/bin/xdg-open"
chmod +x "$tmp/bin/curl" "$tmp/bin/open" "$tmp/bin/xdg-open"

SID=s1; CFG="$tmp/config"; KEY=""
run() { env HOME="$tmp" BEAM_CONFIG_DIR="$CFG" PATH="$tmp/bin:$PATH" BEAM_SESSION_ID="$SID" BEAM_API_KEY="$KEY" "$@"; }
# b <beam args>: sets rc, $tmp/out (stdout, the JSON) and $tmp/err; keeps everything in all.log for the secrets check.
b() {
  if run sh "$BEAM" "$@" > "$tmp/out" 2> "$tmp/err" < /dev/null; then rc=0; else rc=$?; fi
  cat "$tmp/out" "$tmp/err" >> "$tmp/all.log"
}
saw() { cat "$tmp/out" "$tmp/err" | grep -qF -- "$1"; }
jget() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get(sys.argv[2], ""))' "$tmp/out" "$1"; }
pend() { grep "^$2=" "$CFG/pending/$1" | cut -d= -f2-; }
prof() { grep "^$2=" "$CFG/instances/$1" | cut -d= -f2-; }
tofake() { printf '%s' "$1" | sed "s#^https://#http://127.0.0.1:$PORT/#; s#^http://localhost:#http://127.0.0.1:$PORT/localhost:#"; }
browse() { "$REAL_CURL" -sL --noproxy '*' -o /dev/null "$(tofake "$1")"; }
revoked() { grep -c -F -- "$1" "$fake/revoked" 2>/dev/null || true; }
reset_ws() { printf '{}' > "$fake/ws.json"; }
reset_ws
: > "$tmp/all.log"

APP="https://app.beam.ai/ws1/agents"

printf '\n=== an instance without Connect falls back to the key prompt ===\n'
printf 'app.us.beam.ai\n' > "$fake/old"
SID=sA
b login https://app.us.beam.ai/x
[ "$rc" -eq 3 ] && saw auth_missing || fail "not-upgraded instance without a key should ask for one (rc=$rc)"
if printf 'legacy-key\n1\n' | run env BEAM_TEST_INTERACTIVE=1 sh "$BEAM" login https://app.us.beam.ai/x > "$tmp/out" 2> "$tmp/err"; then :; else fail "key prompt login failed"; fi
[ -f "$CFG/instances/us" ] || fail "pasted-key profile was not saved"
[ "$(prof us BEAM_APP_URL)" = "https://app.us.beam.ai" ] || fail "profile lost its app address"
if grep -q '^BEAM_CONNECT=' "$CFG/instances/us"; then fail "pasted key was marked as a Connect key"; fi
b logout
saw '"revoked":false' || fail "logout deleted a key the user pasted"
[ ! -s "$fake/revoked" ] || fail "a pasted key was revoked"
: > "$fake/old"
ok "404 on the probe keeps today's flow; pasted keys are never deleted in Beam"

printf '\n=== connect: link, wait, connected ===\n'
SID=s1; b login "$APP"
[ "$rc" -eq 0 ] && [ "$(jget status)" = waiting ] && [ "$(jget mode)" = listener ] || fail "login did not return a waiting status"
url="$(jget connectUrl)"
case "$url" in "https://app.beam.ai/api/cli/authorize?code_challenge="*"&code_challenge_method=S256&redirect_uri=http%3A%2F%2F127.0.0.1%3A"*"%2Fcallback&state="*) ;; *) fail "unexpected connect link: $url" ;; esac
saw "Connect Beam: $url" || fail "human Connect line missing"
grep -qF "$url" "$tmp/opened" || fail "browser was not opened"
[ "$(wc -c < "$CFG/pending/app" | tr -d ' ')" -gt 0 ] && [ "$(ls -l "$CFG/pending/app" | cut -c1-10)" = "-rw-------" ] || fail "pending file is not private"
verifier="$(pend app VERIFIER)"
b login --wait
[ "$rc" -eq 0 ] && [ "$(jget status)" = waiting ] || fail "--wait before approval should say waiting"
browse "$url"
b login --wait
[ "$rc" -eq 0 ] && [ "$(jget status)" = connected ] && [ "$(jget workspaceId)" = "ws-api.beamstudio.ai" ] || fail "--wait did not connect ($(cat "$tmp/out"))"
saw '🔒 Locked for this session' || fail "connected login omitted the session checklist"
[ ! -e "$CFG/pending/app" ] || fail "pending file was not cleaned up"
key1="$(prof app BEAM_API_KEY)"
[ "$(prof app BEAM_APP_URL)" = "https://app.beam.ai" ] && [ "$(prof app BEAM_CONNECT)" = 1 ] || fail "profile lacks the app address or Connect mark"
case "$key1" in key-api.beamstudio.ai-*) ;; *) fail "profile did not get the issued key" ;; esac
b whoami
[ "$rc" -eq 0 ] || fail "the issued key does not work"
for secret in "$key1" "$verifier" "$(cat "$fake/lastcode")"; do
  if grep -qF -- "$secret" "$tmp/all.log"; then fail "a secret reached the output"; fi
done
ok "link printed, wait polls, key saved; key, verifier and code never printed"

printf '\n=== logout deletes the key in Beam ===\n'
b logout
saw '"revoked":true' && [ "$(revoked "$key1")" -eq 1 ] && [ ! -f "$CFG/instances/app" ] || fail "logout did not revoke and forget"
ok "logout revokes then forgets"

printf '\n=== wrong state is ignored; a refused sign-in fails cleanly ===\n'
b login "$APP"
port="$(pend app PORT)"
code="$("$REAL_CURL" -s --noproxy '*' -o /dev/null -w '%{http_code}' "http://127.0.0.1:$port/callback?code=evil&state=wrong")"
[ "$code" = 400 ] || fail "wrong state was accepted by the listener"
if grep -q '^CODE=' "$CFG/pending/app"; then fail "wrong state wrote a code"; fi
touch "$fake/deny"; browse "$(jget connectUrl)"; rm -f "$fake/deny"
b login --wait
[ "$rc" -eq 2 ] && [ "$(jget status)" = failed ] && [ "$(jget reason)" = access_denied ] && [ ! -e "$CFG/pending/app" ] || fail "refused sign-in did not report failed"
b login --wait
[ "$rc" -eq 2 ] && saw no_pending_login || fail "--wait with nothing pending should say so"
b login --callback 'http://127.0.0.1:1/callback?code=abc&state=nope'
[ "$rc" -eq 2 ] && [ "$(jget reason)" = state_mismatch ] || fail "--callback accepted a foreign state"
ok "state mismatch rejected; error and nothing-pending reported"

printf '\n=== no workspace yet / several workspaces ===\n'
printf '{"api.beamstudio.ai": []}' > "$fake/ws.json"
b login "$APP"; browse "$(jget connectUrl)"; b login --wait
[ "$(jget status)" = no_workspace ] && saw 'Create a workspace in Beam first: https://app.beam.ai' && [ -f "$CFG/instances/app" ] || fail "empty account was not handled"
b logout
printf '{"api.beamstudio.ai": [{"id":"w1","name":"Alpha"},{"id":"w2","name":"Beta"}]}' > "$fake/ws.json"
b login "$APP"; browse "$(jget connectUrl)"; b login --wait
[ "$(jget status)" = choose_workspace ] && [ "$(jget workspaceId)" = None ] && saw '"name": "Beta"' || fail "workspace list was not returned for the agent"
b checkout app Beta
[ "$rc" -eq 0 ] && saw '"workspaceId":"w2"' || fail "chosen workspace was not locked"
b logout; reset_ws
ok "no_workspace keeps the connection; several workspaces are returned and checkout locks one"

printf '\n=== paste-back: --paste and --callback ===\n'
b login "$APP" --paste
[ "$(jget mode)" = paste ] || fail "--paste did not skip the listener"
url="$(jget connectUrl)"
final="$("$REAL_CURL" -s --noproxy '*' -o /dev/null -w '%{redirect_url}' "$(tofake "$url")")"
case "$final" in "http://127.0.0.1:"*"/callback?code="*"&state="*) ;; *) fail "browser did not end on a loopback address: $final" ;; esac
b login --callback "$final"
[ "$rc" -eq 0 ] && [ "$(jget status)" = connected ] || fail "--callback did not connect"
key2="$(prof app BEAM_API_KEY)"
ok "a pasted final address completes the sign-in"

printf '\n=== reconnecting deletes the old key first ===\n'
b login "$APP"
[ "$rc" -eq 2 ] && saw instance_exists || fail "re-login without --replace should refuse"
b login "$APP" --replace
[ "$(revoked "$key2")" -eq 1 ] || fail "old key was not deleted when reconnecting"
browse "$(jget connectUrl)"; b login --wait
key3="$(prof app BEAM_API_KEY)"
[ "$(jget status)" = connected ] && [ "$key3" != "$key2" ] && [ "$(revoked "$key3")" -eq 0 ] || fail "reconnect did not issue a new key"
ok "--replace revokes the old key and keeps the new one"

printf '\n=== two instances stay connected side by side ===\n'
SID=s2; b login https://app.us.beam.ai/x --paste
final="$("$REAL_CURL" -s --noproxy '*' -o /dev/null -w '%{redirect_url}' "$(tofake "$(jget connectUrl)")")"
b login --callback "$final"
[ "$(jget status)" = connected ] && [ -f "$CFG/instances/app" ] && [ -f "$CFG/instances/us" ] || fail "second instance replaced the first"
[ "$(prof us BEAM_APP_URL)" = "https://app.us.beam.ai" ] && [ "$(prof app BEAM_APP_URL)" = "https://app.beam.ai" ] || fail "instances share an app address"
SID=s3; b checkout us; b logout
[ -f "$CFG/instances/app" ] && [ ! -f "$CFG/instances/us" ] && [ "$(revoked "$key3")" -eq 0 ] || fail "logging out one instance touched the other"
ok "each instance keeps its own key and app address"

printf '\n=== offline logout still forgets the key and says how to finish ===\n'
SID=s1; export FAKE_OFFLINE=1; b logout; unset FAKE_OFFLINE
[ ! -f "$CFG/instances/app" ] && saw "Delete the key named 'Beam Run · …' under API keys in Beam" && saw '"revoked":false' || fail "offline logout did not clean up with a hint"
ok "network failure on logout leaves a hint, not a stuck key"

printf '\n=== a sandbox that blocks the listener is reported once ===\n'
export BEAM_TEST_BIND_BLOCKED=1
b login https://app.eu.beam.ai/x
unset BEAM_TEST_BIND_BLOCKED
[ "$rc" -eq 2 ] && [ "$(jget status)" = sandbox_blocked ] && saw 'network access approved' && saw '--paste' || fail "blocked listener was not reported"
[ ! -e "$CFG/pending/eu" ] && [ ! -f "$CFG/instances/eu" ] || fail "blocked login left state behind"
ok "sandbox_blocked names the retry and the paste option"

printf '\n=== app address: as typed, or derived from an API address ===\n'
app_of() { b login "$@" --paste; jget connectUrl | sed 's#/api/cli/authorize.*##'; }
[ "$(app_of --api-url https://api.staging.beamstudio.ai)" = https://app.staging.beamstudio.ai ] || fail "staging API address"
[ "$(app_of https://app.staging.beamstudio.ai/x)" = https://app.staging.beamstudio.ai ] || fail "staging app address"
[ "$(app_of https://app.enterprise.beam.ai/x)" = https://app.enterprise.beam.ai ] || fail "enterprise app form was rewritten"
[ "$(app_of https://enterprise.beamstudio.ai/x)" = https://enterprise.beamstudio.ai ] || fail "enterprise studio form was rewritten"
[ "$(app_of --api-url https://api.enterprise.beamstudio.ai)" = https://enterprise.beamstudio.ai ] || fail "enterprise API address"
[ "$(app_of --api-url https://api.eu.beamstudio.ai)" = https://app.eu.beam.ai ] || fail "regional API address"
[ "$(app_of --api-url https://api.beamstudio.ai)" = https://app.beam.ai ] || fail "production API address"
b login --api-url https://api.acme.example.com
[ "$rc" -eq 3 ] && saw auth_missing || fail "custom API host without --app-url should use the key prompt"
[ "$(app_of --api-url https://api.acme.example.com --app-url https://studio.acme.example.com)" = https://studio.acme.example.com ] || fail "--app-url was ignored"
ok "staging, enterprise (both forms), regions, custom hosts"

printf '\n=== local development: typed address is the app, API on 4000 ===\n'
export BEAM_LOCAL_DEV=1
b login http://localhost:3000/x --paste
[ "$(jget connectUrl | sed 's#/api/cli/authorize.*##')" = http://localhost:3000 ] || fail "local app address"
final="$("$REAL_CURL" -s --noproxy '*' -o /dev/null -w '%{redirect_url}' "$(tofake "$(jget connectUrl)")")"
b login --callback "$final"
unset BEAM_LOCAL_DEV
[ "$(jget status)" = connected ] && [ "$(prof local BEAM_API_URL)" = http://localhost:4000 ] && [ "$(prof local BEAM_APP_URL)" = http://localhost:3000 ] || fail "local development connect"
ok "BEAM_LOCAL_DEV connects through localhost:3000 and localhost:4000"

printf '\n=== profiles saved before this change and the key options ===\n'
CFG="$tmp/old-config"; mkdir -p "$CFG/instances"
printf 'BEAM_INSTANCE_ID=us\nBEAM_INSTANCE_NAME=Beam US\nBEAM_API_URL=https://api.us.beamstudio.ai\nBEAM_MCP_URL=https://api.us.beamstudio.ai/mcp\nBEAM_API_KEY=legacy-key\n' > "$CFG/instances/us"
b login --replace --paste
[ "$(jget connectUrl | sed 's#/api/cli/authorize.*##')" = https://app.us.beam.ai ] || fail "old profile did not derive its app address"
[ "$(revoked legacy-key)" -eq 0 ] || fail "old profile's key was revoked"
CFG="$tmp/config2"; KEY=legacy-key
b login https://app.us.beam.ai/x --replace
[ "$rc" -eq 2 ] && saw instance_not_found || fail "unexpected replace result"
rm -rf "$CFG"; mkdir -p "$CFG"
b login https://app.us.beam.ai/x
[ "$rc" -eq 0 ] && [ "$(jget status)" = connected ] && ! grep -q '^BEAM_CONNECT=' "$CFG/instances/us" || fail "BEAM_API_KEY did not keep the key flow"
ok "old profiles derive the app address; BEAM_API_KEY still skips Connect"

printf '\nBrowser Connect checks PASSED.\n'
