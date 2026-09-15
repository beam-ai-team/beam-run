#!/bin/sh
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BEAM="$ROOT/beam/bin/beam"
PROXY="$ROOT/beam/bin/mcp_proxy.py"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/beam-session-test.XXXXXX")"
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
mkdir -p "$tmp/bin" "$tmp/config"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
ok() { printf '  ok   %s\n' "$1"; }

cat > "$tmp/bin/curl" <<'SH'
#!/bin/sh
out=""; url=""; key=""; workspace=""
while [ $# -gt 0 ]; do
  case "$1" in
    -o) out="$2"; shift 2 ;;
    -H)
      case "$2" in
        x-api-key:*) key="${2#x-api-key: }" ;;
        current-workspace-id:*) workspace="${2#current-workspace-id: }" ;;
      esac
      shift 2 ;;
    http*) url="$1"; shift ;;
    *) shift ;;
  esac
done
if printf '%s' "$url" | grep -q '/v2/user/me'; then
  case "$url|$key" in
    https://api.beamstudio.ai/*\|prod-key)
      printf '%s' '{"id":"u","workspaces":[{"id":"prod-a","name":"Alpha"},{"id":"prod-b","name":"Beta"}]}' > "$out"; printf 200 ;;
    https://api.enterprise.beamstudio.ai/*\|enterprise-key)
      printf '%s' '{"id":"u","workspaces":[{"id":"ent-a","name":"Enterprise Demo"}]}' > "$out"; printf 200 ;;
    https://api.anz.beamstudio.ai/*\|anz-key)
      printf '%s' '{"id":"u","workspaces":[{"id":"anz-a","name":"ANZ Demo"}]}' > "$out"; printf 200 ;;
    https://api.us.beamstudio.ai/*\|us-key)
      printf '%s' '{"id":"u","workspaces":[{"id":"us-a","name":"US Demo"}]}' > "$out"; printf 200 ;;
    https://api.eu.beamstudio.ai/*\|eu-key)
      printf '%s' '{"id":"u","workspaces":[{"id":"eu-a","name":"EU Demo"}]}' > "$out"; printf 200 ;;
    *) printf '%s' '{"error":"unauthorized"}' > "$out"; printf 401 ;;
  esac
elif printf '%s' "$url" | grep -q '/v2/workspace'; then
  printf '%s' '{"id":"workspace-new","name":"Prospect Demo"}' > "$out"; printf 201
else
  [ -z "${BEAM_CAPTURE_DIR:-}" ] || printf '%s\t%s\t%s\n' "$url" "$workspace" "$key" >> "$BEAM_CAPTURE_DIR/requests"
  printf '%s' '{"ok":true}' > "$out"; printf 200
fi
SH
chmod +x "$tmp/bin/curl"

run() {
  env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/config" PATH="$tmp/bin:$PATH" BEAM_CAPTURE_DIR="$tmp" "$@"
}

status_call='{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"beam_session_status","arguments":{}}}'

printf '\n=== connection requires a workspace URL ===\n'
if missing_url="$(run BEAM_SESSION_ID=no-url BEAM_API_URL=https://api.enterprise.beamstudio.ai BEAM_API_KEY=prod-key sh "$BEAM" login </dev/null 2>&1)"; then rc=0; else rc=$?; fi
if [ "$rc" -ne 3 ] || ! printf '%s' "$missing_url" | grep -q workspace_url_missing; then fail "login assumed an instance without a workspace URL"; fi
if root_url="$(run BEAM_SESSION_ID=root-url BEAM_WORKSPACE_URL=https://app.beam.ai BEAM_API_KEY=prod-key sh "$BEAM" login </dev/null 2>&1)"; then rc=0; else rc=$?; fi
if [ "$rc" -ne 2 ] || ! printf '%s' "$root_url" | grep -q workspace_url_invalid; then fail "login accepted an instance root instead of a workspace URL"; fi
ok "new connections never assume Beam App"

