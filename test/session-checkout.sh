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
  [ -z "${BEAM_CAPTURE_DIR:-}" ] || printf '%s\t%s\n' "$url" "$workspace" >> "$BEAM_CAPTURE_DIR/requests"
  printf '%s' '{"ok":true}' > "$out"; printf 200
fi
SH
chmod +x "$tmp/bin/curl"

run() {
  env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/config" PATH="$tmp/bin:$PATH" BEAM_CAPTURE_DIR="$tmp" "$@"
}

printf '\n=== connection requires a workspace URL ===\n'
if missing_url="$(run BEAM_SESSION_ID=no-url BEAM_API_KEY=prod-key sh "$BEAM" login </dev/null 2>&1)"; then rc=0; else rc=$?; fi
if [ "$rc" -ne 3 ] || ! printf '%s' "$missing_url" | grep -q workspace_url_missing; then fail "login assumed an instance without a workspace URL"; fi
if root_url="$(run BEAM_SESSION_ID=root-url BEAM_WORKSPACE_URL=https://app.beam.ai BEAM_API_KEY=prod-key sh "$BEAM" login </dev/null 2>&1)"; then rc=0; else rc=$?; fi
if [ "$rc" -ne 2 ] || ! printf '%s' "$root_url" | grep -q workspace_url_invalid; then fail "login accepted an instance root instead of a workspace URL"; fi
ok "new connections never assume Beam App"

printf '\n=== detected instances and duplicate safety ===\n'
mkdir -p "$tmp/legacy-config"
printf 'BEAM_API_KEY=enterprise-key\nBEAM_WORKSPACE_ID=ent-a\n' > "$tmp/legacy-config/credentials"
if migrated="$(printf '1\n' | env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/legacy-config" PATH="$tmp/bin:$PATH" BEAM_TEST_INTERACTIVE=1 BEAM_SESSION_ID=legacy-enterprise BEAM_API_URL=https://api.enterprise.beamstudio.ai sh "$BEAM" checkout 2>&1)"; then rc=0; else rc=$?; fi
if [ "$rc" -ne 0 ] || ! printf '%s' "$migrated" | grep -q 'Checked out Beam Enterprise'; then fail "legacy enterprise connection did not migrate during checkout"; fi
[ -f "$tmp/legacy-config/instances/enterprise" ] && [ -f "$tmp/legacy-config/credentials.v1-backup" ] || fail "legacy credentials were not migrated safely"
run BEAM_SESSION_ID=login BEAM_WORKSPACE_URL=https://app.beam.ai/prod-a/agents BEAM_API_KEY=prod-key sh "$BEAM" login --workspace-id Alpha >/dev/null 2>&1 || fail "Beam App login"
[ -f "$tmp/config/instances/app" ] || fail "Beam App profile was not saved"
if duplicate="$(run BEAM_SESSION_ID=duplicate BEAM_WORKSPACE_URL=https://app.beam.ai/prod-a/agents BEAM_API_KEY=prod-key sh "$BEAM" login 2>&1)"; then rc=0; else rc=$?; fi
if [ "$rc" -ne 2 ] || ! printf '%s' "$duplicate" | grep -q instance_exists; then fail "duplicate instance was not rejected safely"; fi
run BEAM_SESSION_ID=another-login BEAM_WORKSPACE_URL=https://app.enterprise.beam.ai/ent-a/agents BEAM_API_KEY=enterprise-key sh "$BEAM" login >/dev/null 2>&1 || fail "enterprise login"
[ -f "$tmp/config/instances/enterprise" ] || fail "enterprise profile was not saved"
run BEAM_SESSION_ID=region-login BEAM_WORKSPACE_URL=https://app.anz.beam.ai/anz-a/agents BEAM_API_KEY=anz-key sh "$BEAM" login >/dev/null 2>&1 || fail "regional login"
if [ ! -f "$tmp/config/instances/anz" ] || ! grep -q 'BEAM_INSTANCE_NAME=Beam ANZ' "$tmp/config/instances/anz"; then fail "regional profile was not derived dynamically"; fi
ok "workspace URLs resolve instances dynamically and duplicates fail safely"

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

