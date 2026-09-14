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
    *) printf '%s' '{"error":"unauthorized"}' > "$out"; printf 401 ;;
  esac
else
  [ -z "${BEAM_CAPTURE_DIR:-}" ] || printf '%s\t%s\n' "$url" "$workspace" >> "$BEAM_CAPTURE_DIR/requests"
  printf '%s' '{"ok":true}' > "$out"; printf 200
fi
SH
chmod +x "$tmp/bin/curl"

run() {
  env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/config" PATH="$tmp/bin:$PATH" BEAM_CAPTURE_DIR="$tmp" "$@"
}

printf '\n=== detected instances and duplicate safety ===\n'
mkdir -p "$tmp/legacy-config"
printf 'BEAM_API_KEY=enterprise-key\nBEAM_WORKSPACE_ID=ent-a\n' > "$tmp/legacy-config/credentials"
if migrated="$(env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/legacy-config" PATH="$tmp/bin:$PATH" BEAM_API_KEY=enterprise-key sh "$BEAM" login 2>&1)"; then rc=0; else rc=$?; fi
if [ "$rc" -ne 2 ] || ! printf '%s' "$migrated" | grep -q instance_exists; then fail "legacy enterprise key was not detected during migration"; fi
[ -f "$tmp/legacy-config/instances/enterprise" ] && [ -f "$tmp/legacy-config/credentials.v1-backup" ] || fail "legacy credentials were not migrated safely"
run BEAM_SESSION_ID=login BEAM_API_KEY=prod-key sh "$BEAM" login >/dev/null 2>&1 || fail "production login"
[ -f "$tmp/config/instances/production" ] || fail "production profile was not saved"
if duplicate="$(run BEAM_SESSION_ID=login BEAM_API_KEY=prod-key sh "$BEAM" login 2>&1)"; then rc=0; else rc=$?; fi
if [ "$rc" -ne 2 ] || ! printf '%s' "$duplicate" | grep -q instance_exists; then fail "duplicate instance was not rejected safely"; fi
run BEAM_SESSION_ID=login BEAM_API_KEY=enterprise-key sh "$BEAM" login >/dev/null 2>&1 || fail "enterprise login"
[ -f "$tmp/config/instances/enterprise" ] || fail "enterprise profile was not saved"
ok "keys are detected, saved per instance, and duplicates fail safely"

printf '\n=== isolated session checkouts ===\n'
run BEAM_SESSION_ID=session-a sh "$BEAM" checkout enterprise >/dev/null 2>&1 || fail "enterprise checkout"
run BEAM_SESSION_ID=session-b sh "$BEAM" checkout production Alpha >/dev/null 2>&1 || fail "production checkout"
a="$(run BEAM_SESSION_ID=session-a sh "$BEAM" checkout)"
b="$(run BEAM_SESSION_ID=session-b sh "$BEAM" checkout)"
printf '%s' "$a" | grep -q '"instanceId":"enterprise"' || fail "session A lost enterprise"
printf '%s' "$b" | grep -q '"workspaceId":"prod-a"' || fail "session B lost production workspace"
if missing="$(run BEAM_SESSION_ID=session-c sh "$BEAM" agents list 2>&1)"; then rc=0; else rc=$?; fi
if [ "$rc" -ne 2 ] || ! printf '%s' "$missing" | grep -q checkout_required; then fail "new multi-instance session did not require checkout"; fi
ok "parallel sessions retain independent instance and workspace context"

printf '\n=== workspace can be completed after a scoped prompt ===\n'
mkdir -p "$tmp/single-config/instances"
cp "$tmp/config/instances/production" "$tmp/single-config/instances/production"
grep -v '^BEAM_WORKSPACE_' "$tmp/single-config/instances/production" > "$tmp/single-config/instances/production.tmp"
mv "$tmp/single-config/instances/production.tmp" "$tmp/single-config/instances/production"
if env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/single-config" BEAM_SESSION_ID=needs-workspace PATH="$tmp/bin:$PATH" sh "$BEAM" agents list >/dev/null 2>&1; then rc=0; else rc=$?; fi
[ "$rc" -eq 2 ] || fail "missing workspace should stop scoped work"
env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/single-config" BEAM_SESSION_ID=needs-workspace PATH="$tmp/bin:$PATH" sh "$BEAM" checkout production Alpha >/dev/null 2>&1 || fail "locked instance could not complete its workspace checkout"
completed="$(env HOME="$tmp" BEAM_CONFIG_DIR="$tmp/single-config" BEAM_SESSION_ID=needs-workspace PATH="$tmp/bin:$PATH" sh "$BEAM" checkout)"
printf '%s' "$completed" | grep -q '"workspaceId":"prod-a".*"locked":1' || fail "completed checkout did not retain its lock"
ok "a locked instance can fill its initially missing workspace"

printf '\n=== lock after scoped work ===\n'
run BEAM_SESSION_ID=session-a sh "$BEAM" agents list >/dev/null || fail "scoped enterprise read"
same="$(run BEAM_SESSION_ID=session-a sh "$BEAM" checkout enterprise)" || fail "idempotent checkout"
printf '%s' "$same" | grep -q '"locked":1' || fail "re-checking the same context unlocked the session"
if locked="$(run BEAM_SESSION_ID=session-a sh "$BEAM" checkout production Alpha 2>&1)"; then rc=0; else rc=$?; fi
if [ "$rc" -ne 2 ] || ! printf '%s' "$locked" | grep -q session_locked; then fail "used session was allowed to switch"; fi
grep -q 'api.enterprise.beamstudio.ai.*ent-a' "$tmp/requests" || fail "enterprise operation missed its workspace header"
ok "a used session cannot switch and requests carry its checked-out workspace"

printf '\n=== local bridge sees the same session ===\n'
status='{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"beam_session_status","arguments":{}}}'
bridge="$(printf '%s\n' "$status" | env BEAM_CONFIG_DIR="$tmp/config" BEAM_SESSION_ID=session-a BEAM_API_KEY= python3 "$PROXY")"
printf '%s' "$bridge" | grep -q 'Beam Enterprise.*Enterprise Demo.*locked' || fail "bridge context differs from CLI context"
ok "agent tools and CLI share the same visible, locked checkout"

printf '\nSession checkout checks PASSED.\n'