printf '\n=== detected instances and duplicate safety ===\n'
run BEAM_SESSION_ID=login BEAM_WORKSPACE_URL=https://app.beam.ai/prod-a/agents BEAM_API_KEY=prod-key sh "$BEAM" login --workspace-id Alpha >/dev/null 2>&1 || fail "Beam App login"
[ -f "$tmp/config/instances/app" ] || fail "Beam App profile was not saved"
if duplicate="$(run BEAM_SESSION_ID=duplicate BEAM_WORKSPACE_URL=https://app.beam.ai/prod-a/agents BEAM_API_KEY=prod-key sh "$BEAM" login 2>&1)"; then rc=0; else rc=$?; fi
if [ "$rc" -ne 2 ] || ! printf '%s' "$duplicate" | grep -q instance_exists; then fail "duplicate instance was not rejected safely"; fi
run BEAM_SESSION_ID=another-login BEAM_WORKSPACE_URL=https://app.enterprise.beam.ai/ent-a/agents BEAM_API_KEY=enterprise-key sh "$BEAM" login >/dev/null 2>&1 || fail "enterprise login"
[ -f "$tmp/config/instances/enterprise" ] || fail "enterprise profile was not saved"
run BEAM_SESSION_ID=region-login BEAM_WORKSPACE_URL=https://app.anz.beam.ai/anz-a/agents BEAM_API_KEY=anz-key sh "$BEAM" login >/dev/null 2>&1 || fail "regional login"
if [ ! -f "$tmp/config/instances/anz" ] || ! grep -q 'BEAM_INSTANCE_NAME=Beam ANZ' "$tmp/config/instances/anz"; then fail "regional profile was not derived dynamically"; fi
ok "workspace URLs resolve instances dynamically and duplicates fail safely"

printf '\n=== structured session initialization ===\n'
mkdir -p "$tmp/empty-config"
new_user="$(printf '%s\n' "$status_call" | env BEAM_CONFIG_DIR="$tmp/empty-config" BEAM_SESSION_ID=new-user BEAM_API_KEY= python3 "$PROXY")"
printf '%s' "$new_user" | grep -q 'Beam session setup' || fail "new-user status omitted setup heading"
printf '%s' "$new_user" | grep -q 'Paste a Beam workspace URL' || fail "new-user status omitted URL step"
printf '%s' "$new_user" | grep -q 'Enter the API key in the hidden prompt' || fail "new-user status omitted secure key step"
printf '%s' "$new_user" | grep -q 'Select or create a workspace' || fail "new-user status omitted workspace step"
if printf '%s' "$new_user" | grep -q 'Ask the user\|Never ask\|skill\|policy card'; then fail "new-user response exposed agent instructions"; fi
setup_user="$(printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"beam_setup_status","arguments":{}}}' | env BEAM_CONFIG_DIR="$tmp/empty-config" BEAM_SESSION_ID=setup-user BEAM_API_KEY= python3 "$PROXY")"
printf '%s' "$setup_user" | grep -q 'Paste a Beam workspace URL' || fail "setup skill status omitted the first connection step"
if new_checkout="$(env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/empty-config" BEAM_SESSION_ID=new-checkout PATH="$tmp/bin:$PATH" sh "$BEAM" checkout 2>&1)"; then rc=0; else rc=$?; fi
[ "$rc" -eq 3 ] || fail "unconnected checkout should require login"
printf '%s' "$new_checkout" | grep -q 'Beam session setup' || fail "unconnected CLI omitted structured setup"

multiple_instances="$(printf '%s\n' "$status_call" | env BEAM_CONFIG_DIR="$tmp/config" BEAM_SESSION_ID=choose-instance BEAM_API_KEY= python3 "$PROXY")"
printf '%s' "$multiple_instances" | grep -q 'Connected instances' || fail "returning-user status omitted instance choice"
printf '%s' "$multiple_instances" | grep -q 'Beam App' || fail "returning-user status omitted Beam App"
printf '%s' "$multiple_instances" | grep -q 'Beam Enterprise' || fail "returning-user status omitted Beam Enterprise"
printf '%s' "$multiple_instances" | grep -q 'Add another' || fail "returning-user status omitted add-instance choice"
printf '%s' "$multiple_instances" | grep -q 'Which instance would you like to use?' || fail "returning-user response lacked a direct question"
if printf '%s' "$multiple_instances" | grep -q 'Ask the user\|Never ask\|skill\|policy card'; then fail "returning-user response exposed agent instructions"; fi
if instance_checkout="$(run BEAM_SESSION_ID=choose-instance-cli sh "$BEAM" checkout 2>&1)"; then rc=0; else rc=$?; fi
[ "$rc" -eq 2 ] || fail "multi-instance checkout should require a choice"
printf '%s' "$instance_checkout" | grep -q 'Connected instances' || fail "CLI omitted structured instance choice"
if printf '%s' "$instance_checkout" | grep -q 'prod-a\|ent-a'; then fail "CLI instance choice leaked workspace rows"; fi

