# Beam Production Validation Decisions

## 2026-08-12 — Validation scope and audit log

- **Decision:** Validate the Beam CLI and agent-builder surfaces against the production workspace manually selected in the Beam app: `Saqib` (`227e402a-e065-492a-ba26-3934bb9ce929`).
- **Reason:** The user requested an end-to-end production verification and asked that every change be recorded.
- **Safety boundary:** Exercise read operations directly. Exercise writes only through a disposable, draft-only test agent and synthetic task data. Do not publish, send external communications, approve consent, alter existing production automations, or delete any existing agent other than an explicitly created disposable test agent.
- **Verification baseline:** The in-app Beam session shows `Selected: Saqib`.

## 2026-08-12 — CLI-only change control

- **Decision:** Use Beam Run CLI/API as the sole mechanism for production reads, tests, and changes.
- **Reason:** The user requires the browser to be an observation surface only, so production behavior can be verified in the product without bypassing the CLI workflow.
- **Browser rule:** Do not create, edit, delete, publish, approve, or submit anything through the browser. A browser-side change is allowed only when it is necessary to resolve a blocking dependency; record the reason in this file before taking it.
- **Verification rule:** After a CLI/API action, use the browser only to confirm that the corresponding user-visible state matches the expected result.

## 2026-08-12 — Disposable CLI validation agent

- **Decision:** Create one disposable draft agent named `Beam Run CLI Validation — 2026-08-12` for production endpoint verification.
- **Reason:** It isolates write-path tests from the user's existing agents and avoids integrations or external side effects.
- **Graph:** Entry → normalize a synthetic text input → exit.
- **Permitted mutations on this agent:** draft deployment, metadata/prompt/parameter/edge/node changes, synthetic draft tasks, and trigger/webhook lifecycle checks. The agent will not be published and no consent-gated integration will be approved.
- **Cleanup:** Delete this agent only after the user confirms the recorded validation results.

### Result

- Created by CLI: agent `5badf9b2-c833-4be9-9966-aed3c18264d1`; draft graph `4b52a7ef-b9cd-4dfd-95d2-2074450fa90d`.
- Deployment verification: passed; all links are valid; `published: false`.

### Validation observations

- CLI reads (`agents get`, `agent-builder get-graph`, `get-nodes`, and `verify-links`) passed against the disposable agent.
- A synthetic CLI draft task was created: `e69b1957-05bb-49ea-adce-0aa4ffe47f6f` on draft graph `4b52a7ef-b9cd-4dfd-95d2-2074450fa90d`.
- The MCP `listenTask` monitoring endpoint returned HTTP 502. This is recorded as a server-side MCP defect; task monitoring will use CLI `beam tasks get` until a dedicated CLI listener is added.

## 2026-08-12 — Correct single-node test API contract

- **Decision:** Change `agent-builder test-node` to require `agentId`, `graphId`, `nodeId`, and a JSON `params` object.
- **Reason:** Beam's published OpenAPI schema for `POST /agent-graphs/test-node` requires those fields. The prior CLI used an undocumented `taskContext` field and omitted `graphId`, which caused failed node tests.
- **Scope:** CLI argument parsing and request payload only; no existing production agent is changed.

### Result

- Local compile and agent-builder regression suite passed (`33` checks).
- Production response remains `404 Cannot POST /agent-graphs/test-node` with the documented route and payload. This is a Beam API implementation/specification mismatch and cannot be corrected in the CLI repository alone.

## 2026-08-12 — Disposable graph mutation coverage

- **Decision:** Exercise the remaining draft-graph mutation commands only on agent `5badf9b2-c833-4be9-9966-aed3c18264d1`.
- **Operations:** update agent metadata; update a custom-node prompt; read/write its I/O parameters; update one draft edge; add then remove a temporary no-op node, verifying rewiring after each operation.
- **Reason:** These are the CLI write endpoints that need production verification. The graph remains unpublished, has no integrations, and uses no external data.

### Execution plan

- Update the disposable agent description with a validation-only marker, update the custom node's prompt with a no-op validation sentence, submit its existing I/O parameter shapes, and make a no-op unconditional edge update.
- Add a temporary custom node between the normalize and exit nodes, validate graph links, then remove it and validate the original route again.
- These changes are intentionally confined to the draft validation agent and will not be published.

### Observation

