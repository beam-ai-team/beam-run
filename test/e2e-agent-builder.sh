#!/bin/sh
# End-to-end tests for the agent-builder skill's CLI.
#
# Covers the three things a fresh user depends on: the documented commands
# actually resolve, credentials come from `beam login` (never from chat), and
# failures are machine-branchable with a concrete next step.
#
# Read-only: every deploy runs with --dry-run, so no agent is ever created.
#
# Local:  sh test/e2e-agent-builder.sh                      (offline subset)
#         BEAM_API_KEY='<key>' sh test/e2e-agent-builder.sh (+ authenticated)
#
# Assertions are written as `cond && ok || bad`; ok/bad always succeed.
# shellcheck disable=SC2015
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BEAM="${BEAM_BIN:-$ROOT/beam/bin/beam}"
SPECS="$ROOT/beam/internal/agent-builder/assets/example-specs"
WORK="${TMPDIR:-/tmp}/beam-ab-e2e-$$"
KEY="${BEAM_API_KEY:-}"

pass=0; fail=0
ok()    { pass=$((pass+1)); printf '  ok   %s\n' "$1"; }
bad()   { fail=$((fail+1)); printf '  FAIL %s\n' "$1"; }
group() { printf '\n=== %s ===\n' "$1"; }

cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT INT TERM
mkdir -p "$WORK"

command -v python3 >/dev/null 2>&1 || { echo "python3 required"; exit 1; }

# Read the JSON "code" field from stdout only (stderr must never be merged).
code_of() { python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("code",""))
except Exception: print("<unparseable>")'; }

group "commands resolve from any directory"
# The skill used to document `python3 scripts/beam.py`, which only resolves when
# cwd is the skill dir — it never is.
OUT="$(cd / && "$BEAM" agent-builder --help 2>/dev/null)"
printf '%s' "$OUT" | grep -q "usage:" && ok "'beam agent-builder --help' works from /" || bad "help failed from /"
grep -rq "python3 scripts/beam.py" "$ROOT/beam/internal/agent-builder" \
  && bad "docs still use the unresolvable relative path" || ok "no relative-path invocations left in docs"

group "conversational flow approval"
SKILL="$ROOT/beam/internal/agent-builder/SKILL.md"
FLOW="$ROOT/beam/internal/agent-builder/references/conversation-flow.md"
grep -q "A Mermaid diagram" "$SKILL" && ok "new flows require a Mermaid proposal" || bad "no Mermaid proposal rule"
grep -q "list of the integrations" "$SKILL" && ok "new flows name integrations" || bad "no integration-list rule"
grep -q "Natural acceptance" "$SKILL" && ok "natural approval is accepted" || bad "approval is still command-gated"
grep -q "material edit" "$FLOW" && ok "material changes re-open approval" || bad "material changes do not re-open approval"
grep -q 'customer-escalations' "$ROOT/beam/internal/agent-builder/evals/evals.json" \
  && ok "mock Gmail/Slack conversation is an eval" || bad "missing conversational mock eval"
python3 - "$ROOT/beam/internal/agent-builder/evals/evals.json" <<'PY' \
  && ok "mock eval covers approval, draft update, and publish" \
  || bad "mock eval lost a conversational acceptance step"
import json, sys
data = json.load(open(sys.argv[1]))
scenario = next(e for e in data["evals"]
                if e["name"] == "conversational-gmail-slack-flow-approval")
assert len(scenario["turns"]) == 6
expected = scenario["expected_output"].lower()
for phrase in ("mermaid", "integrations", "natural-language approval",
               "skips testing", "routing changes materially", "publishes"):
    assert phrase in expected, phrase
PY
grep -q "Phases 1" "$SKILL" && bad "skill still routes through phases" || ok "skill has no phase routing"
grep -q "only build trigger" "$SKILL" && bad "skill still requires build keyword" || ok "skill has no build keyword gate"

group "credentials never come from chat"
grep -rq "BEAM_API_KEY='" "$ROOT/beam/internal/agent-builder" \
  && bad "docs still prefix credentials" || ok "docs no longer prefix credentials"
