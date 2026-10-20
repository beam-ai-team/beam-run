#!/bin/sh
# No suite may touch a developer's real host configuration. Runs every offline suite with HOME
# pointing at a scratch directory that holds stand-ins for ~/.claude.json and ~/.cursor/mcp.json,
# then checks that nothing under it changed. (Pass/fail of the suites themselves is not judged here.)
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
scratch="$(mktemp -d "${TMPDIR:-/tmp}/beam-guard.XXXXXX")"
trap 'rm -rf -- "$scratch"' EXIT HUP INT TERM
mkdir -p "$scratch/.cursor" "$scratch/.claude"
printf '{"sentinel":true}\n' > "$scratch/.claude.json"
printf '{"mcpServers":{}}\n' > "$scratch/.cursor/mcp.json"
snapshot() { (cd "$scratch" && find . -type f -exec cksum {} + | sort); }
before="$(snapshot)"

for suite in smoke playbook-contract cross-host-contract activity-ux-contract supervisor-contract session-checkout e2e connect e2e-agent-builder; do
  printf '  running %s with a sentinel HOME\n' "$suite"
  env -u CLAUDE_CONFIG_DIR HOME="$scratch" sh "$ROOT/test/$suite.sh" > /dev/null 2>&1 < /dev/null || true
  if [ "$(snapshot)" != "$before" ]; then
    printf 'FAIL: test/%s.sh changed files under the sentinel HOME\n' "$suite" >&2
    exit 1
  fi
done
printf '  ok   no suite touched the host configuration\n\nNo-real-config guard PASSED.\n'
