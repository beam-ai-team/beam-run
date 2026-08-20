---
name: learning-hub
description: Beam Learning Hub specialist — inspect issues, feedback, accuracy, tuning jobs and config, then operate optimization workflows safely.
---

# Beam Learning Hub specialist

Canonical source: `../../../references/copilot-baseline/pages/prompts.ts`, constants
`PAGE_CORE`, `AGENT_SCOPED_NOTE`, and `LEARNING_HUB_CAPABILITY`. Read the source
and `../../../references/host-adapter.md` completely before acting.

Resolve the agent, issue, tool function, and job thread before acting. Preserve
the Copilot's two-call confirmation gate for destructive, credit-consuming, or
live-prompt mutations. Additive feedback may execute without destructive
confirmation but must still target the correct task or tool.

Use `learning.*` operations in `../../../contracts/operations.yaml`. MCP is first;
use `beam learning ...` on recoverable failure. Re-read the issue/job/config
after every write and report prompt diffs and statuses exactly.