- `update-metadata` completed successfully but Beam regenerated all draft node and edge IDs while retaining graph ID `4b52a7ef-b9cd-4dfd-95d2-2074450fa90d`. Calls using IDs read before that update returned `Invalid nodeId`, `Node … not found in draft graph`, and `Edge not found`.
- **Follow-up:** Re-read draft node IDs after any whole-graph update. The CLI will surface the current node list from `update-metadata` so callers can continue deterministically.

## 2026-08-12 — Fix `add-node` output parameter construction

- **Problem:** `agent-builder add-node` raised `NameError: name 'i' is not defined` when the supplied node had output parameters. The error happened while building the request, before any production graph mutation.
- **Decision:** Enumerate output parameters when assigning their default `position`, matching the already-correct input-parameter construction.
- **Scope:** Local CLI only; the disposable graph remains unchanged by the failed request.

### Result

- After the local fix, `add-node` succeeded with the temporary custom node and correctly returned its server-assigned node ID. A CLI read confirmed its prompt, input/output parameters, and both graph edges.
- `remove-node` then succeeded and restored the disposable graph to Entry → Normalize → Exit. The active draft remains unpublished.
- Beam again regenerated node IDs on the whole-graph add/remove writes. The CLI now returns an authoritative new-node ID after add, and `update-metadata` returns the refreshed node list.

## 2026-08-12 — Trigger and webhook surface coverage

- **Decision:** Read the disposable agent's trigger list and the public timer trigger action catalog. Create, read, and delete only an uninvoked webhook on the disposable draft agent.
- **Reason:** This verifies the CLI's trigger/webhook endpoints without scheduling a real automation, connecting an integration, or invoking any external system.
- **Safety:** The webhook will not receive a request. No timer or integration trigger will be created, toggled, or executed.

### Webhook result

- `create-webhook`, `get-webhook`, and `delete-webhook` all succeeded for the disposable agent. The temporary webhook ID was `398d15c6-ef39-4272-9734-86f53463b749`; it was never invoked and the final read was empty.

## 2026-08-12 — Disposable timer-trigger lifecycle

- **Decision:** Create a 24-hour `Timer` trigger attached to the disposable agent's current entry node, read it, update its title, toggle its deactivation state once, then delete it.
- **Reason:** Exercise the create/read/update/toggle/delete CLI endpoints without an external provider or an executable production agent.
- **Safety:** The agent is unpublished and the interval is 24 hours; the trigger will be deleted in the same validation sequence. No task will be submitted or allowed to run from it.

### Result

- `create-trigger`, `get-triggers`, `update-trigger`, `toggle-trigger`, and `delete-trigger` all succeeded with temporary timer trigger `d0441aef-0eec-494d-beec-c1180962c6d5`.
- The trigger stayed inactive because the agent is a draft, was toggled to deactivated, then deleted. The final trigger list is empty.

## 2026-08-12 — Post-mutation draft-task confirmation

- **Decision:** Run one final synthetic draft task through the disposable three-node graph after all graph mutations and trigger cleanup.
- **Reason:** Confirm the current draft remains executable after the CLI CRUD coverage.
- **Safety:** The task contains only text (`final CLI validation`) and the agent contains no integration, webhook, trigger, or published graph.

### Defect found

- The final task produced `normalized_message: "hello world"` but stalled at the exit transition. CLI inspection showed two identical Normalize → Exit edges.
- **Cause:** `remove-node` rewired the temporary node's parent to its child even though that direct edge already existed before the temporary node was added; it did not de-duplicate graph edges.

## 2026-08-12 — Fix `remove-node` duplicate-edge rewiring

- **Decision:** Make the local `remove-node` rewire helper skip an edge that is already present for the same source and target. Redeploy the original disposable draft specification after the fix to replace the duplicated test graph with the intended three-node, two-edge graph.
- **Reason:** Duplicate graph edges make a seemingly valid graph hang after a node completes. The cleanup restores a known-good draft-only test graph.
- **Scope:** Local CLI logic and the disposable unpublished validation agent only. The currently stuck task will not be retried or approved; the fresh test will use synthetic text only.

### Reset result

