# Beam Copilot prompt baseline

This directory is an exact source snapshot from `beam-agent-os` commit
`40fdd5687a7a4e9122c27d8b175235107c096a58`.

Source root:

`src/mastra/agents/copilot`

Beam Run no longer copies its instructions from this snapshot: the agent brief and
playbooks are written by hand (see `specs/agent-playbook-architecture.md`). The
snapshot is kept only as a change warning. When Copilot's product rules change,
`test/copilot-source-drift.sh` reports it, and we decide what to carry into the
playbooks or the action list. Never edit the TypeScript snapshot by hand; refresh
it from the source commit and update `SHA256SUMS` together.

Snapshot mapping:

| Snapshot | Agent OS source |
| --- | --- |
| `supervisor/prompt.ts` | `supervisor/prompt.ts` |
| `domain/routing-table.ts` | `_shared/domain/routing-table.ts` |
| `domain/page-tool-subsets.ts` | `_shared/domain/page-tool-subsets.ts` |
| `domain/tool-catalog.ts` | `_shared/domain/tool-catalog.ts` |
| `domain/tool-keys.ts` | `_shared/domain/tool-keys.ts` |
| `general-agent/prompt.ts` | `sub-agents/general-agent/prompt.ts` |
| `builder/prompt.ts` | `sub-agents/builder/prompt.ts` |
| `pages/prompts.ts` | `sub-agents/pages/prompts.ts` |

When the Copilot source is available locally, run `sh test/copilot-source-drift.sh`
to compare every snapshot byte-for-byte with its canonical source. To inspect a
different checkout, set `BEAM_COPILOT_ROOT=/absolute/path/to/beam-agent-os`.
