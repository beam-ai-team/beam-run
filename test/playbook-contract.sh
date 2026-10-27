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
op connection.set | grep -q 'safety: external-effect' || fail "connection set must be graded external-effect"
op task.create-test | grep -q 'confirmation: always' || fail "test-mode runs must always ask first"
op task.create-test | grep -q 'safety: external-effect' || fail "test-mode runs must always ask first"
op task.replay-test | grep -q 'confirmation: always' || fail "replaying past tasks must always ask first and re-read the task"
op task.replay-test | grep -q 'safety: external-effect' || fail "replaying past tasks must always ask first and re-read the task"
op task.replay-test | grep -q 'postRead: task.get' || fail "replaying past tasks must always ask first and re-read the task"
python3 beam/bin/operation_manifest.py | python3 -c 'import json,sys
ops={o["id"]:o for o in json.load(sys.stdin)["operations"]}
kinds={a.get("field"):a.get("kind") for a in ops["testmode.start"]["execution"]["commands"][0]}
sys.exit(0 if kinds["triggerConnection"]==kinds["toolConnection"]=="repeated-value" else 1)' || fail "test mode start overrides must be repeated flags"
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
bt test-mode run agent-1 --input hello; expect 7 "a test task without a session must exit test_mode_inactive"
[ "$(field code)" = test_mode_inactive ] && [ -n "$(field next)" ] || fail "inactive error lacks its code or next step"
ok "status and the inactive error carry a code, an exit status and a next step"

posts() { if [ -f "$tm/fake/taskbodies" ]; then wc -l < "$tm/fake/taskbodies" | tr -d ' '; else echo 0; fi; }
bt test-mode replay agent-1 --task past-mail --task past-chat --task past-mail --task past-other --task past-noinput --task past-text --task past-array --task past-missing --dry-run
expect 0 "a dry-run replay must work with test mode off"
[ "$(posts)" = 0 ] || fail "a dry-run replay started a task"
python3 -c 'import json,sys
d=json.load(open(sys.argv[1]))
mail=json.dumps({"subject": "Invoice 42", "from": "billing@example.com", "beamAgentOSTaskID": "nested-id"})
want={"task": mail, "attachments": [{"name": "invoice.pdf", "type": "file", "key": "files/invoice.pdf"}],
      "additionalInfo": "", "customerQuery": {"beamTaskId": "nested-keep", "lang": "en"}}
rows={r["taskId"]: r["taskQuery"] for r in d["dataset"]}
assert d["dryRun"] is True and list(rows) == ["past-mail", "past-chat"], rows
assert rows["past-mail"] == want and list(rows["past-mail"]) == list(want), rows["past-mail"]
assert rows["past-mail"]["task"] == mail, "the nested mail string changed"
assert rows["past-chat"] == {"query": "Where is my order?"}, rows["past-chat"]
left={r["taskId"]: r["reason"] for r in d["leftOut"]}
assert left == {"past-other": "belongs to agent agent-2, not agent-1",
                "past-noinput": "has no stored input (originalTaskQuery)",
                "past-text": "its stored input (originalTaskQuery) is not a JSON object",
                "past-array": "its stored input (originalTaskQuery) is not a JSON object",
                "past-missing": "not found in this workspace"}, left' "$tm/out" || fail "dry-run dataset, key stripping or left-out reasons are wrong: $(cat "$tm/out")"
bt test-mode replay agent-1 --task past-mail; expect 7 "a replay without a session must exit test_mode_inactive"
[ "$(field code)" = test_mode_inactive ] && [ "$(posts)" = 0 ] || fail "a replay with test mode off reached the API"
bt test-mode replay agent-1 --task past-other --task past-noinput --dry-run; expect 0 "a dry run with every id left out should still report"
[ "$(field dataset)" = '[]' ] && [ "$(field nextStep)" = null ] || fail "a dry run with nothing to replay must say so"
ok "replay dry run: top-level task ids stripped, nested and other keys untouched, every skipped id listed with its reason"
bt test-mode replay agent-1 --task past-forbidden --task past-upper --task past-chat --dry-run
expect 0 "a dry run with a task the role cannot read must still report"
python3 -c 'import json,sys
d=json.load(open(sys.argv[1]))
assert [r["taskId"] for r in d["dataset"]] == ["past-upper", "past-chat"], d["dataset"]
assert d["leftOut"] == [{"taskId": "past-forbidden", "reason": "not accessible to your role"}], d["leftOut"]' "$tm/out" || fail "a 403 task must be left out and agent ids compared case-insensitively: $(cat "$tm/out")"
bt test-mode replay AGENT-1 --task past-chat --dry-run; expect 0 "a dry run with an upper-case agent id failed"
[ "$(field dataset.0.taskId)" = past-chat ] && [ "$(field leftOut)" = '[]' ] || fail "an upper-case agent id must match the task's agent: $(cat "$tm/out")"
ok "replay leaves out a task the role cannot read and matches agent ids case-insensitively"

