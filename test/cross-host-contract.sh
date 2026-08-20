#!/bin/sh
# Assert that Codex, Claude Code, Cursor, and Agent Plugins expose one public Beam Run surface.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
ok() { printf '  ok   %s\n' "$1"; }

cd "$ROOT"

printf '\n=== universal host surface ===\n'
python3 - <<'PY' || exit 1
import json
from pathlib import Path

root = Path("beam")
files = {
    "agent-plugin": root / "plugin.json",
    "codex": root / ".codex-plugin" / "plugin.json",
    "claude": root / ".claude-plugin" / "plugin.json",
    "cursor": root / ".cursor-plugin" / "plugin.json",
}
manifests = {name: json.loads(path.read_text()) for name, path in files.items()}
for name, manifest in manifests.items():
    if manifest["name"] != "beam":
        raise SystemExit(f"FAIL: {name} manifest is not Beam")
    if not manifest["version"].startswith("0.6.0"):
        raise SystemExit(f"FAIL: {name} manifest is not on the universal runtime version")

if manifests["agent-plugin"].get("skills") != "./skills":
    raise SystemExit("FAIL: generic Agent Plugin does not expose shared skills")
if manifests["codex"].get("skills") != "./skills/":
    raise SystemExit("FAIL: Codex does not expose shared skills")
if manifests["cursor"].get("skills") != ["./skills"]:
    raise SystemExit("FAIL: Cursor does not expose shared skills")
if "skills" in manifests["claude"]:
    raise SystemExit("FAIL: Claude should use its standard shared skills directory discovery")
print("  ok   every host resolves the shared public skills directory")
PY

public_skills="$(find beam/skills -mindepth 2 -maxdepth 2 -name SKILL.md | sort)"
expected="beam/skills/beam/SKILL.md
beam/skills/setup/SKILL.md"
[ "$public_skills" = "$expected" ] || fail "public skill discovery must contain only Beam Run and setup"
ok "only Beam Run and onboarding are host-discoverable"

grep -q 'Do \*\*not\*\* load the raw Copilot' beam/skills/beam/SKILL.md || fail "public skill still requests raw snapshot reads"
grep -q 'runtime/domains/<domain>.md' beam/skills/beam/SKILL.md || fail "public skill does not use focused policy cards"
grep -q 'one short, user-facing activity message' beam/skills/beam/SKILL.md || fail "public skill lacks shared activity UX"
grep -q 'never narrate each command' beam/skills/beam/SKILL.md || fail "public skill can expose per-command detail"
[ -d beam/internal/legacy-skills ] || fail "legacy specialist material was not preserved"
[ -d beam/internal/agent-builder ] || fail "builder implementation was not preserved"
ok "legacy implementation is retained without becoming host UI"

printf '\nCross-host contract checks PASSED.\n'
