#!/bin/sh
# Verify the portable, user-facing activity contract without depending on host UI.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
ok() { printf '  ok   %s\n' "$1"; }

cd "$ROOT"

printf '\n=== portable activity UX ===\n'
skill="beam/skills/beam/SKILL.md"

grep -q 'one short, user-facing activity message' "$skill" || fail "logical-operation status rule missing"
grep -q 'For a read-only operation, say that no changes will be made' "$skill" || fail "read-only boundary missing"
grep -q 'For a write,' "$skill" || fail "external-effect boundary missing"
grep -q 'intended effect before starting' "$skill" || fail "external-effect intent missing"
grep -q 'exact entity and resulting state' "$skill" || fail "change-result reporting missing"
grep -q 'never narrate each command' "$skill" || fail "per-command narration suppression missing"
ok "public supervisor has the complete user-facing activity contract"

domains='general-workspace agent-builder agent-tasks global-tasks agent-flow integrations agent-config agent-analytics inbox templates views learning-hub'
for domain in $domains; do
  card="beam/runtime/domains/$domain.md"
  grep -q 'Group related platform calls under that line' "$card" || fail "grouping rule missing from $domain"
  grep -q 'For a read-only operation, say that no changes will be made' "$card" || fail "read-only rule missing from $domain"
  grep -q 'exact entity and resulting state' "$card" || fail "change result rule missing from $domain"
done
ok "every routed domain inherits the same activity behavior"

printf '\nActivity UX contract checks PASSED.\n'
