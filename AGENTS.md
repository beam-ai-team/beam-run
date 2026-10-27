## First use: Architech setup and execution

Before substantive work, read and apply the [portable Architech setup guide](docs/reference/architech-agent-setup.md), then launch or resume actual Architech in this owning checkout. Reading instructions is not activation.

- **Architech's classic Orchestrator leads** investigation/search, planning, implementation, tests and remediation, using its own authorized specialists.
- The outer Codex/Claude/Cursor host **supervises**: relay human intent and binding rules, launch/resume, monitor, independently verify and report. A token consultation does not transfer execution to the host.
- Bounded bootstrap/safety checks and host-only connector/UI actions are allowed when needed: return their evidence to the same Architech session, then continue with Architech as lead. Higher-priority instructions and explicit human exceptions prevail.
- Use classic `architech`, durable `--session` storage and the actual owning checkout. Record the real session path/id and actual executable version, not the framework version. If launch, authentication or a required capability fails, report the concrete blocker; never silently substitute host execution.
- One-shot specialists must complete in the foreground, or use supported durable isolation with verified completion. A saved session alone does not isolate running children.
- Existing repository business/product rules, source ownership, tracker, authentication, cost/consent and delivery gates below remain canonical. Bootstrap does not authorize installs, paid calls, credential changes, external writes, commits, deployments or releases. Distinguish host actions from actual Architech tool calls in evidence.

# Beam Run development

- A plugin change is not complete until its tests pass, it is installed locally
  under a new cache-busted version, and the changed experience is verified in a
  fresh Codex task.
- Configure this repository as the local `beam-run` marketplace while developing.
  Never overwrite an existing plugin cache directory in place.
- Codex Beam operations must remain on the task-scoped CLI path after checkout;
  do not mix them with the shared Beam MCP process.