mkdir -p "$tmp/previous-config/instances"
cp "$tmp/config/instances/app" "$tmp/previous-config/instances/app"
previous_status="$(printf '%s\n' "$status_call" | env BEAM_CONFIG_DIR="$tmp/previous-config" BEAM_SESSION_ID=previous-status BEAM_API_KEY= python3 "$PROXY")"
printf '%s' "$previous_status" | grep -q 'Previously used: Alpha' || fail "one-instance status did not suggest the previous workspace"
printf '%s' "$previous_status" | grep -q 'Use Alpha again, choose another workspace, or create a new one?' || fail "one-instance response lacked workspace options"
if printf '%s' "$previous_status" | grep -q 'Ask the user\|Never ask\|skill\|policy card'; then fail "previous-workspace response exposed agent instructions"; fi
if previous_checkout="$(env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/previous-config" BEAM_SESSION_ID=previous-checkout PATH="$tmp/bin:$PATH" sh "$BEAM" checkout app 2>&1)"; then rc=0; else rc=$?; fi
[ "$rc" -eq 2 ] || fail "workspace confirmation should be required"
printf '%s' "$previous_checkout" | grep -q 'Beam session setup' || fail "checkout fallback omitted structured setup"
printf '%s' "$previous_checkout" | grep -q 'Previously used: Alpha' || fail "checkout fallback omitted previous workspace"
if printf '%s' "$previous_checkout" | grep -q 'prod-b\|Beta'; then fail "checkout fallback dumped unrelated workspaces"; fi
ok "new, returning, and multi-instance sessions receive one structured setup flow"

printf '\n=== isolated session checkouts ===\n'
run BEAM_SESSION_ID=session-a sh "$BEAM" checkout enterprise >/dev/null 2>&1 || fail "enterprise checkout"
run BEAM_SESSION_ID=session-b sh "$BEAM" checkout app Alpha >/dev/null 2>&1 || fail "Beam App checkout"
a="$(run BEAM_SESSION_ID=session-a sh "$BEAM" checkout)"
b="$(run BEAM_SESSION_ID=session-b sh "$BEAM" checkout)"
printf '%s' "$a" | grep -q '"instanceId":"enterprise"' || fail "session A lost enterprise"
printf '%s' "$b" | grep -q '"workspaceId":"prod-a"' || fail "session B lost production workspace"
if missing="$(run BEAM_SESSION_ID=session-c sh "$BEAM" agents list 2>&1)"; then rc=0; else rc=$?; fi
if [ "$rc" -ne 2 ] || ! printf '%s' "$missing" | grep -q checkout_required; then fail "new multi-instance session did not require checkout"; fi
ok "parallel sessions retain independent instance and workspace context"

run BEAM_SESSION_ID=session-b BEAM_API_URL=https://api.enterprise.beamstudio.ai BEAM_MCP_URL=https://api.enterprise.beamstudio.ai/mcp BEAM_API_KEY=enterprise-key BEAM_WORKSPACE_ID=ent-a sh "$BEAM" agents list >/dev/null || fail "saved checkout ignored inherited overrides"
grep -q 'api.beamstudio.ai.*prod-a.*prod-key' "$tmp/requests" || fail "environment values overrode the saved checkout"
ok "saved checkout controls endpoint, key, and workspace"

