#!/bin/sh
# Verify the generated host-neutral policy cards used by every Beam Run host.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
ok() { printf '  ok   %s\n' "$1"; }

cd "$ROOT"

printf '\n=== universal runtime policy ===\n'
python3 beam/scripts/verify_runtime_policy.py || fail "runtime cards are stale or not reproducible"
ok "runtime cards are reproducible from the pinned baseline"

[ -s beam/runtime/common.md ] || fail "missing runtime common policy"
[ -s beam/runtime/routes.md ] || fail "missing runtime route index"
[ -s beam/runtime/manifest.json ] || fail "missing runtime manifest"

domains='general-workspace agent-builder agent-tasks global-tasks agent-flow integrations agent-config agent-analytics inbox templates views learning-hub'
for domain in $domains; do
  [ -s "beam/runtime/domains/$domain.md" ] || fail "missing domain card $domain"
  [ -s "beam/runtime/operations/$domain.md" ] || fail "missing operation card $domain"
  grep -q "Beam Run policy — $domain" "beam/runtime/domains/$domain.md" || fail "wrong domain card $domain"
done
ok "every Copilot domain has a focused policy and operation card"

grep -q 'graph.publish' beam/runtime/operations/agent-builder.md || fail "publish policy missing"
grep -q 'explicit-publish-intent' beam/runtime/operations/agent-builder.md || fail "publish confirmation missing"
grep -q 'task.create-live' beam/runtime/operations/agent-tasks.md || fail "live task policy missing"
grep -q 'task.approve' beam/runtime/operations/inbox.md || fail "task approval policy missing"
grep -q 'always' beam/runtime/operations/inbox.md || fail "task approval confirmation missing"
ok "high-risk task and publishing contracts are retained"

grep -q 'Group related platform calls under that line' beam/runtime/common.md || fail "common policy lacks grouped activity UX"
for domain in $domains; do
  grep -q 'Group related platform calls under that line' "beam/runtime/domains/$domain.md" || fail "domain card lacks grouped activity UX: $domain"
done
ok "every runtime policy card has the shared activity UX contract"

printf '\nRuntime policy contract checks PASSED.\n'
