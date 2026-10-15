#!/bin/sh
# Verify the Beam Run agent brief, its playbooks and the action list agree.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
ok() { printf '  ok   %s\n' "$1"; }

cd "$ROOT"

printf '\n=== agent and playbooks ===\n'
python3 beam/scripts/check_playbooks.py || fail "playbooks, brief and action list disagree"
python3 test/evals/test_scoring.py || fail "eval scoring or action dependencies regressed"
ok "every action is covered and every confirmation is a stop point"

[ ! -e beam/runtime ] || fail "generated screen cards are back; playbooks replace them"
grep -q '../../playbooks/' beam/skills/beam/SKILL.md || fail "brief does not point at the playbooks"
grep -q '../../contracts/operations.yaml' beam/skills/beam/SKILL.md || fail "brief does not point at the action list"
ok "the brief routes through playbooks and the action list"

printf '\n=== high-risk actions keep their confirmation ===\n'
op() { awk -v id="  $1:" '$0==id{f=1;next} /^  [a-z]/{f=0} f' beam/contracts/operations.yaml; }
op graph.publish | grep -q 'confirmation: explicit-publish-intent' || fail "publish confirmation missing"
op task.create-live | grep -q 'confirmation: required-if-production-side-effect' || fail "live task confirmation missing"
op task.approve | grep -q 'confirmation: always' || fail "consent approval confirmation missing"
op agent.delete | grep -q 'confirmation: explicit-agent-name-and-id' || fail "agent deletion confirmation missing"
op learning.approve-job | grep -q 'confirmation: always-two-turn' || fail "live prompt approval confirmation missing"
op graph.create-trigger | grep -q 'confirmation: explicit' || fail "trigger creation confirmation missing"
ok "publish, live runs, approvals, deletion, live prompt changes and triggers stop for the user"

printf '\nPlaybook contract checks PASSED.\n'
