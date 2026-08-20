# Beam Copilot prompt baseline

This directory is an exact source snapshot from `beam-agent-os` commit
`40fdd5687a7a4e9122c27d8b175235107c096a58`.

Source root:

`src/mastra/agents/copilot`

The snapshot exists so Beam Run specialists are derived from the product
Copilot's routing, prompt, tool-ownership, and confirmation rules instead of
being independently invented. Do not edit the TypeScript snapshot to adapt it
for a coding-agent host. Put host-specific differences in the relevant
`SKILL.md` and record them in `beam/contracts/copilot-parity.yaml`.

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

Parity has two gates:

1. Source drift: snapshot hashes must remain stable until deliberately refreshed.
2. Behavior: routing, required reads, confirmation, tool choice, and response
   behavior must match the corresponding Copilot specialist after applying the
   documented host adapter.

When the Copilot source is available locally, run `sh test/copilot-source-drift.sh`
to compare every snapshot byte-for-byte with its canonical source. To inspect a
different checkout, set `BEAM_COPILOT_ROOT=/absolute/path/to/beam-agent-os`.