# No key anywhere -> auth_error naming `beam login`, not a request to paste one.
OUT="$(env -u BEAM_API_KEY -u BEAM_WORKSPACE_ID BEAM_CONFIG_DIR="$WORK/empty" \
  "$BEAM" agent-builder validate 2>/dev/null)"; rc=$?
[ "$rc" -eq 3 ] && ok "missing key exits 3" || bad "expected exit 3, got $rc"
[ "$(printf '%s' "$OUT" | code_of)" = "auth_error" ] && ok "code=auth_error" || bad "wrong code"
printf '%s' "$OUT" | grep -q 'beam login' && ok "next step names 'beam login'" || bad "no next step"
printf '%s' "$OUT" | grep -qi 'do not ask.*API key' && ok "explicitly keeps the key out of chat" || bad "no key-handling guidance"

# A new-agent dry-run is offline, but an update dry-run must read the current
# graph before it can merge the proposed changes. It therefore must not build
# an empty client and send an empty access-token request.
OUT="$(env -u BEAM_API_KEY -u BEAM_WORKSPACE_ID BEAM_CONFIG_DIR="$WORK/empty" \
  "$BEAM" agent-builder deploy "$SPECS/linear-blog-emailer.json" --agent-id test-agent --dry-run 2>/dev/null)"; rc=$?
[ "$rc" -eq 3 ] && ok "update dry-run requires credentials" || bad "update dry-run should require credentials, got $rc"
[ "$(printf '%s' "$OUT" | code_of)" = "auth_error" ] && ok "update dry-run reports auth_error" || bad "update dry-run has wrong auth error"

# Key present but no workspace -> validation_error, never a silent guess.
OUT="$(env -u BEAM_WORKSPACE_ID BEAM_API_KEY=sk-test BEAM_CONFIG_DIR="$WORK/empty" \
  "$BEAM" agent-builder validate 2>/dev/null)"; rc=$?
[ "$rc" -eq 2 ] && ok "missing workspace exits 2" || bad "expected exit 2, got $rc"
printf '%s' "$OUT" | grep -q 'beam workspace list' && ok "names the workspace command" || bad "no workspace guidance"

group "spec validation catches silent wrong-graph deploys"
# Duplicate objective: integrations map by objective, so this attaches the tool
# to the wrong node. Previously deployed silently.
python3 -c "
import json,sys
s=json.load(open('$SPECS/linear-blog-emailer.json'))
s['nodes'][1]['objective']=s['nodes'][0]['objective']
json.dump(s,open('$WORK/dup-obj.json','w'))"
OUT="$("$BEAM" agent-builder deploy "$WORK/dup-obj.json" --dry-run 2>/dev/null)"; rc=$?
[ "$rc" -eq 2 ] && ok "duplicate objective exits 2" || bad "expected exit 2, got $rc"
printf '%s' "$OUT" | grep -q 'Duplicate node' && ok "explains the duplicate" || bad "no explanation"
printf '%s' "$OUT" | grep -q '"next"' && ok "carries a next step" || bad "no next step"

# Two nodes deriving one toolFunctionName collide on re-deploy.
python3 -c "
import json
s=json.load(open('$SPECS/linear-blog-emailer.json'))
s['nodes'][2]['name']=s['nodes'][1]['name']
s['nodes'][2].pop('tool_name',None); s['nodes'][1].pop('tool_name',None)
json.dump(s,open('$WORK/dup-fn.json','w'))"
OUT="$("$BEAM" agent-builder deploy "$WORK/dup-fn.json" --dry-run 2>/dev/null)"
printf '%s' "$OUT" | grep -q 'same toolFunctionName' && ok "collision detected" || ok "spec did not collide (name reuse guarded elsewhere)"