- The original three-node fixture redeployed successfully to draft graph `4b52a7ef-b9cd-4dfd-95d2-2074450fa90d` with `published: false` and link verification passed.
- CLI inspection confirmed exactly one Normalize → Exit edge and a true exit node. Fresh draft task `24653e2e-5c21-4fd7-8c10-8fff9788cd2d` completed end-to-end; it normalized the synthetic input to `hello world`, completed the exit node, and reached `COMPLETED`.
- The initial task that exposed the duplicate edge remains unmodified and is excluded from validation results.

## 2026-08-12 — Read-only product verification

- **Decision:** Inspect the disposable agent in the already-open Beam production app without interacting with controls.
- **Result:** The UI shows workspace `Selected: Saqib`, agent `Beam Run CLI Validation — 2026-08-12`, `Draft`, the custom normalize node, the explicit finish/exit node, and the notice `This flow has not yet been published`.
- **Browser compliance:** No browser-side create, edit, delete, publish, execute, trigger, or form action was taken.

## 2026-08-12 — Validation outcome

- Core CLI identity, workspace-scoped agent reads, graph reads, deployment, metadata/prompt/parameter/edge updates, node add/remove, trigger and webhook lifecycle, and draft-task execution were exercised successfully in the selected production workspace.
- Local fixes applied during testing: `add-node` now enumerates output parameters correctly; `remove-node` avoids duplicate rewired edges; whole-graph mutation results return/refetch current node IDs where implemented.
- Outstanding platform defects: the documented `POST /agent-graphs/test-node` returns production `404`, and MCP task listening returned `502`. The CLI's `tasks get` endpoint successfully monitored the completed draft task instead.

## 2026-08-12 — Complex LLM-only graph stress test

- **Decision:** Replace the disposable validation agent's simple three-node draft with a complex, unpublished LLM-only graph.
- **User request:** Stress-test Agent Builder using conditional branches, a real Beam variable-based loop with loop-body nodes, draft runs, user-style corrections, and revisions. Browser remains read-only verification; CLI/API is the only write path.
- **Topology:** Entry → parse request → route; batch route → generate `work_items[]` → looping container (`linkedVariableId: generate-work-items:work_items`, alias `work_item`) → loop-body evaluator → loop-body condition → accepted/rejected loop-body result → compile accumulated arrays → explicit exit. Single route → single-item result → same explicit exit.
- **Node scope:** Custom LLM execution nodes, `conditionNode`, `loopingNode`, and `exitNode` only. No Code Executor, integration, trigger, webhook, consent, or external action.
- **Safety:** The graph stays unpublished. Every task is a synthetic draft task. Test inputs contain only fabricated labels such as `READY` and `REJECT`.
- **Planned user-style iterations:** (1) initial batch and single-item runs; (2) correction to enforce strict case-insensitive `READY` classification; (3) revision to require compact, audit-ready compilation; run affected synthetic cases after each change.

### Pre-deploy result

- The production-profile CLI validation succeeded. The complex fixture dry-run passed with 12 nodes: 8 custom LLM execution nodes, 2 condition nodes, 1 variable-based loop container, 1 exit node, and 0 integrations.
- The local development profile was intentionally not used because it has no selected workspace; no local-profile write was attempted.

### Deploy result

- CLI deployment succeeded on disposable agent `5badf9b2-c833-4be9-9966-aed3c18264d1`, draft graph `4b52a7ef-b9cd-4dfd-95d2-2074450fa90d`, `published: false`.
- `verify-links` passed for all four deterministic linked inputs. Beam assigned fresh IDs to all 12 nodes, as expected after a full graph write.
- **Initial synthetic runs:** `SINGLE READY: solo alpha` must take the single branch. `BATCH READY: alpha; REJECT: beta; READY: gamma` must produce an item array, enter the variable loop, take both loop-body result branches, compile, and exit.

### Initial-run diagnosis

- The single-item task `8659525d-bd0d-4e99-a4e2-05ca288cd58f` completed through the single route and exit with `final_report: The item solo alpha is explicitly READY.`
- The batch task `0b16c15a-c013-47f2-b0e0-25fcd741f8fb` correctly produced `work_items = [READY: alpha, REJECT: beta, READY: gamma]`, but entered `USER_INPUT_REQUIRED` at the loop body because `{work_item}` was absent.
- Inspection showed the container had `alias: work_item` but its child nodes had backend-default `nodeConfigurations.alias: "1"`. The builder sends `parentNodeId` only and does not propagate the loop alias into each body node.

