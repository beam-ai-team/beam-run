#!/bin/sh
# Verify the Beam Run agent brief, its playbooks and the action list agree.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PATH="$ROOT/test/fixtures/stub-bin:$PATH"; export PATH; unset CLAUDE_CONFIG_DIR  # host CLIs are stubbed: a test never edits a real config
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

printf '\n=== setup skill: Connect wording ===\n'
setup=beam/skills/setup/SKILL.md
# Everything outside "## Fallbacks" is the Connect path: no key pasting, no mandatory restart.
connect_path="$(awk '/^## Fallbacks/{skip=1; next} /^## /{skip=0} !skip' "$setup")"
if printf '%s\n' "$connect_path" | grep -iE 'paste (an |your |the )?(api )?key|enter (the |your )?(api )?key|hidden prompt|masked' | grep -v '^- \*\*Never\*\*' | grep -q .; then
  fail "the setup skill tells the user to paste a key on the Connect path"
fi
if grep -ihE 'restart' "$setup" GETTING_STARTED.md TESTING.md | grep -iE 'afterward([^s]|$)|after (you )?(connect|sign|log)' | grep -viE 'no restart|not needed|not required|only' | grep -q .; then
  fail "a restart is described as required after connecting"
fi
for needle in 'beam login <instance>' 'beam login --wait <instanceId>' 'sandbox_blocked' 'no_workspace' 'choose_workspace' 'clickable link' 'beam login --callback'; do
  grep -qF "$needle" "$setup" || fail "the setup skill omits: $needle"
done
ok "the setup skill drives Connect, never asks for a key on that path, and needs no restart"