printf '\n=== workspace can be completed after a scoped prompt ===\n'
mkdir -p "$tmp/single-config/instances"
cp "$tmp/config/instances/app" "$tmp/single-config/instances/app"
grep -v '^BEAM_WORKSPACE_' "$tmp/single-config/instances/app" > "$tmp/single-config/instances/app.tmp"
mv "$tmp/single-config/instances/app.tmp" "$tmp/single-config/instances/app"
env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/single-config" BEAM_SESSION_ID=read-only PATH="$tmp/bin:$PATH" sh "$BEAM" agent-builder --help >/dev/null 2>&1 || fail "read-only help failed"
[ ! -e "$tmp/single-config/sessions/read-only" ] || fail "read-only help created a session"
if env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/single-config" BEAM_SESSION_ID=needs-workspace PATH="$tmp/bin:$PATH" sh "$BEAM" agents list >/dev/null 2>&1; then rc=0; else rc=$?; fi
[ "$rc" -eq 2 ] || fail "missing workspace should stop scoped work"
recover_tools="$(printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | env BEAM_CONFIG_DIR="$tmp/single-config" BEAM_SESSION_ID=needs-workspace BEAM_API_KEY= python3 "$PROXY")"
printf '%s' "$recover_tools" | grep -q 'beam_checkout' || fail "locked instance without a workspace hid checkout"
env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/single-config" BEAM_SESSION_ID=needs-workspace PATH="$tmp/bin:$PATH" sh "$BEAM" checkout app Alpha >/dev/null 2>&1 || fail "instance could not complete its workspace checkout"
completed="$(env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/single-config" BEAM_SESSION_ID=needs-workspace PATH="$tmp/bin:$PATH" sh "$BEAM" checkout)"
printf '%s' "$completed" | grep -q '"workspaceId":"prod-a".*"locked":1' || fail "completed checkout did not retain its lock"
ok "a locked instance can fill its initially missing workspace"

mkdir -p "$tmp/workspace-command/instances"
cp "$tmp/config/instances/app" "$tmp/workspace-command/instances/app"
workspace_command="$(env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/workspace-command" BEAM_SESSION_ID=workspace-command PATH="$tmp/bin:$PATH" sh "$BEAM" workspace prod-a)" || fail "workspace compatibility command failed"
printf '%s' "$workspace_command" | grep -q '"locked":true' || fail "workspace compatibility command did not lock"
if env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/workspace-command" BEAM_SESSION_ID=workspace-command PATH="$tmp/bin:$PATH" sh "$BEAM" workspace prod-b >/dev/null 2>&1; then rc=0; else rc=$?; fi
[ "$rc" -eq 2 ] || fail "workspace compatibility command switched a locked session"
ok "workspace compatibility command uses the checkout lock"

fresh_tools='{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
fresh_bridge="$(printf '%s\n' "$fresh_tools" | env BEAM_CONFIG_DIR="$tmp/single-config" BEAM_SESSION_ID=mcp-new BEAM_API_KEY= python3 "$PROXY")"
printf '%s' "$fresh_bridge" | grep -q 'beam_checkout' || fail "a new MCP session inherited the profile's previous workspace"
ok "new MCP sessions require their own workspace checkout"

printf '\n=== lock after scoped work ===\n'
run BEAM_SESSION_ID=session-a sh "$BEAM" agents list >/dev/null || fail "scoped enterprise read"
same="$(run BEAM_SESSION_ID=session-a sh "$BEAM" checkout enterprise)" || fail "idempotent checkout"
printf '%s' "$same" | grep -q '"locked":1' || fail "re-checking the same context unlocked the session"
if locked="$(run BEAM_SESSION_ID=session-a sh "$BEAM" checkout app Alpha 2>&1)"; then rc=0; else rc=$?; fi
if [ "$rc" -ne 2 ] || ! printf '%s' "$locked" | grep -q session_locked; then fail "used session was allowed to switch"; fi
grep -q 'api.enterprise.beamstudio.ai.*ent-a' "$tmp/requests" || fail "enterprise operation missed its workspace header"
ok "a used session cannot switch and requests carry its checked-out workspace"