printf '\n=== workspace can be completed after a scoped prompt ===\n'
mkdir -p "$tmp/single-config/instances"
cp "$tmp/config/instances/app" "$tmp/single-config/instances/app"
grep -v '^BEAM_WORKSPACE_' "$tmp/single-config/instances/app" > "$tmp/single-config/instances/app.tmp"
mv "$tmp/single-config/instances/app.tmp" "$tmp/single-config/instances/app"
if env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/single-config" BEAM_SESSION_ID=needs-workspace PATH="$tmp/bin:$PATH" sh "$BEAM" agents list >/dev/null 2>&1; then rc=0; else rc=$?; fi
[ "$rc" -eq 2 ] || fail "missing workspace should stop scoped work"
env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/single-config" BEAM_SESSION_ID=needs-workspace PATH="$tmp/bin:$PATH" sh "$BEAM" checkout app Alpha >/dev/null 2>&1 || fail "instance could not complete its workspace checkout"
completed="$(env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/single-config" BEAM_SESSION_ID=needs-workspace PATH="$tmp/bin:$PATH" sh "$BEAM" checkout)"
printf '%s' "$completed" | grep -q '"workspaceId":"prod-a".*"locked":1' || fail "completed checkout did not retain its lock"
ok "a locked instance can fill its initially missing workspace"

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
status='{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"beam_session_status","arguments":{}}}'
bridge="$(printf '%s\n' "$status" | env BEAM_CONFIG_DIR="$tmp/config" BEAM_SESSION_ID=session-a BEAM_API_KEY= python3 "$PROXY")"
printf '%s' "$bridge" | grep -q 'Beam Enterprise.*Enterprise Demo.*locked' || fail "bridge context differs from CLI context"
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

printf '\n=== existing credentials survive updates ===\n'
mkdir -p "$tmp/legacy-app"
printf 'BEAM_API_KEY=prod-key\nBEAM_WORKSPACE_ID=prod-a\n' > "$tmp/legacy-app/credentials"
env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/legacy-app" PATH="$tmp/bin:$PATH" sh "$BEAM" whoami >/dev/null || fail "legacy connection stopped working after update"
[ -f "$tmp/legacy-app/credentials" ] || fail "ordinary use removed legacy credentials"
legacy_app="$(printf '1\n' | env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/legacy-app" PATH="$tmp/bin:$PATH" BEAM_TEST_INTERACTIVE=1 BEAM_SESSION_ID=legacy-app sh "$BEAM" checkout 2>&1)" || fail "legacy Beam App checkout failed"
printf '%s' "$legacy_app" | grep -q 'Alpha (previously used)' || fail "legacy checkout did not show the previous workspace first"
if printf '%s' "$legacy_app" | grep -Eq 'Paste your Beam workspace URL|Add your Beam API key'; then fail "legacy checkout asked the user to reconnect"; fi
[ -f "$tmp/legacy-app/instances/app" ] && [ -f "$tmp/legacy-app/credentials.v1-backup" ] || fail "legacy credentials were not migrated safely"
mkdir -p "$tmp/legacy-failed"
printf 'BEAM_API_KEY=unknown-key\nBEAM_WORKSPACE_ID=old-workspace\n' > "$tmp/legacy-failed/credentials"
if env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/legacy-failed" PATH="$tmp/bin:$PATH" BEAM_WORKSPACE_URL=https://app.enterprise.beam.ai/old-workspace BEAM_API_KEY= sh "$BEAM" login </dev/null >/dev/null 2>&1; then rc=0; else rc=$?; fi
if [ "$rc" -ne 3 ] || [ ! -f "$tmp/legacy-failed/credentials" ] || [ -e "$tmp/legacy-failed/credentials.v1-backup" ]; then fail "failed migration changed legacy credentials"; fi
ok "existing users remain connected and migrate atomically"

printf '\nSession checkout checks PASSED.\n'
