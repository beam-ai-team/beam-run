# Beam Run supervisor — comprehensive testing plan

## Goal

Prove that Beam Run provides the Beam Copilot operating model inside a coding
agent: one supervisor, the same domain ownership and instructions, MCP-first
execution, deterministic CLI fallback, preserved context, and truthful
completion. The existing onboarding experience is a protected regression area.

## Test environments

Use three isolated environments:

1. **Offline contract environment** — no credentials or network; validates prompt
   provenance, routing coverage, command syntax, and safety gates.
2. **Staging workspace** — disposable agents, tasks, connections, views, and
   Learning Hub data; runs every read and reversible write.
3. **Controlled live workspace** — one test agent with harmless integrations;
   validates consent and external-effect behavior without touching production data.

For staging, prepare:

- one active agent and one agent with an unpublished draft;
- one running, completed, failed, waiting, and consent-paused task;
- at least two integrations, including multiple connections for one provider;
- one template with prerequisites and one without;
- one View with normal and linked columns;
- one Learning Hub issue and one completed optimization job;
- one agent context file, one external URL file, and one sub-agent attachment.

## Global acceptance gates

Every scenario must satisfy all applicable gates:

| Gate | Pass condition |
| --- | --- |
| Routing | The supervisor selects the canonical specialist; multi-domain work is decomposed in dependency order. |
| Prompt parity | The specialist follows the checked-in Copilot snapshot and host adapter; prompt hash checks pass. |
| Context | Workspace, agent, task, active/draft graph, and confirmation state survive every handoff and fallback. |
| MCP first | A healthy mapped MCP tool is attempted before CLI unless the operation is CLI-only. |
| Fallback | Missing tool, malformed result, transport failure, or documented MCP defect causes the mapped CLI command—not improvisation or abandonment. |
| Ambiguous writes | A lost/malformed write response causes a state read before any replay. No create/delete/publish/approval is blindly repeated. |
| Safety | Destructive and external-effect operations require the specified natural-language approval and exact CLI confirmation token. |
| Grounding | IDs, names, statuses, counts, dates, graph mode, and metrics match tool output exactly. |
| Completion | Result is `completed`, `completed-with-fallback`, `needs-user-input`, or `blocked-platform`, with the relevant artifact or precise blocker. |
| Onboarding | Setup/login/register/doctor and the signed-out MCP session behave exactly as before. |

## Functional coverage by module

Run each row once with MCP healthy and once with the mapped MCP tool hidden or
forced to return a recoverable malformed response. CLI-only rows need one normal
run plus their read-after-write verification.

| Module | Scenarios | Required verification |
| --- | --- | --- |
| Supervisor | Single-domain route; multi-domain request; dependent chain; independent reads; user correction midway | One coherent answer; no duplicate specialists; corrected context reaches all later steps |
| General workspace | Current user; list/resolve agents; inspect task by ID; ambiguous workspace; empty workspace | Correct workspace named; no silent cross-workspace scan |
| Agent tasks | List/filter/status counts/latest; live create; draft test; detail; retry; rate; cancel wait; abort; delete | Live/draft graph is explicit; returned task/graph IDs checked; destructive actions confirmed |
| Global tasks | Search across agents; group/filter; resolve agent from task; bulk-style sequence | Bounded results; each write targets the resolved task and workspace |
| Inbox | List/unread count; mark read; explain notification; submit requested input; approve/reject consent; delete | Underlying task/node is read first; proposed values and consent are confirmed; state is re-read |
| Agent flow | Read graph/nodes/node; trigger and webhook inspection; link verification; graph history | Explanation follows trigger → path → branches/waits → exit; no mutation from read-only skill |
| Agent builder | New draft; metadata update; prompt/parameter/node/edge/tool/consent changes; trigger/webhook; test; publish | Existing builder suite passes; smallest patch used; draft default preserved; publish explicit |
| Agent config | Metadata; tools; sub-agents; context files; upload/URL attach; reassign/remove; agent deletion | Copilot-supported fields only; file/tool removals confirmed; post-write lists match |
| Integrations | Catalog/categories; connected state; connection list; connect/update/default/remove; custom create/update/remove | IDs resolved from reads; credentials only in payload files; no secrets in chat/history; removals confirmed |
| Templates | Categories/list/detail/recommendations/prerequisites; create agent | Full template read before create; prerequisites stated; new agent remains draft unless separately published |
| Analytics | Default and explicit date ranges; metrics; task drill-down; graph-history correlation; export | Exact range and metric labels reported; causal claims supported by drill-down data |
| Views | List/detail/columns/records/linked records; create/delete; add/update/delete column; CSV export | Schema read before record explanation; update payload retains required mapping fields; destructive changes confirmed |
| Learning Hub | Issues by tab; issue/feedback/job detail; accuracy/tool/config reads; optimize; approve/reject/re-run/cancel where available | Two-turn confirmation on credit/live-prompt actions; exact prompt diff and job status; post-write re-read |
| Host capabilities | Local file/code/web work needed by a Beam request | Host performs generic work; Beam specialists retain ownership of Beam state changes |

