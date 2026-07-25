#!/bin/sh
# Smoke test for the beam CLI — read-only (never creates tasks).
# Local:  BEAM_API_KEY='<key>' sh test/smoke.sh      (or run with no key for offline checks)
# CI:     provides BEAM_API_KEY via secrets; falls back to offline checks when absent.
set -eu

BEAM="${BEAM_BIN:-$(cd "$(dirname "$0")/.." && pwd)/beam/bin/beam}"
say() { printf '\n=== %s ===\n' "$1"; }
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

say "version"; "$BEAM" --version || fail "version"
say "help";    "$BEAM" --help >/dev/null || fail "help"
say "unknown-command exits 2"
set +e; "$BEAM" definitely-not-a-command >/dev/null 2>&1; rc=$?; set -e
[ "$rc" -eq 2 ] || fail "expected exit 2 for unknown command, got $rc"
echo "ok"

if [ -z "${BEAM_API_KEY:-}" ]; then
  say "doctor (no key — expect exit 3)"
  set +e; "$BEAM" doctor >/dev/null; dc=$?; set -e
  [ "$dc" -eq 3 ] || fail "expected doctor exit 3 with no key, got $dc"
  echo "ok (exit 3)"
  echo; echo "Offline smoke PASSED. Set BEAM_API_KEY to exercise the authenticated path."
  exit 0
fi

# Authenticated path — key comes from the environment, never argv.
say "login (env key)";      "$BEAM" login >/dev/null || fail "login"
say "doctor";               "$BEAM" doctor || fail "doctor"
say "whoami";               "$BEAM" whoami >/dev/null || fail "whoami"
say "workspace (best-effort)"
"$BEAM" workspace >/dev/null 2>&1 && echo "ok" || echo "no workspace auto-set (ok)"
say "agents list (best-effort)"
"$BEAM" agents list >/dev/null 2>&1 && echo "ok" || echo "agents list needs a workspace (ok)"

echo; echo "Authenticated smoke PASSED."
