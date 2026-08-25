#!/bin/sh
# Offline contract checks for the Copilot-aligned supervisor and fallbacks.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BEAM="$ROOT/beam/bin/beam"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
ok() { printf '  ok   %s\n' "$1"; }

cd "$ROOT"

printf '\n=== canonical Copilot baseline ===\n'
if command -v shasum >/dev/null 2>&1; then
  shasum -a 256 -c beam/references/copilot-baseline/SHA256SUMS >/dev/null || fail "Copilot snapshot drifted"
elif command -v sha256sum >/dev/null 2>&1; then
  sha256sum -c beam/references/copilot-baseline/SHA256SUMS >/dev/null || fail "Copilot snapshot drifted"
else
  fail "no SHA-256 checker available"
fi
ok "snapshot hashes match the recorded Beam Copilot source"
grep -q '40fdd5687a7a4e9122c27d8b175235107c096a58' beam/references/copilot-baseline/README.md || fail "source commit missing"
ok "source commit is recorded"

printf '\n=== universal supervisor runtime ===\n'
[ -s beam/skills/beam/SKILL.md ] || fail "missing universal Beam Run skill"
[ -s beam/skills/setup/SKILL.md ] || fail "missing setup skill"
grep -q 'only public runtime entry point' beam/skills/beam/SKILL.md || fail "Beam Run is not the only public runtime entry"
grep -q 'mapped CLI fallback' beam/skills/beam/SKILL.md || fail "completion fallback missing"
grep -q 'Do \*\*not\*\* load the raw Copilot' beam/skills/beam/SKILL.md || fail "runtime still depends on source snapshots"
grep -q 'For a read-only operation, say that no changes will be made' beam/skills/beam/SKILL.md || fail "read-only activity boundary missing"
grep -q 'name the exact entity and resulting state' beam/skills/beam/SKILL.md || fail "write-result activity contract missing"
[ -s beam/runtime/routes.md ] || fail "missing generated route index"
ok "universal supervisor and runtime gates are present"

printf '\n=== operation and fallback contracts ===\n'
grep -q 'surfaceOrder: \[mcp, cli\]' beam/contracts/operations.yaml || fail "MCP-first order missing"
if grep -q 'status: planned' beam/contracts/operations.yaml; then fail "operation registry still contains planned fallbacks"; fi
for module in tasks inbox integrations templates analytics views learning; do
  grep -q "beam $module" beam/contracts/operations.yaml || fail "no CLI mapping for $module"
done
ok "every registered operation has a ready fallback"

printf '\n=== CLI safety and discovery ===\n'
sh -n "$BEAM" || fail "CLI shell syntax"
help="$(sh "$BEAM" --help)"
for command in 'beam mcp check' 'beam workspace create' 'beam tasks create' 'beam inbox' 'beam integrations' 'beam templates' 'beam analytics' 'beam views' 'beam learning'; do
  printf '%s' "$help" | grep -q "$command" || fail "help missing $command"
done
ok "supervisor fallback surfaces are discoverable"

tmp="$(mktemp -d "${TMPDIR:-/tmp}/beam-supervisor-test.XXXXXX")"
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
if HOME="$tmp" BEAM_CONFIG_DIR="$tmp/config" sh "$BEAM" mcp check >/dev/null 2>&1; then rc=0; else rc=$?; fi
[ "$rc" -eq 3 ] || fail "signed-out MCP check should exit 3, got $rc"
if HOME="$tmp" BEAM_CONFIG_DIR="$tmp/config" sh "$BEAM" tasks delete task-1 >/dev/null 2>&1; then rc=0; else rc=$?; fi
[ "$rc" -eq 2 ] || fail "unconfirmed task deletion should exit 2, got $rc"
if HOME="$tmp" BEAM_CONFIG_DIR="$tmp/config" sh "$BEAM" learning optimize agent-1 issue-1 >/dev/null 2>&1; then rc=0; else rc=$?; fi
[ "$rc" -eq 2 ] || fail "unconfirmed optimization should exit 2, got $rc"
ok "auth and destructive confirmation gates are enforced"