## Failure-injection matrix

| Injected condition | Expected behavior |
| --- | --- |
| MCP tool absent | `beam mcp check --tool …` reports missing; specialist runs mapped CLI command |
| MCP endpoint unreachable | CLI fallback runs if Beam API remains reachable; otherwise `blocked-platform` names both failures |
| MCP result is non-object/malformed | Read operation retries through CLI; write operation reconciles state before any retry |
| CLI not on PATH | Specialist resolves bundled launcher and continues; onboarding is not restarted solely for PATH |
| CLI authentication invalid | Original operation pauses; existing setup/login flow is used; operation resumes afterward |
| Workspace ambiguous | Ask once, save selected workspace, continue the original specialist task |
| Permission/validation failure | Do not change transport repeatedly; report the exact permission or field issue |
| API 5xx after write body sent | Treat as ambiguous; inspect state; never replay blindly |
| User changes target mid-flow | Discard stale target context; re-resolve and continue with the new target |

## Automated suites

Run from the repository root:

```sh
sh test/supervisor-contract.sh
sh test/copilot-source-drift.sh
sh test/smoke.sh
sh test/e2e.sh
sh test/e2e-agent-builder.sh
```

Before accepting changes, also run:

```sh
sh -n beam/bin/beam
git diff --check
```

Expected result: all checks pass, and there is no diff under
`beam/skills/setup/`, `GETTING_STARTED.md`, or the signed-out behavior in
`beam/bin/mcp_proxy.py` unless onboarding was explicitly approved as a separate change.

## Manual review sequence

1. Run unchanged onboarding from a clean home directory and restart the host.
2. Ask a read-only cross-module question; inspect supervisor routing and context.
3. Run a live task and a draft test with the same input; verify distinct graph IDs.
4. Force the task MCP tool missing; repeat and verify CLI fallback plus identical result reporting.
5. Pause a harmless task for input and consent; test submit, reject, and approve paths.
6. Perform one reversible write in integrations, templates, Views, agent config,
   and Learning Hub; re-read after each.
7. Simulate a dropped response after a create/write and verify reconciliation prevents duplication.
8. Execute one multi-domain request such as “find the failing task, explain the
   flow, fix the draft prompt, test it, then show the new analytics.” Verify
   ordered delegation, preserved IDs, explicit draft/live state, and one final summary.

## Sign-off record

Record for every module: environment, date, tester, MCP result, fallback result,
the `BEAM_TRACE_TRANSPORT=1` outcome, safety result, context result,
response-quality result, defects, and evidence links/task IDs. The feature is ready for personal use when all global gates pass,
all high-risk writes have live evidence, and no onboarding regression exists.