bt connections missing agent-1 --mode test; expect 10 "missing test connections must exit 10"
[ "$(field missingCount)" = 5 ] || fail "expected 5 missing test connections, got $(field missingCount)"
[ "$(row step_tool test testConnection)" = null ] || fail "a test connection was pre-filled from live"
[ "$(row step_tool test nextStep)" = '"beam connections set agent-1 --node n-draft-mail --mode test --connection conn-gmail-3"' ] || fail "step nextStep is not the exact set command"
[ "$(row llm_tool test nextStep)" = '"beam connections set agent-1 --node n-draft-llm --tool tool-slack --mode test --connection conn-slack-2"' ] || fail "LLM-step tool nextStep suggested the live connection"
[ "$(row llm_tool test usesLiveInTest)" = true ] && [ "$(row llm_tool test reason)" = '"falls back to live until INT-11779"' ] && [ "$(row llm_tool test missing)" = true ] || fail "LLM-step tools must be missing and say they fall back to live"
python3 -c 'import json,sys
r=[r for r in json.load(open(sys.argv[1]))["rows"] if r["nodeId"]=="n-draft-sheet"][0]
sys.exit(0 if r["nextStep"]=="beam://integrations?provider=google-sheets" and r["candidates"][0]["isLive"] and r.get("note") else 1)' "$tm/out" || fail "a live-only integration must link to Beam instead of suggesting the live connection"
[ "$(row custom_api test nextStep)" = '"beam://integrations?provider=crm-api"' ] || fail "an integration without connections should link to Beam"
[ "$(row trigger test nextStep)" = '"beam test-mode start agent-1 --trigger-connection trig-1=conn-gmail-3"' ] || fail "trigger nextStep should start test mode with a non-live override"
if grep -q must-not-leak "$tm/out"; then fail "connection credentials leaked into the report"; fi
bt connections summary agent-1; expect 0 "summary failed"
[ "$(row mcp_integration test testConnection)" = '"not settable yet (INT-11779)"' ] || fail "MCP test connection note missing"
[ "$(row mcp_integration test usesLiveInTest)" = true ] && [ "$(row mcp_integration test missing)" = false ] || fail "MCP rows must use live in test and not count as missing"
[ "$(row step_tool live missing)" = false ] || fail "a connected live step was reported missing"
bt connections options agent-1 --node n-draft-mail; expect 0 "connections options failed"
[ "$(field mode)" = test ] && [ "$(field nextStep)" = "beam connections set agent-1 --node n-draft-mail --mode test --connection conn-gmail-3" ] || fail "connections options must default to test and suggest a non-live connection: $(cat "$tm/out")"
ok "missing-connection rules: separate test connections, exact next steps, MCP noted not counted"