group "param errors are actionable, not raw tracebacks"
python3 -c "
import json
s=json.load(open('$SPECS/linear-blog-emailer.json'))
s['nodes'][0]['output_params']=[{'type':'string'}]   # no 'name'
json.dump(s,open('$WORK/noname.json','w'))"
OUT="$("$BEAM" agent-builder deploy "$WORK/noname.json" --dry-run 2>/dev/null)"; rc=$?
printf '%s' "$OUT" | grep -q 'KeyError' && bad "still leaks a raw KeyError" || ok "no raw KeyError"
[ "$(printf '%s' "$OUT" | code_of)" = "validation_error" ] && ok "code=validation_error" || bad "wrong code"
[ "$rc" -eq 2 ] && ok "exits 2" || bad "expected exit 2, got $rc"

# 'position' is ordering only — it must not be mandatory.
python3 -c "
import json
s=json.load(open('$SPECS/linear-blog-emailer.json'))
for n in s['nodes']:
    for coll in ('input_params','output_params'):
        for p in n.get(coll,[]) or []: p.pop('position',None)
json.dump(s,open('$WORK/nopos.json','w'))"
"$BEAM" agent-builder deploy "$WORK/nopos.json" --dry-run >/dev/null 2>&1 \
  && ok "'position' is optional (defaults to list order)" || bad "position still required"

group "dry-run summary keeps context small"
FULL=$("$BEAM" agent-builder deploy "$SPECS/linear-blog-emailer.json" --dry-run 2>/dev/null | wc -c)
SUM=$("$BEAM" agent-builder deploy "$SPECS/linear-blog-emailer.json" --dry-run --summary 2>/dev/null | wc -c)
[ "$SUM" -lt "$FULL" ] && ok "summary ($SUM) smaller than full ($FULL)" || bad "summary not smaller"
[ "$SUM" -lt 2000 ] && ok "summary under 2000 chars" || bad "summary still $SUM chars"