printf '\n=== test mode and connections against a fake Beam ===\n'
op testmode.start | grep -q 'confirmation: always' || fail "test mode start lost its confirmation"
op testmode.stop | grep -q 'confirmation: always' || fail "test mode stop lost its confirmation"
op connection.set | grep -q 'confirmation: always' || fail "connection set lost its confirmation"
tm="$(mktemp -d "${TMPDIR:-/tmp}/beam-test-mode.XXXXXX")"
mkdir -p "$tm/fake" "$tm/home"
python3 test/fake_beam.py "$tm/fake" &
TM_PID=$!
trap 'kill "$TM_PID" 2>/dev/null || true; rm -rf -- "$tm"' EXIT HUP INT TERM
n=0
while [ ! -s "$tm/fake/port" ]; do n=$((n + 1)); [ "$n" -lt 100 ] || fail "fake Beam did not start"; sleep 0.1; done
TM_URL="http://127.0.0.1:$(cat "$tm/fake/port")/api.test"
bt() {
  if env HOME="$tm/home" BEAM_CONFIG_DIR="$tm/home/config" BEAM_API_KEY=test-key BEAM_WORKSPACE_ID=ws-1 \
    BEAM_API_URL="$TM_URL" BEAM_LOCAL_DEV=1 sh beam/bin/beam "$@" > "$tm/out" 2> "$tm/err"; then rc=0; else rc=$?; fi
}
field() { python3 -c 'import json,sys
d=json.load(open(sys.argv[1]))
for k in sys.argv[2].split("."):
    d=d[int(k)] if isinstance(d,list) else d.get(k)
print(json.dumps(d) if isinstance(d,(dict,list)) or d is None else d)' "$tm/out" "$1"; }
row() { python3 -c 'import json,sys
rows=[r for r in json.load(open(sys.argv[1]))["rows"] if r["kind"]==sys.argv[2] and r["mode"]==sys.argv[3]]
print(json.dumps(rows[0][sys.argv[4]]) if rows else "none")' "$tm/out" "$1" "$2" "$3"; }
expect() { [ "$rc" -eq "$1" ] || { cat "$tm/out" "$tm/err" >&2; fail "$2 (exit $rc, wanted $1)"; }; }

bt test-mode status agent-1; expect 0 "status failed"
[ "$(field testMode.testMode)" = off ] || fail "status should report test mode off"
bt tasks test agent-1 --input hello; expect 7 "a test task without a session must exit test_mode_inactive"
[ "$(field code)" = test_mode_inactive ] && [ -n "$(field next)" ] || fail "inactive error lacks its code or next step"
ok "status and the inactive error carry a code, an exit status and a next step"

bt connections missing agent-1 --mode test; expect 10 "missing test connections must exit 10"
[ "$(field missingCount)" = 4 ] || fail "expected 4 missing test connections, got $(field missingCount)"
[ "$(row step_tool test testConnection)" = null ] || fail "a test connection was pre-filled from live"
[ "$(row step_tool test nextStep)" = '"beam connections set agent-1 --node n-draft-mail --mode test --connection conn-gmail-2"' ] || fail "step nextStep is not the exact set command"
[ "$(row llm_tool test nextStep)" = '"beam connections set agent-1 --node n-draft-llm --tool tool-slack --mode test --connection conn-slack-1"' ] || fail "LLM-step tool nextStep is wrong"
[ "$(row custom_api test nextStep)" = '"beam://integrations?provider=crm-api"' ] || fail "an integration without connections should link to Beam"
[ "$(row trigger test nextStep)" = '"beam test-mode start agent-1 --trigger-connection trig-1=conn-gmail-2"' ] || fail "trigger nextStep should start test mode with the override"
if grep -q must-not-leak "$tm/out"; then fail "connection credentials leaked into the report"; fi
bt connections summary agent-1; expect 0 "summary failed"
[ "$(row mcp_integration test testConnection)" = '"not settable yet (INT-11779)"' ] || fail "MCP test connection note missing"
[ "$(row mcp_integration test usesLiveInTest)" = true ] && [ "$(row mcp_integration test missing)" = false ] || fail "MCP rows must use live in test and not count as missing"
[ "$(row step_tool live missing)" = false ] || fail "a connected live step was reported missing"
ok "missing-connection rules: separate test connections, exact next steps, MCP noted not counted"

: > "$tm/fake/mints"
bt connections set agent-1 --node n-draft-mail --mode test --connection conn-gmail-2; expect 0 "setting a step test connection failed"
[ "$(wc -l < "$tm/fake/mints" | tr -d ' ')" = 1 ] || fail "one command minted more than one Bearer token"
python3 -c 'import json,sys
b=json.load(open(sys.argv[1]))["node"]["toolConfiguration"]
sys.exit(0 if b["integrationProviderId"]=="conn-gmail-1" and b["testIntegrationProviderId"]=="conn-gmail-2" and b["toolFunctionName"] else 1)' "$tm/fake/lastpatch" || fail "the update did not send the whole node with only the test field changed"
bt connections set agent-1 --node n-draft-llm --tool tool-slack --mode test --connection conn-slack-1; expect 0 "setting an LLM-step tool test connection failed"
python3 -c 'import json,sys
n=json.load(open(sys.argv[1]))["node"]; t=n["agentGraphNodeTools"][0]
sys.exit(0 if n.get("toolConfiguration") and t["integrationProviderId"]=="conn-slack-1" and t["testIntegrationProviderId"]=="conn-slack-1" else 1)' "$tm/fake/lastpatch" || fail "the LLM-step update dropped the node tool or its live connection"
bt connections summary agent-1; expect 0 "summary after the updates failed"
[ "$(row step_tool live liveConnection)" = '{"id": "conn-gmail-1", "name": "Support inbox"}' ] && [ "$(row step_tool test liveConnection)" = '{"id": "conn-gmail-1", "name": "Support inbox"}' ] && [ "$(row llm_tool test liveConnection)" = '{"id": "conn-slack-1", "name": "Ops Slack"}' ] || fail "a test-connection update changed a live connection"
bt connections set agent-1 --node n-draft-mail --mode test --connection conn-slack-1; expect 2 "a connection of another integration must be refused"
bt connections set agent-1 --node n-live-mail --mode test --connection conn-gmail-2; expect 2 "a live-graph node must be refused for a test connection"
bt connections set agent-1 --trigger trig-1 --mode live --connection conn-gmail-2; expect 2 "a live trigger connection must not be changed from the CLI"
ok "connections set reads the whole node, changes one field, re-reads it, and never wipes a live connection"

bt test-mode start agent-1 --max-runs 3 --trigger-connection trig-1=conn-gmail-2; expect 0 "test mode start failed"
[ "$(field testMode.runsRemaining)" = 3 ] || fail "start should report 3 runs remaining"
bt test-mode start agent-1; expect 6 "a second start must exit test_mode_active"
bt tasks test agent-1 --input first --input second; expect 0 "test tasks failed"
[ "$(field runsUsed)" = 2 ] && [ "$(field runsRemaining)" = 1 ] && [ "$(field tasks.1.id)" = task-2 ] || fail "test tasks did not report ids and runs"
python3 -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get("isTestTask") is True else 1)' "$tm/fake/lasttask" || fail "test tasks did not send isTestTask"
bt tasks test agent-1 --input a --input b; expect 2 "more inputs than runs left must be refused before starting"
bt tasks test agent-1 "plain draft"; expect 0 "the draft test form stopped working"
python3 -c 'import json,sys; b=json.load(open(sys.argv[1])); sys.exit(0 if b.get("isDraftTask") is True and "isTestTask" not in b else 1)' "$tm/fake/lasttask" || fail "the positional form is no longer a draft test"
ok "test mode start, runs used and remaining, and the draft-test form side by side"

bt connections set agent-1 --trigger trig-1 --mode test --connection conn-gmail-1; expect 2 "a trigger restart must ask for confirmation"
[ "$(field code)" = confirmation_required ] && grep -q 'runsUsed resets from 2 to 0' "$tm/out" || fail "the restart warning does not name the reset"
bt connections set agent-1 --trigger trig-1 --mode test --connection conn-gmail-1 --confirm-restart; expect 0 "the confirmed trigger restart failed"
[ "$(field testMode.runsUsed)" = 0 ] && [ "$(field triggerOverrides.0.integrationProviderId)" = conn-gmail-1 ] || fail "the restart did not apply the new trigger connection"
ok "a trigger's test connection restarts test mode only after the reset is confirmed"

printf '["one", {"query": "two"}, "three"]' > "$tm/inputs.json"
bt tasks test agent-1 --inputs-file "$tm/inputs.json"; expect 0 "inputs file failed"
[ "$(field runsRemaining)" = 0 ] && [ "$(field testMode)" = off ] || fail "the session should switch off when its runs are used"
bt tasks test agent-1 --input more; expect 8 "a used-up session must exit test_runs_exhausted"
bt test-mode stop agent-1; expect 7 "stopping a stopped session must exit test_mode_inactive"
bt test-mode start agent-1; expect 0 "restart after exhaustion failed"
touch "$tm/fake/race409"
bt tasks test agent-1 --input x; expect 8 "an API 409 must map to test_runs_exhausted, not a network error"
grep -q 'Test runs exhausted: 3 of 3 used' "$tm/out" && [ "$(field notStarted.0)" = x ] || fail "the API error body or the unstarted inputs were dropped"
rm -f "$tm/fake/race409"
bt test-mode stop agent-1; expect 0 "stop failed"
touch "$tm/fake/deny403"
bt test-mode start agent-1; expect 9 "a 403 must exit permission_denied"
rm -f "$tm/fake/deny403"
ok "API errors keep their message and map to test_mode_*, test_runs_exhausted and permission_denied"

kill "$TM_PID" 2>/dev/null || true

printf '\nPlaybook contract checks PASSED.\n'