printf '\n=== local bridge sees the same session ===\n'
bridge="$(printf '%s\n' "$status_call" | env BEAM_CONFIG_DIR="$tmp/config" BEAM_SESSION_ID=session-a BEAM_API_KEY= python3 "$PROXY")"
printf '%s' "$bridge" | grep -q 'Beam Enterprise.*Enterprise Demo.*Locked' || fail "bridge context differs from CLI context"
if printf '%s' "$bridge" | grep -q 'Ask the user\|Never ask\|skill\|policy card'; then fail "ready response exposed agent instructions"; fi
saved_bridge="$(printf '%s\n' "$status_call" | env BEAM_CONFIG_DIR="$tmp/config" BEAM_SESSION_ID=session-b BEAM_API_URL=https://api.enterprise.beamstudio.ai BEAM_MCP_URL=https://api.enterprise.beamstudio.ai/mcp BEAM_API_KEY=enterprise-key BEAM_WORKSPACE_ID=ent-a python3 "$PROXY")"
printf '%s' "$saved_bridge" | grep -q 'Beam App.*Alpha.*Locked' || fail "bridge environment overrode its saved checkout"
ok "agent tools and CLI share the same visible, locked checkout"

printf '\n=== interactive workspace creation ===\n'
created="$(printf '2\nProspect Demo\n' | run BEAM_TEST_INTERACTIVE=1 BEAM_SESSION_ID=create-workspace sh "$BEAM" checkout enterprise 2>&1)" || fail "workspace creation during checkout failed"
printf '%s' "$created" | grep -q 'Create new workspace' || fail "workspace selector omitted create option"
printf '%s' "$created" | grep -q 'Created Prospect Demo' || fail "created workspace was not confirmed"
status="$(run BEAM_SESSION_ID=create-workspace sh "$BEAM" checkout)"
printf '%s' "$status" | grep -q 'workspace-new.*locked":1' || fail "created workspace was not selected and locked"
ok "workspace selection can create, select, and lock a new workspace"

printf '\n=== returning user can add an instance ===\n'
added="$(printf '4\nhttps://app.us.beam.ai/us-a/agents\nus-key\n1\n' | run BEAM_TEST_INTERACTIVE=1 BEAM_SESSION_ID=add-instance sh "$BEAM" checkout 2>&1)" || fail "add-new instance flow failed"
printf '%s' "$added" | grep -q 'Add new instance' || fail "instance selector omitted add option"
printf '%s' "$added" | grep -q 'Connected to Beam US' || fail "new regional instance was not named"
[ -f "$tmp/config/instances/us" ] || fail "new regional instance was not saved"
run BEAM_SESSION_ID=future-region BEAM_WORKSPACE_URL=https://app.eu.beam.ai/eu-a/agents BEAM_API_KEY=eu-key sh "$BEAM" login >/dev/null 2>&1 || fail "future regional login"
grep -q 'BEAM_INSTANCE_NAME=Beam EU' "$tmp/config/instances/eu" || fail "unlisted future region was not derived from its URL"
ok "returning users can add a new instance from checkout"

printf '\n=== old single-instance users reconnect once ===\n'
mkdir -p "$tmp/legacy-app"
printf 'BEAM_API_KEY=prod-key\nBEAM_WORKSPACE_ID=prod-a\n' > "$tmp/legacy-app/credentials"
if env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/legacy-app" PATH="$tmp/bin:$PATH" sh "$BEAM" whoami >/dev/null 2>&1; then rc=0; else rc=$?; fi
[ "$rc" -eq 3 ] || fail "old credentials were silently reused"
if legacy_setup="$(env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/legacy-app" PATH="$tmp/bin:$PATH" sh "$BEAM" setup </dev/null 2>&1)"; then rc=0; else rc=$?; fi
if [ "$rc" -ne 3 ] || ! printf '%s' "$legacy_setup" | grep -q 'Sign in'; then fail "upgrade did not request a fresh connection"; fi
env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/legacy-app" PATH="$tmp/bin:$PATH" BEAM_SESSION_ID=legacy-app BEAM_WORKSPACE_URL=https://app.beam.ai/prod-a/agents BEAM_API_KEY=prod-key sh "$BEAM" login >/dev/null 2>&1 || fail "legacy user could not reconnect normally"
[ -f "$tmp/legacy-app/instances/app" ] || fail "reconnected instance was not saved"
ok "old credentials are ignored and the normal connection flow succeeds"

printf '\nSession checkout checks PASSED.\n'