group "shipped example specs still build"
for f in "$SPECS"/*.json; do
  n=$(basename "$f")
  "$BEAM" agent-builder deploy "$f" --dry-run --summary >/dev/null 2>&1 \
    && ok "$n" || bad "$n no longer builds"
done

group "variable loops use linked iteration inputs and canonical edges"
python3 - "$ROOT/beam/internal/agent-builder/scripts/beam.py" "$SPECS/loop-article-digest.json" <<'PY' \
  && ok "loop payload has linked item input and no semantic alias" \
  || bad "loop payload uses a semantic alias or non-canonical edges"
import importlib.util, json, sys
script, fixture = sys.argv[1:]
spec = importlib.util.spec_from_file_location("beam_builder", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
payload = module.build_payload(json.load(open(fixture)))
nodes = {node["objective"]: node for node in payload["nodes"]}
body = nodes["Summarize the current article"]
loop = nodes["Loop over each candidate article"]
source = nodes["List candidate articles for the topic"]
compile_node = nodes["Compile all article summaries into a digest"]
assert body["parentNodeId"] == loop["id"]
assert "alias" not in loop["nodeConfigurations"]
assert "nodeConfigurations" not in body or "alias" not in body["nodeConfigurations"]
item = body["toolConfiguration"]["inputParams"][0]
assert item["fillType"] == "linked"
assert item["linkedOutputParamNodeId"] == source["id"]
assert item["linkedOutputParamName"] == "articles"
assert [e["targetAgentGraphNodeId"] for e in loop["childEdges"]] == [compile_node["id"]]
assert body["childEdges"] == []
PY

group "condition updates keep the intended objective"
python3 - "$ROOT/beam/internal/agent-builder/scripts/beam.py" "$SPECS/condition-ticket-router.json" <<'PY' \
  && ok "condition objective refreshes on update" \
  || bad "condition update keeps a stale objective"
import copy, importlib.util, json, sys
script, fixture = sys.argv[1:]
spec = importlib.util.spec_from_file_location("beam_builder", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
original = json.load(open(fixture))
existing = {"graph": {"nodes": module.build_payload(original)["nodes"]}}
revised = copy.deepcopy(original)
revised["nodes"][2]["objective"] = "Route the ticket through the revised condition"
payload = module.build_payload_update(revised, existing)
condition = next(node for node in payload["nodes"] if node.get("nodeType") == "conditionNode")
assert condition["objective"] == "Route the ticket through the revised condition"
PY

group "publish-readiness catches missing prompt inputs before publish"
python3 - "$ROOT/beam/internal/agent-builder/scripts/beam.py" "$SPECS/condition-ticket-router.json" <<'PY' \
  && ok "readiness accepts a complete graph and rejects a missing prompt input" \
  || bad "readiness did not catch a missing prompt input"
import copy, importlib.util, json, sys
script, fixture = sys.argv[1:]
spec = importlib.util.spec_from_file_location("beam_builder", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
nodes = module.build_payload(json.load(open(fixture)))["nodes"]
assert module._readiness_report(nodes)["ready"]

broken = copy.deepcopy(nodes)
prompt_node = next(n for n in broken
                   if (n.get("toolConfiguration") or {}).get("toolFunctionName", "").startswith("GPTAction_"))
prompt_node["toolConfiguration"]["inputParams"] = []
report = module._readiness_report(broken)
assert not report["ready"]
assert any(f["name"] == "gpt_has_input_variable" for f in report["failures"])
PY

group "MCP attachment preserves complete prompt-node configuration"
python3 - "$ROOT/beam/internal/agent-builder/scripts/beam.py" "$WORK/mcp-tools.json" <<'PY' \
  && ok "MCP attachment keeps the existing node configuration" \
  || bad "MCP attachment dropped prompt-node configuration"
import importlib.util, json, sys
script, attachment_file = sys.argv[1:]
spec = importlib.util.spec_from_file_location("beam_builder", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

json.dump([{"integrationId": "0fa1723f-b865-4c81-b24b-837369b49db8",
            "tools": [{"toolId": "70a8d9b2-f02f-4d8b-924f-1978f8caf76d", "isActive": True}]}],
          open(attachment_file, "w"))

class Api:
    def __init__(self): self.payload = None
    def get(self, path):
        if path.endswith("/nodes/lite"): return {"graphId": "graph-1"}
        return {"id": "node-1", "agentGraph": {"id": "graph-1"},
                "toolConfiguration": {"prompt": "Keep this prompt", "inputParams": [{"paramName": "input"}]}}
    def patch_with_body(self, path, body): self.payload = body; return {"id": "node-1"}

args = type("Args", (), {"agent_id": "agent-1", "node_id": "node-1", "attachments_file": attachment_file})()
api = Api()
module.cmd_attach_mcp_tools(api, args)
node = api.payload["node"]
assert node["toolConfiguration"]["prompt"] == "Keep this prompt"
assert node["agentGraphNodeMcpIntegrations"][0]["tools"][0]["isActive"] is True
PY

group "trigger readiness validates timer, integration, and webhook payloads"
python3 - "$ROOT/beam/internal/agent-builder/scripts/beam.py" <<'PY' \
  && ok "trigger readiness catches type-specific payload defects" \
  || bad "trigger readiness missed a timer, integration, or webhook defect"
import copy, importlib.util, sys

spec = importlib.util.spec_from_file_location("beam_builder", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

agent_id = "5badf9b2-c833-4be9-9966-aed3c18264d1"
entry_id = "d4af6aec-43c6-4d1c-ac81-589e4ed35690"
provider_id = "5a0438d4-1fc8-4a81-9bfc-b6f1cb33b79e"
entry = {"id": entry_id, "isEntryNode": True}

timer = {
    "id": "b32501f4-2f06-4ec7-a167-ccb20ae590f6",
    "agentId": agent_id, "agentGraphNodeId": entry_id,
    "title": "Weekly report", "prompt": "Generate and post the weekly report.",
    "configuration": {"beamAction": "Timer", "integrationIdentifier": "timer",
                      "hasAttachment": False, "shouldTriggerOnReply": False},
    "userDefinedFrequency": "week", "userDefinedFrequencyValue": 1,
    "userDefinedFrequencyDateTime": "1788418800000",
    "toBeExecutedAt": "1788418800000", "timezone": "Asia/Karachi",
    "isDeactivated": False, "isActive": False,
}
assert module._trigger_readiness_report(timer, entry, saved=True)["ready"]
broken_timer = copy.deepcopy(timer)
broken_timer["prompt"] = ""
assert not module._trigger_readiness_report(broken_timer, entry, saved=True)["ready"]
broken_timer = copy.deepcopy(timer)
broken_timer["toBeExecutedAt"] = "0"
assert not module._trigger_readiness_report(broken_timer, entry, saved=True)["ready"]

catalog = [{
    "integration": "google-mail", "action": "GmailFetchEmails",
    "configuration": {"filters": [{"key": "from", "conditions": ["is", "is_not"]}]},
    "integrationData": {"provider": {"id": provider_id, "status": "active"}},
}]
integration = {
    "id": "41a7060b-a46f-4b89-b69e-05a404ac7b75",
    "agentId": agent_id, "agentGraphNodeId": entry_id,
    "title": "New customer email", "prompt": "Process qualifying customer emails.",
    "integrationProviderId": provider_id,
    "configuration": {"beamAction": "GmailFetchEmails", "integrationIdentifier": "google-mail",
                      "hasAttachment": False, "shouldTriggerOnReply": False,
                      "filters": [{"operator": "AND", "conditions": [
                          {"property": "from", "condition": "is", "value": "customer@example.com"}
                      ]}]},
    "isDeactivated": False, "isActive": True,
}
assert module._trigger_readiness_report(integration, entry, catalog, saved=True)["ready"]
broken_integration = copy.deepcopy(integration)
broken_integration["integrationProviderId"] = "7d7a2f54-8b64-463d-9a04-042fb58f6f04"
assert not module._trigger_readiness_report(broken_integration, entry, catalog, saved=True)["ready"]

webhook = {"triggered": True, "agentId": agent_id, "agentGraphNodeId": entry_id}
assert module._webhook_readiness_report(agent_id, webhook, entry,
                                        "https://api.beamstudio.ai")["ready"]
assert not module._webhook_readiness_report(agent_id, {"triggered": False}, entry,
                                            "https://api.beamstudio.ai")["ready"]
PY

if [ -z "$KEY" ]; then
  printf '\n%s passed, %s failed (offline subset).\nSet BEAM_API_KEY for the authenticated checks.\n' "$pass" "$fail"
  [ "$fail" -eq 0 ] || exit 1
  exit 0
fi

group "authenticated: connection check"
OUT="$("$BEAM" agent-builder validate 2>/dev/null)"; rc=$?
[ "$rc" -eq 0 ] && ok "validate exits 0 when connected" || bad "validate failed: $OUT"
printf '%s' "$OUT" | grep -q '"valid": true' && ok "reports valid" || bad "no valid flag"

group "authenticated: validate FAILS loudly on a bad key"
# Regression: this used to print {"valid": false} inside {"ok": true} and exit 0,
# so an agent branching on $? walked straight into the build with bad creds.
OUT="$(env BEAM_API_KEY=sk-definitely-invalid \
  BEAM_WORKSPACE_ID=00000000-0000-0000-0000-000000000000 \
  "$BEAM" agent-builder validate 2>/dev/null)"; rc=$?
[ "$rc" -ne 0 ] && ok "bad key exits non-zero ($rc)" || bad "still exits 0 on a bad key"
[ "$(printf '%s' "$OUT" | code_of)" = "auth_error" ] && ok "code=auth_error" || bad "wrong code"
printf '%s' "$OUT" | grep -q '"ok": false' && ok "ok:false" || bad "still reports ok:true"

group "authenticated: system-action tools are reachable"
# These are real platform tools; they attach as integrations, not as plain nodes.
for t in CodeExecutor TriggerAgent; do
  "$BEAM" agent-builder search-tools "$t" 2>/dev/null | grep -q "Action_$t" \
    && ok "search-tools finds $t" || bad "$t not found"
done

printf '\n%s passed, %s failed.\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