printf '\n=== deterministic fallback requests ===\n'
mkdir -p "$tmp/bin" "$tmp/config"
printf 'BEAM_API_KEY=sk-test\nBEAM_WORKSPACE_ID=workspace-1\n' > "$tmp/config/credentials"
cat > "$tmp/bin/curl" <<'SH'
#!/bin/sh
body="$(sed -n '1,$p')"
out=""
url=""
api_key=false
bearer=false
while [ $# -gt 0 ]; do
  case "$1" in
    -o) out="${2:-}"; shift 2 ;;
    -H)
      case "${2:-}" in
        x-api-key:*) api_key=true ;;
        Authorization:\ Bearer\ *) bearer=true ;;
      esac
      shift 2 ;;
    *) url="$1"; shift ;;
  esac
done
if printf '%s' "$body" | grep -q '"method":"tools/list"'; then
  printf '%s\n' '{"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"task_create"},{"name":"beam_list_tasks"}]}}'
elif printf '%s' "$body" | grep -q '"method":"tools/call"'; then
  printf '%s\n' '{"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"ok"}]}}'
elif printf '%s' "$url" | grep -q '/auth/access-token'; then
  printf '%s' '{"idToken":"jwt-test"}' > "$out"
  printf '200'
elif [ "${BEAM_TEST_AUTH_MODE:-}" = "bearer-only" ] && [ "$api_key" = true ]; then
  printf '%s' '{"error":"api key rejected for this read"}' > "$out"
  printf '401'
elif printf '%s' "$url" | grep -q '/v2/user/me'; then
  printf '%s' '{"id":"user-1","email":"user@example.test","name":"Test User","workspaces":[{"id":"workspace-1","name":"Test Workspace"}],"memberships":[{"permissions":["large","raw","payload"]}]}' > "$out"
  printf '200'
elif printf '%s' "$url" | grep -q '/v2/workspace'; then
  [ -z "${BEAM_TEST_CAPTURE:-}" ] || printf '%s' "$body" > "$BEAM_TEST_CAPTURE"
  [ -z "${BEAM_TEST_CAPTURE_URL:-}" ] || printf '%s' "$url" > "$BEAM_TEST_CAPTURE_URL"
  printf '%s' '{"id":"workspace-new","name":"New Workspace","domain":"example.test","role":"owner","createdAt":"2026-08-25T00:00:00.000Z"}' > "$out"
  printf '201'
elif printf '%s' "$url" | grep -q '/agent/agent-1'; then
  printf '%s' '{"id":"agent-1","createdAt":"2026-01-02T03:04:05.000Z"}' > "$out"
  printf '200'
else
  [ -z "${BEAM_TEST_CAPTURE:-}" ] || printf '%s' "$body" > "$BEAM_TEST_CAPTURE"
  [ -z "${BEAM_TEST_CAPTURE_URL:-}" ] || printf '%s' "$url" > "$BEAM_TEST_CAPTURE_URL"
  printf '%s' '{"ok":true,"id":"result-1"}' > "$out"
  printf '200'
fi
SH
chmod +x "$tmp/bin/curl"

fallback_env="HOME=$tmp BEAM_CONFIG_DIR=$tmp/config PATH=$tmp/bin:$PATH BEAM_TEST_CAPTURE=$tmp/body"
# shellcheck disable=SC2086
mcp="$(env $fallback_env sh "$BEAM" mcp check --tool task_create)" || fail "healthy MCP tool check failed"
printf '%s' "$mcp" | grep -q '"available":true' || fail "MCP tool availability missing"
if env $fallback_env sh "$BEAM" mcp check --tool absent_tool >/dev/null 2>&1; then rc=0; else rc=$?; fi
[ "$rc" -eq 2 ] || fail "missing MCP tool should select fallback with exit 2"
ok "MCP health distinguishes healthy, available, and missing-tool states"