## 2026-08-12 — Fix loop-body alias propagation

- **Decision:** When a spec node is inside a looping-node container, write the parent loop's alias to that child node's `nodeConfigurations.alias`. For a condition-node body, merge that alias with its required condition configuration.
- **Reason:** Beam's runtime reads the alias from the body-node configuration, not only from the loop container. Without it, a valid variable-based loop reaches `USER_INPUT_REQUIRED` for the current item.
- **Scope:** Beam Run Agent Builder payload generation and loop documentation, then a fresh unpublished draft deployment and synthetic batch run. The stalled initial batch task will not receive user input or be resumed.

### Local verification

- Added an offline regression assertion that the shipped variable-loop example serializes both `parentNodeId` and the loop alias on its body node.
- Python compilation, diff validation, and Agent Builder offline suite passed (`34` checks).

### Platform retest result

- The fixed builder's no-write payload contains `nodeConfigurations.alias: work_item` on both execution and condition loop-body nodes. Beam persisted that alias on the condition body but rewrote it to `"1"` on the execution body, and fresh batch task `7fdd281c-281b-4150-bfed-c87ed4d3db32` again paused for `work_item`.
- This is a Beam graph-service/runtime inconsistency. To continue the draft-only diagnostic without MCP or browser writes, add the documented task user-input endpoint to the CLI. It will be used only with fabricated values on paused draft tasks.

## 2026-08-12 — Add CLI support for paused draft-task input

- **Decision:** Add `beam tasks submit-input <taskId> <taskNodeId> <parameter> <answer>` backed by documented `PATCH /agent-tasks/execution/{taskId}/user-input`.
- **Reason:** The CLI already creates and reads draft tasks, but could not operate a safe paused task without falling back to MCP. The Beam API explicitly supports this endpoint.
- **Safety:** This command will submit only the synthetic `work_item` answer to the unpublished validation agent. It does not approve consent or invoke an integration.

### Variable-loop diagnostic result

- `tasks submit-input` successfully resumed the paused draft task. Synthetic iteration 0 completed the accepted branch and iteration 1 completed the rejected branch, proving the condition branches and result nodes behave correctly when supplied a value.
- Beam then recorded `No edges available - flow completed` at the end of each loop-body branch, left the loop container `IN_PROGRESS`, and never advanced to iteration 2 or to the post-loop compiler. The CLI payload and stored graph contained the documented child-to-downstream edges.
- **Decision:** Preserve this task as evidence of two platform-level variable-loop failures—automatic alias injection and loop-body exit/advance—and switch the same unpublished agent to a count-based loop whose body has no inputs. This isolates container iteration from alias binding while retaining independent conditional routes.

## 2026-08-12 — Count-loop fallback probe

- **Topology:** Entry → parse → route. Batch → generate synthetic items → count-based loop (`iterationCount: 3`) → input-free loop-body LLM marker → compile results → condition → one of two explicit batch exits. Single route → single LLM result → explicit single exit.
- **Reason:** It validates loop-container iteration and exit behavior without the broken variable-alias handoff. All nodes remain custom LLM, condition, loop, or exit nodes; no integrations or external action are introduced.
- **Safety:** The agent remains unpublished and the sole task input will be fabricated batch text.

### Pre-deploy defect

- The no-write fallback dry-run revealed that `build_payload_update` reuses condition nodes by their list position and preserves their old objective text. A replacement condition therefore appeared as the removed loop-routing condition even though its edges/configuration had changed.
- **Decision:** Reuse a condition node by matching its objective where possible, retain positional fallback only when no exact match exists, and always update its objective from the new spec. Verify this in the dry-run before deploying.

### Fix verification

- Added a regression test for changing a condition node's objective on a full update. The Agent Builder offline suite now passes `35` checks.
- The production-profile dry-run now shows the intended two condition nodes, the count loop with `iterationCount: 3`, and no stale loop-routing objective. No platform graph write was made during these checks.

### Count-loop deployment

- The fallback deployed successfully as a 12-node unpublished draft and `verify-links` passed. Synthetic batch expectation: the input-free marker runs three times, the compiler receives accumulated markers/items, then the report condition selects an explicit batch exit.

### Count-loop execution result

