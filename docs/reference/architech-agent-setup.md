# Architech: first-use setup for people and supervising agents

Read and apply this guide before substantive work. The repository's
[AGENTS.md](../../AGENTS.md) and existing canonical docs remain authoritative;
this guide adds bootstrap instructions, not replacement rules.

## 1. Install and check your own runtime

On macOS or Linux, run the supported installer when setup is authorized:

```sh
curl -fsSL https://api.mutagent.io/architech/install.sh | bash
```

Supply **your own approved email**. The installer asks for email only, not an
access code; not every email is entitled to access. If refused, ask for access
with your identity rather than borrowing someone else's email or credentials.
Use your own OpenAI account and, only if needed, your own cloud account.
Never copy another person's tokens, credential files or authenticated sessions.

If `architech` is missing from PATH, check `~/.local/bin/architech` and use this
current-shell fallback (do not silently modify shell profiles):

```sh
export PATH="$HOME/.local/bin:$PATH"
architech --version
architech --help
architech update --check
# When authorized and an update is available:
architech update
architech doctor
```

`update --check` exits **1 when an update exists**; inspect its message, not just
its exit status. The executable verified for this guide is **0.1.22**, a snapshot,
not a permanent pin. Framework version **0.3.0** is not the executable version.
Check the currently approved runtime and record the actual version at handoff.
If diagnostic output is truncated when piped, capture the full terminal output
instead; redact credentials before sharing. Report concrete failures, not assumed
success. Do not run installation or updates during a task that forbids them.

## 2. Authenticate personally and attach to this checkout

Start the **classic Orchestrator** in the actual owning checkout, not a sibling
repository or workspace umbrella. A separately owned submodule requires its own
authorized session and applicable instructions:

```sh
cd /absolute/path/to/owning-checkout
architech
```

Inside that interactive session:

```text
/login openai-codex
/onboard
/session
```

Complete `/login openai-codex` with **your own** OpenAI browser/device flow before
onboarding. The person performs personal authentication; a supervising agent
prepares concrete setup and asks only for missing authentication or input. Never
invent an identity, copy credentials, or repeatedly ask for already-given approvals.

Tell `/onboard` to **attach to the existing codebase** and preserve canonical
`AGENTS.md`, compatibility instructions and documentation. For an attach-only onboarding, explicitly request `mode=harness` and
`memory_rules=exempt` so existing instructions remain the approved context instead
of generating duplicate rule/memory stacks. Preserve any existing setup plan;
use the supported engine for CLI-owned artifacts only when a change is needed
and authorized. If `.architech/ONBOARD-PLAN.json` is absent in a fresh clone,
state these choices explicitly; do not depend on ignored files or context maps.
Keep the repository's existing tracker; GitHub Projects may be skipped when no
board is selected. Do not invent a board, team ID, or connection.
Do not fan out generated package scaffolds, rewrite established rules, or edit
backend submodules through symlinks. If the repository uses Linear, retain its existing routing and verify the
intended workspace/team before any authorized writes.
A configuration file alone does **not** verify a Linear or cloud connection.

Factory/cloud authentication is separate and optional, never a prerequisite for
local work. No cloud endpoint availability is promised. No cloud-login command
is prescribed here: confirm current supported help before optional setup.

## 3. Let the real Architech session do the work

Actual Architech leads investigation, search, planning, implementation, tests and
fixes, using its specialists when appropriate. The surrounding Codex/Claude/Cursor
agent supervises: relay human scope and binding constraints, launch/resume the
actual process, monitor it, supply bounded host-only tools when needed, return
their evidence to that same session, and independently verify the result.
Reading these instructions or asking Architech for advice once is **not activation**.
If launch/authentication fails, report the blocker; never silently substitute
Codex or another host's execution for Architech's work.

Use `architech`, not `architech agent` or `--prime`, for ordinary orchestrated work.
Keep work tools enabled: do not add `--no-tools`, read-only tool allowlists or
`--no-session` unless explicitly authorized for that purpose.

For an interactive durable launch and later resume:

```sh
cd /absolute/path/to/owning-checkout
architech --session-dir "$HOME/.architech/agent/sessions/my-task"
# Run /session inside Architech; record the actual File and ID it reports.
# Later, from the same checkout, replace this placeholder with that real file:
architech --session "/absolute/path/to/recorded-session.jsonl"
```

After personal authentication, the supervisor can run a noninteractive task:

```sh
cd /absolute/path/to/owning-checkout
architech --print --session-dir "$HOME/.architech/agent/sessions/my-task" "Carry out the authorized task under this repo's applicable instructions and any active delivery holds. Use foreground specialists and wait for all lanes to finish before returning. Report the real session path/id and evidence."
# Reuse the actual saved session file for followups, never a fabricated ID:
architech --print --session "/absolute/path/to/recorded-session.jsonl" "Continue the same task with this binding followup. Use foreground specialists and wait for all lanes to finish before returning."
```

In print mode, verify the actual saved `.jsonl` in the chosen session directory
and its session header (`id` and `cwd`) before recording/resuming it. Do not pick
an unrelated concurrent session. `/session` displays File and ID interactively.
Paths above are placeholders or the new user's own storage, not dependencies on
another checkout or a maintainer's home directory.

Use foreground specialist completion for one-shot runs. Background specialists
require supported durable isolation and verified completion; a saved session
alone does not isolate live children. The supervisor must not exit while
unisolated children still run.

## 4. Verify and hand off honestly

Record the actual executable version, owning checkout, real session path/id,
changed paths, focused validation commands/results and an evidence receipt
(log/terminal capture or independently verified artifact). Distinguish host-only
actions from actual Architech tool calls. Native `agent-trajectory` supports
Pi/Claude sessions, **not native Codex rollouts**. Do not fabricate combined global
percentages, model coverage or a “100% enforced” claim.

Preserve all repository business, source-ownership, authentication, cost/consent
and safety rules. Existing delivery/release holds remain binding until explicitly
lifted; this setup guide authorizes no release, tag, distribution, deployment,
external publication, credential change or paid operation.
Docs-only changes do not prove deployment safety. Local setup/work is not
publication authorization; check live automation and external integrations before
any separately authorized delivery. Locally edited guides are unavailable to
fresh clones until safely reviewed and delivered to their clone source.
