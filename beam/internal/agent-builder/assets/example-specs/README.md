# Example Specs

Ready-to-deploy Beam agent specs. Copy one, edit the names/prompts/integrations
for the user's actual goal, and deploy it:

```bash
beam agent-builder deploy assets/example-specs/<file>.json
```

Always run with `--dry-run` first to inspect the generated payload without
calling the API. See `references/spec-format.md` for the full schema.

| File | Pattern shown |
|------|---------------|
| `linear-blog-emailer.json` | Linear flow (entry -> custom node -> integration node). One custom GPT node feeding a Gmail integration via `linked` params. |
| `condition-ticket-router.json` | `conditionNode` (`llm_based`) with three explicit branches including a written catch-all. Downstream nodes link to an upstream node's output. |
| `waiting-email-followup.json` | `waitingNode` (`time_based`) between two integration nodes, plus two Gmail integrations on one spec. |
| `loop-article-digest.json` | `loopingNode` (variable-based) — runs a body node once per item in an upstream array; the body node uses `parent` to mark loop membership. |

These are templates, not finished agents — replace the placeholder topics,
recipients, and prompts with the user's real requirements before deploying.
