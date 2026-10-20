#!/bin/sh
# Verify the portable, user-facing activity contract without depending on host UI.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PATH="$ROOT/test/fixtures/stub-bin:$PATH"; export PATH; unset CLAUDE_CONFIG_DIR  # host CLIs are stubbed: a test never edits a real config
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
ok "agent brief has the complete user-facing activity contract"

if grep -l 'status line\|activity message' beam/playbooks/*.md >/dev/null 2>&1; then
  fail "a playbook redefines activity messages; the brief owns them"
fi
ok "playbooks inherit the brief's activity behavior without redefining it"

printf '\nActivity UX contract checks PASSED.\n'
