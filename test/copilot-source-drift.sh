#!/bin/sh
# Compare the frozen prompt baseline with a Beam Copilot checkout.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COPILOT_ROOT="${BEAM_COPILOT_ROOT:-$ROOT/../VibeCoding/beam-dev/beam-agent-os}"
SOURCE="$COPILOT_ROOT/src/mastra/agents/copilot"
SNAPSHOT="$ROOT/beam/references/copilot-baseline"

if [ ! -d "$SOURCE" ]; then
  printf 'SKIP: Beam Copilot source checkout not found at %s\n' "$COPILOT_ROOT"
  exit 0
fi

compare() {
  src="$1"; dst="$2"
  cmp -s "$SOURCE/$src" "$SNAPSHOT/$dst" || {
    printf 'DRIFT: %s differs from %s\n' "$src" "$dst" >&2
    return 1
  }
  printf '  ok   %s\n' "$dst"
}

failed=0
compare 'supervisor/prompt.ts' 'supervisor/prompt.ts' || failed=1
compare '_shared/domain/routing-table.ts' 'domain/routing-table.ts' || failed=1
compare '_shared/domain/tool-catalog.ts' 'domain/tool-catalog.ts' || failed=1
compare '_shared/domain/tool-keys.ts' 'domain/tool-keys.ts' || failed=1
compare '_shared/domain/page-tool-subsets.ts' 'domain/page-tool-subsets.ts' || failed=1
compare 'sub-agents/general-agent/prompt.ts' 'general-agent/prompt.ts' || failed=1
compare 'sub-agents/builder/prompt.ts' 'builder/prompt.ts' || failed=1
compare 'sub-agents/pages/prompts.ts' 'pages/prompts.ts' || failed=1

[ "$failed" -eq 0 ] || exit 1
printf 'Copilot source and Beam Run snapshots match exactly.\n'
