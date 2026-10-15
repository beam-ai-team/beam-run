# Internal Beam Run implementation material

Not host-discoverable: coding-agent hosts load only the `beam` and `setup` skills
under `beam/skills/`.

- `agent-builder/` holds the builder script the `beam agent-builder` CLI runs, plus
  the authoring references, patterns, lint checklist, example specs and builder evals
  that the build, change and test playbooks in `beam/playbooks/` link to.
