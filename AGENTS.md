# Beam Run development

- A plugin change is not complete until its tests pass, it is installed locally
  under a new cache-busted version, and the changed experience is verified in a
  fresh Codex task.
- Configure this repository as the local `beam-run` marketplace while developing.
  Never overwrite an existing plugin cache directory in place.
- Codex Beam operations must remain on the task-scoped CLI path after checkout;
  do not mix them with the shared Beam MCP process.