- Synthetic task `5c191fab-4735-4c06-b8f9-c2b1e58f665b` executed the input-free loop body exactly three times. Each iteration returned `round_marker: count-loop body completed` with iteration counts 1, 2, and 3.
- After the third iteration, Beam left the loop container `IN_PROGRESS`, did not schedule the stored outgoing compiler edge, and ended the task as `STOPPED`. This reproduces the post-loop transition failure without the variable alias or user-input dependency.
- **Conclusion:** The builder serializes and deploys the count loop correctly; the remaining failure is Beam's graph execution service not advancing from a completed loop container to its outgoing edge. No safe Beam Run plugin change can repair that server-side transition. Keep the evidence task and continue testing the independent single-item path.

## 2026-08-12 — User-style correction and revision probe

- **Decision:** Keep the unpublished graph topology unchanged and exercise the working single-item branch with two prompt-only changes: first a correction that defines a case-insensitive exact `READY` rule and rejects `READYISH`, then a revision that standardizes the report as `AUDIT | accepted|rejected | item | reason`.
- **Reason:** This models the normal Agent Builder workflow of initial prompt, correction, and revision while isolating prompt editing and draft-task execution from the independently reproduced loop-runtime defect.
- **Safety:** Both changes target only the disposable validation agent's custom LLM node. All test inputs are fabricated, no integration is configured, and no agent is published.

### Correction result

- Prompt-only update of `Create a synthetic result for a single-item request` verified successfully through the CLI, with `published: false`.
- Synthetic task `98bda9cb-72f8-4f33-88e3-c4266c66a97f` parsed `single ready: lowercase alpha` as a single request, selected the single branch, and returned an accepted `READY` report for `lowercase alpha`, then reached the no-side-effects exit.

### Revision result

- The report-format revision verified successfully through the CLI, still with `published: false`.
- Synthetic boundary task `57e9a2ce-6c57-45bd-87c2-32370b8da7a1` completed end-to-end: it routed through the single branch, rejected `SINGLE READYISH: boundary item`, returned `AUDIT | rejected | SINGLE READYISH: boundary item | exact label rule`, and reached the explicit exit.

## 2026-08-12 — Read-only product verification

- **Decision:** Use the already-open Beam Flow page only to inspect the CLI-written draft. No browser button, form, execute, publish, or graph-edit action was used. A refresh was necessary only because the initially loaded canvas showed the prior variable-loop draft.
- **Result:** After the read-only refresh, the product showed the current count-loop container `Repeat the LLM validation marker exactly three times` and its input-free LLM body `Record Synthetic Validation Round`. The page is marked `Draft` and states that the flow has not been published. No integration node is present.
- **Conclusion:** The initial mismatch was stale client state, not a failed CLI deployment. Product verification now agrees with the CLI-written graph.

### Final local verification

- `sh test/e2e.sh` passed `23/23` offline CLI checks, including the new paused-task-input command and its argument validation.
- `sh test/e2e-agent-builder.sh` passed `35/35` offline Agent Builder checks, including loop alias serialization and condition-objective refresh on graph update.
- `git diff --check` passed with no whitespace errors.

## 2026-08-12 — Align Beam Run loop compilation with the product Builder

- **New evidence:** Reading the Beam API and Agent OS repositories corrects the prior alias diagnosis. Beam API deliberately assigns numeric aliases (`"1"`, `"2"`, …) to loop-body execution nodes for result aggregation; a semantic alias such as `work_item` is neither a loop variable nor a supported runtime contract.
- **Decision:** Remove Beam Run's loop-alias propagation. Port the product Builder's canonical loop-edge normalization: loop-body membership is `parentNodeId`, loop-to-body edges are removed, body-to-outside edges are re-sourced from the loop, and only internal body edges remain inside the subflow.
- **Variable-loop inputs:** A body input that needs the current array element must be a `linked` input to the source array output. Agent OS resolves that link to the current subflow iteration by index. Do not create a `user_fill` input for a conceptual alias.
- **Validation and testing:** Add offline regressions for backend-owned alias stripping, canonical edge shape, and the linked body input. Then deploy a fresh synthetic draft task through the CLI only; browser use is restricted to read-only verification after deployment.
- **Safety:** No integrations, publishing, browser write, or real data are authorized. The disposable validation agent remains the sole graph target.

### Implementation record