env $fallback_env sh "$BEAM" tasks create agent-1 'do the work' >/dev/null || fail "live task fallback failed"
grep -q '"isDraftTask":false' "$tmp/body" || fail "live task fallback selected wrong graph mode"
env $fallback_env sh "$BEAM" tasks create agent-1 'test the work' --draft >/dev/null || fail "draft task fallback failed"
grep -q '"isDraftTask":true' "$tmp/body" || fail "draft task fallback selected wrong graph mode"
ok "task fallback preserves live versus draft mode"

workspace_create="$(env $fallback_env BEAM_TEST_CAPTURE_URL="$tmp/url" sh "$BEAM" workspace create 'New Workspace' --domain example.test --icon-src https://example.test/icon.png)" || fail "workspace create fallback failed"
printf '%s' "$workspace_create" | grep -q '"id":"workspace-new"' || fail "workspace creation response was not returned"
grep -q '/v2/workspace' "$tmp/url" || fail "workspace creation did not use the public route"
grep -q '"name":"New Workspace"' "$tmp/body" || fail "workspace creation omitted the name"
grep -q '"domain":"example.test"' "$tmp/body" || fail "workspace creation omitted the domain"
grep -q '"iconSrc":"https://example.test/icon.png"' "$tmp/body" || fail "workspace creation omitted the icon URL"
if env $fallback_env sh "$BEAM" workspace create '1234567890123456789012345678901' >/dev/null 2>&1; then rc=0; else rc=$?; fi
[ "$rc" -eq 2 ] || fail "overlong workspace names should exit 2"
ok "workspace creation uses the published account-scoped API contract"

printf '{"name":"Support Runs","agentId":"agent-1"}\n' > "$tmp/view.json"
env $fallback_env sh "$BEAM" views create "$tmp/view.json" >/dev/null || fail "view create fallback failed"
grep -q '"name":"Support Runs"' "$tmp/body" || fail "view payload was not preserved"
ok "module writes use validated JSON payload files"

transport="$(env $fallback_env BEAM_TEST_AUTH_MODE=bearer-only BEAM_TRACE_TRANSPORT=1 sh "$BEAM" tasks statuses 2>&1)" || fail "Bearer fallback read failed"
printf '%s' "$transport" | grep -q '"auth":"bearer-fallback"' || fail "read fallback did not report bearer transport"
printf '%s' "$transport" | grep -q '"ok":true' || fail "read fallback did not return the endpoint response"
inbox_transport="$(env $fallback_env BEAM_TRACE_TRANSPORT=1 sh "$BEAM" inbox unread-count 2>&1)" || fail "direct bearer inbox read failed"
printf '%s' "$inbox_transport" | grep -q '"auth":"bearer-direct"' || fail "direct bearer read did not report its transport"
if env $fallback_env BEAM_TEST_AUTH_MODE=bearer-only sh "$BEAM" tasks create agent-1 'must not retry write' >/dev/null 2>&1; then rc=0; else rc=$?; fi
[ "$rc" -eq 3 ] || fail "writes must not retry with bearer transport"
ok "read-only bearer fallback is traced and writes remain single-attempt"

identity="$(env $fallback_env sh "$BEAM" whoami)" || fail "compact whoami failed"
printf '%s' "$identity" | grep -q '"workspaceCount":1' || fail "compact whoami omitted workspace count"
if printf '%s' "$identity" | grep -q 'memberships'; then fail "compact whoami leaked raw profile data"; fi
raw_identity="$(env $fallback_env sh "$BEAM" whoami --raw)" || fail "raw whoami failed"
printf '%s' "$raw_identity" | grep -q 'memberships' || fail "raw whoami did not preserve the full profile"
ok "whoami is compact by default and explicit about raw access"

env $fallback_env BEAM_TEST_CAPTURE_URL="$tmp/url" sh "$BEAM" analytics get agent-1 >/dev/null || fail "analytics fallback failed"
grep -q '/agent-tasks/analytics?agentId=agent-1&startDate=2026-01-02&endDate=' "$tmp/url" || fail "analytics fallback did not use the Copilot date range and public route"
ok "analytics fallback uses the Copilot date default and public route"

printf '\nSupervisor contract checks PASSED.\n'
