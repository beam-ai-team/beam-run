#!/bin/sh
# Assert that Codex, Claude Code, Cursor, and Agent Plugins expose one public Beam Run surface.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PATH="$ROOT/test/fixtures/stub-bin:$PATH"; export PATH; unset CLAUDE_CONFIG_DIR  # host CLIs are stubbed: a test never edits a real config
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
    if manifest["version"].split("+")[0] != Path("beam/VERSION").read_text().strip():
        raise SystemExit(f"FAIL: {name} manifest does not match beam/VERSION")

if manifests["agent-plugin"].get("skills") != "./skills":
    raise SystemExit("FAIL: generic Agent Plugin does not expose shared skills")
if manifests["codex"].get("skills") != "./skills/":
    raise SystemExit("FAIL: Codex does not expose shared skills")
if manifests["cursor"].get("skills") != ["./skills"]:
    raise SystemExit("FAIL: Cursor does not expose shared skills")
if "skills" in manifests["claude"]:
    raise SystemExit("FAIL: Claude should use its standard shared skills directory discovery")
print("  ok   every host resolves the shared public skills directory")

portable_mcp = json.loads((root / "mcp.json").read_text())
if portable_mcp.get("$schema") != "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json":
    raise SystemExit("FAIL: portable MCP config has no supported schema")
server = portable_mcp.get("mcpServers", {}).get("beam", {})
if server.get("type") != "stdio" or server.get("command") != "./bin/beam" or server.get("args") != ["mcp"]:
    raise SystemExit("FAIL: portable MCP config does not launch the bundled Beam bridge")
print("  ok   portable MCP config loads the bundled local bridge")
PY

public_skills="$(find beam/skills -mindepth 2 -maxdepth 2 -name SKILL.md | sort)"
expected="beam/skills/beam/SKILL.md
beam/skills/setup/SKILL.md"
[ "$public_skills" = "$expected" ] || fail "public skill discovery must contain only Beam Run and setup"
ok "only Beam Run and onboarding are host-discoverable"

grep -q '../../playbooks/' beam/skills/beam/SKILL.md || fail "public skill does not route through playbooks"
grep -q 'one short, user-facing activity message' beam/skills/beam/SKILL.md || fail "public skill lacks shared activity UX"
grep -q 'never narrate each command' beam/skills/beam/SKILL.md || fail "public skill can expose per-command detail"
[ ! -e beam/internal/legacy-skills ] || fail "old specialist skills should be gone"
[ -f beam/internal/agent-builder/scripts/beam.py ] || fail "builder implementation was not preserved"
if find beam/playbooks -name SKILL.md | grep -q .; then fail "playbooks must not be host-discoverable skills"; fi
ok "playbooks and builder material stay out of host skill discovery"

printf '\nCross-host contract checks PASSED.\n'