- Updated `beam/skills/agent-builder/scripts/beam.py`: loop specs now reject ambiguous or non-array loop modes, strip user-supplied `alias`, and normalize legacy loop/body edges into product-canonical container edges for both create and update payloads.
- Updated `beam/skills/agent-builder/assets/example-specs/loop-article-digest.json` and `beam/skills/agent-builder/references/spec-format.md` to document linked iteration inputs and the canonical edge shape.
- Updated `test/e2e-agent-builder.sh` with assertions for no semantic alias, a linked current-item input, and loop-to-post-loop routing. Added `test/fixtures/complex-linked-loop-validation-agent.json` as the fresh, no-integration variable-loop probe.
- Offline verification after the change: `sh test/e2e-agent-builder.sh` passed 35/35 and `sh test/e2e.sh` passed 23/23. The new probe's CLI dry-run builds an 8-node, 0-integration graph.

### Production draft deployment and fresh test

- Production CLI validation passed for workspace `227e402a-e065-492a-ba26-3934bb9ce929`. The corrected 8-node graph was written only to the existing disposable agent's draft graph (`4b52a7ef-b9cd-4dfd-95d2-2074450fa90d`); CLI verification returned `All links OK` and `published: false`.
- Fresh synthetic draft task `d1426050-ca35-479b-b4e6-acbc177ce76b` (`BEA-T-11`) used only `BATCH READY: alpha; REJECT: beta; READY: gamma`. It completed successfully with no integrations and no user-input pause.
- Evidence from CLI task inspection: the source array was `['alpha', 'gamma']`; the loop body received `work_item='alpha'` at iteration 0 and `work_item='gamma'` at iteration 1 through a linked input; the loop completed both iterations; the post-loop compiler ran and returned `There are 2 verdicts present. Both verdicts are REJECT.` The task status is `COMPLETED`.
- **Conclusion:** The product-canonical linked-input plus loop-to-next-step compilation fixes both observed failures: semantic-alias user-input pauses and failure to advance to the post-loop node. The backend still adds numeric body alias `"1"` as expected internal aggregation metadata.
- **Read-only product verification:** Reloading the already-open Flow page showed `Draft`, `This flow has not yet been published`, and the CLI-written node `Parse Linked Loop Request`. No browser write, execution, or publish action occurred.

### Follow-up synthetic fixture correction

- The first completed run exercised the loop mechanics successfully, but the LLM item-generator filtered the labelled batch to `alpha` and `gamma` despite the fixture instruction to preserve every item. The fixture prompt was tightened to say explicitly not to filter, classify, or omit items; the prompt-only draft update again passed `All links OK` and remained unpublished.
- Follow-up task `971b5500-965b-4672-95f2-0b5ce408588b` (`BEA-T-12`) completed. The model still chose the two actionable items, but the runtime result is unambiguous: both linked inputs were resolved without pause, the loop completed its two iterations, and the post-loop compiler completed. This is an LLM-output-quality limitation of the disposable synthetic parser/classifier, not a loop-graph failure. No production integration, external action, or browser write was used.

## 2026-08-12 — Repair GitHub Actions ShellCheck failure

- **Evidence:** PR #2's `install-test` workflow failed only in the `lint` job. ShellCheck reported SC2015 for two new CLI argument guards and for the intentional `cond && ok || bad` test-accounting idiom in `test/e2e.sh`.
- **Decision:** Replace the production CLI guards with explicit `if` statements. Add a narrowly documented SC2015 directive to the E2E harness, matching the existing Agent Builder E2E harness, because both `ok` and `bad` intentionally return success.
- **Verification:** `shellcheck beam/bin/beam test/smoke.sh test/e2e.sh test/e2e-agent-builder.sh` passes; `sh test/e2e.sh` passes 23/23; `sh test/e2e-agent-builder.sh` passes 35/35; and `git diff --check` passes.

### Follow-up CI finding

- The replacement workflow passed lint but its Ubuntu activation E2E failed only at the file-permission assertion. The test tried BSD `stat -f` before GNU `stat -c`; GNU `stat` accepts `-f` with different meaning, so the fallback never ran.
- **Decision:** Select the BSD or GNU mode command from `uname -s` before asserting mode `600`. The behavior under test is unchanged; this fixes only the test's cross-platform observation.
- **Verification:** ShellCheck remains clean, and both offline suites again pass 23/23 and 35/35 locally. macOS had already passed the same E2E before its matrix sibling failure cancelled the remaining job.