: > "$tm/fake/mints"; : > "$tm/fake/connections"
params() { python3 -c 'import json,sys,urllib.request
g=json.load(urllib.request.urlopen(urllib.request.Request(sys.argv[1]+"/agent-graphs/agent-1?graphId="+sys.argv[2],headers={"x-api-key":"test-key"})))["graph"]
n=[n for n in g["nodes"] if n["id"]==sys.argv[3]][0]
tools=[n["toolConfiguration"]]+(n.get("agentGraphNodeTools") or [])
print(json.dumps([[t.get("inputParams"),t.get("outputParams")] for t in tools],sort_keys=True))' "$TM_URL" "$1" "$2"; }
mail_before="$(params g-draft n-draft-mail)"; llm_before="$(params g-draft n-draft-llm)"
bt connections set agent-1 --node n-draft-mail --mode test --connection conn-gmail-2; expect 0 "setting a step test connection failed"
[ "$(wc -l < "$tm/fake/mints" | tr -d ' ')" = 1 ] || fail "one command minted more than one Bearer token"
bt connections set agent-1 --node n-draft-llm --tool tool-slack --mode test --connection conn-slack-2; expect 0 "setting an LLM-step tool test connection failed"
[ "$(cat "$tm/fake/connections")" = '{"connectionId": "conn-gmail-2", "mode": "test"}
{"connectionId": "conn-slack-2", "mode": "test", "toolConfigurationId": "tool-slack"}' ] || fail "connections set sent more than the connection field: $(cat "$tm/fake/connections")"
[ "$(params g-draft n-draft-mail)" = "$mail_before" ] && [ "$(params g-draft n-draft-llm)" = "$llm_before" ] || fail "setting a connection changed input params or output examples"
bt connections summary agent-1; expect 0 "summary after the updates failed"
[ "$(row step_tool live liveConnection)" = '{"id": "conn-gmail-1", "name": "Support inbox"}' ] && [ "$(row step_tool test liveConnection)" = '{"id": "conn-gmail-1", "name": "Support inbox"}' ] && [ "$(row llm_tool test liveConnection)" = '{"id": "conn-slack-1", "name": "Ops Slack"}' ] || fail "a test-connection update changed a live connection"
[ "$(row step_tool test testConnection)" = '{"id": "conn-gmail-2", "name": "Test inbox"}' ] || fail "the step test connection was not saved"
bt connections set agent-1 --node n-draft-mail --mode test --connection conn-slack-1; expect 2 "a connection of another integration must be refused"
bt connections set agent-1 --node n-live-mail --mode test --connection conn-gmail-2; expect 2 "a live-graph node must be refused for a test connection"
bt connections set agent-1 --trigger trig-1 --mode live --connection conn-gmail-2; expect 2 "a live trigger connection must not be changed from the CLI"
: > "$tm/fake/connections"
bt connections set agent-1 --node n-live-mail --mode live --connection conn-gmail-2; expect 2 "a live connection change must ask for --confirm-live"
[ "$(field code)" = confirmation_required ] && [ ! -s "$tm/fake/connections" ] || fail "an unconfirmed live change reached the API"
bt connections set agent-1 --node n-live-mail --mode live --connection conn-gmail-2 --confirm-live; expect 0 "the confirmed live change failed"
[ "$(field after.integrationProviderId)" = conn-gmail-2 ] && [ "$(field draftUpdated)" = True ] && [ "$(field nextPublishReverts)" = False ] && [ "$(field draftNodeId)" = n-draft-mail ] || fail "the live change was not mirrored to the draft"
[ "$(wc -l < "$tm/fake/connections" | tr -d ' ')" = 2 ] && [ "$(sort -u "$tm/fake/connections")" = '{"connectionId": "conn-gmail-2", "mode": "live"}' ] || fail "the live change and its draft mirror must each send only the live connection"
bt connections set agent-1 --node n-live-mail --mode live --connection conn-gmail-1 --confirm-live; expect 0 "restoring the live connection failed"
ok "connections set sends only the connection field, re-reads it, and leaves params, output examples and live connections alone"

bt test-mode start agent-1 --max-runs 3 --trigger-connection trig-1=conn-gmail-2; expect 0 "test mode start failed"
[ "$(field testMode.runsRemaining)" = 3 ] || fail "start should report 3 runs remaining"
bt test-mode start agent-1; expect 6 "a second start must exit test_mode_active"
bt test-mode run agent-1 --input first --input second; expect 0 "test tasks failed"
[ "$(field runsUsed)" = 2 ] && [ "$(field runsRemaining)" = 1 ] && [ "$(field tasks.1.id)" = task-2 ] || fail "test tasks did not report ids and runs"
python3 -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get("isTestTask") is True else 1)' "$tm/fake/lasttask" || fail "test tasks did not send isTestTask"
bt test-mode run agent-1 --input a --input b; expect 2 "more inputs than runs left must be refused before starting"
before="$(posts)"
bt test-mode replay agent-1 --task past-mail --task past-chat --task past-other; expect 2 "more replay rows than runs left must be refused before starting"
[ "$(posts)" = "$before" ] && [ "$(field code)" = validation_error ] || fail "a replay over the runs left started a task"
grep -q '2 tasks to replay but only 1 of 3 test runs remain' "$tm/out" || fail "the replay refusal does not name the rows and runs left"
ok "test mode start, runs used and remaining"

bt connections set agent-1 --trigger trig-1 --mode test --connection conn-gmail-3; expect 2 "a trigger restart must ask for confirmation"
[ "$(field code)" = confirmation_required ] || fail "the restart warning does not name the reset"
grep -q 'runsUsed resets from 2 to 0' "$tm/out" || fail "the restart warning does not name the reset"
bt connections set agent-1 --trigger trig-1 --mode test --connection conn-gmail-3 --confirm-restart; expect 0 "the confirmed trigger restart failed"
[ "$(field testMode.runsUsed)" = 0 ] && [ "$(field triggerOverrides.0.integrationProviderId)" = conn-gmail-3 ] || fail "the restart did not apply the new trigger connection"
ok "a trigger's test connection restarts test mode only after the reset is confirmed"

printf '["one", {"query": "two"}, "three"]' > "$tm/inputs.json"
bt test-mode run agent-1 --inputs-file "$tm/inputs.json"; expect 0 "inputs file failed"
[ "$(field runsRemaining)" = 0 ] && [ "$(field testMode)" = off ] || fail "the session should switch off when its runs are used"
bt test-mode run agent-1 --input more; expect 8 "a used-up session must exit test_runs_exhausted"
bt test-mode stop agent-1; expect 7 "stopping a stopped session must exit test_mode_inactive"
bt test-mode start agent-1; expect 0 "restart after exhaustion failed"
touch "$tm/fake/race409"
bt test-mode run agent-1 --input x; expect 8 "an API 409 must map to test_runs_exhausted, not a network error"
grep -q 'Test runs exhausted: 3 of 3 used' "$tm/out" && [ "$(field notStarted.0)" = x ] || fail "the API error body or the unstarted inputs were dropped"
rm -f "$tm/fake/race409"
bt test-mode stop agent-1; expect 0 "stop failed"
touch "$tm/fake/deny403"
bt test-mode start agent-1; expect 9 "a 403 must exit permission_denied"
rm -f "$tm/fake/deny403"
ok "API errors keep their message and map to test_mode_*, test_runs_exhausted and permission_denied"

bt test-mode start agent-1 --max-runs 3; expect 0 "start before the replay failed"
bt test-mode replay agent-1 --task past-mail --task past-forbidden --task past-other --task past-chat; expect 0 "the replay failed"
python3 -c 'import json,sys
d=json.load(open(sys.argv[1]))
assert [r["sourceTaskId"] for r in d["started"]] == ["past-mail", "past-chat"] and all(r["taskId"] for r in d["started"]), d["started"]
assert d["leftOut"] == [{"taskId": "past-forbidden", "reason": "not accessible to your role"},
                       {"taskId": "past-other", "reason": "belongs to agent agent-2, not agent-1"}], d["leftOut"]
assert d["runsUsed"] == 2 and d["runsRemaining"] == 1, d
bodies=[json.loads(line) for line in open(sys.argv[2]).read().splitlines()[-2:]]
for body in bodies:
    assert set(body) == {"agentId", "taskQuery", "isTestTask"} and body["agentId"] == "agent-1" and body["isTestTask"] is True, body
    assert isinstance(body["taskQuery"], dict), body
    assert not {"beamAgentOSTaskID", "beamAgentOSTaskId", "beamTaskId", "beamTaskTimestamp"} & set(body["taskQuery"]), body
assert "query" not in bodies[0]["taskQuery"] and bodies[0]["taskQuery"]["attachments"][0]["key"] == "files/invoice.pdf", bodies[0]
assert bodies[1]["taskQuery"] == {"query": "Where is my order?"}, bodies[1]' "$tm/out" "$tm/fake/taskbodies" || fail "the replay did not start one test task per row with the stripped input: $(cat "$tm/out")"
bt test-mode stop agent-1; expect 0 "stop after the replay failed"
ok "replay starts one test task per row with the stored input as sent, and lists the ids it left out"

kill "$TM_PID" 2>/dev/null || true

printf '\nPlaybook contract checks PASSED.\n'
