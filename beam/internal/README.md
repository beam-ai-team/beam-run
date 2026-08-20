# Internal Beam Run implementation material

This directory preserves the previous supervisor, page-specialist, CLI, MCP, and
agent-builder skill material during the universal-runtime migration. It is not in
the public `beam/skills/` discovery path, so coding-agent hosts load only the
universal `beam` skill and the existing `setup` skill.

- `agent-builder/` keeps builder scripts, authoring references, examples, and evals
  used by the Beam CLI and by the generated `agent-builder` runtime policy.
- `legacy-skills/` keeps the former host-specialist instructions as migration and
  audit material. They are not normal runtime dependencies.

The pinned Beam Copilot baseline in `beam/references/copilot-baseline/` remains
the product source of truth. Run `python3 beam/scripts/compile_runtime_policy.py`
after a deliberate baseline or operation-contract change.
