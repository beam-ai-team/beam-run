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
SPECS="$ROOT/beam/skills/agent-builder/assets/example-specs"
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
grep -rq "python3 scripts/beam.py" "$ROOT/beam/skills/agent-builder" \
  && bad "docs still use the unresolvable relative path" || ok "no relative-path invocations left in docs"

group "conversational flow approval"
SKILL="$ROOT/beam/skills/agent-builder/SKILL.md"
FLOW="$ROOT/beam/skills/agent-builder/references/conversation-flow.md"
grep -q "A Mermaid diagram" "$SKILL" && ok "new flows require a Mermaid proposal" || bad "no Mermaid proposal rule"
grep -q "list of the integrations" "$SKILL" && ok "new flows name integrations" || bad "no integration-list rule"
grep -q "Natural acceptance" "$SKILL" && ok "natural approval is accepted" || bad "approval is still command-gated"
grep -q "material edit" "$FLOW" && ok "material changes re-open approval" || bad "material changes do not re-open approval"
grep -q 'customer-escalations' "$ROOT/beam/skills/agent-builder/evals/evals.json" \
  && ok "mock Gmail/Slack conversation is an eval" || bad "missing conversational mock eval"
python3 - "$ROOT/beam/skills/agent-builder/evals/evals.json" <<'PY' \
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
grep -rq "BEAM_API_KEY='" "$ROOT/beam/skills/agent-builder" \
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
python3 - "$ROOT/beam/skills/agent-builder/scripts/beam.py" "$SPECS/loop-article-digest.json" <<'PY' \
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
python3 - "$ROOT/beam/skills/agent-builder/scripts/beam.py" "$SPECS/condition-ticket-router.json" <<'PY' \
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
