---
name: cli
description: Beam CLI — agent-oriented commands (JSON output, typed exit codes). Discover login, whoami, workspace, agents list, and mcp proxy usage.
---

# The `beam` CLI

Auth via API key stored in `~/.config/beam/credentials` (or `BEAM_API_KEY`).
Workspace via `BEAM_WORKSPACE_ID` / `beam workspace <id>`.

```bash
beam --help
beam login --api-key <key>
beam whoami
beam workspace                 # show
beam workspace <id>            # set
beam agents list
beam mcp                       # stdio MCP proxy (long-running)
beam logout
```

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | OK |
| 1 | Internal / missing dependency (e.g. no npx/uvx for `mcp`) |
| 2 | Validation |
| 3 | Auth |
| 5 | Network |

Errors print a JSON envelope on stderr: `{"error":{"code":"…","message":"…"}}`.

## Prefer simple commands

Run one plain `beam …` command at a time. Pipe to `jq` when transforming JSON.
Don't print API keys.

## Docs

- Plugin / setup: https://github.com/beam-ai-team/beam-run
- MCP: https://docs.beam.ai/08-reference/api/mcp-connection/mcp-connection
- API base: `https://api.beamstudio.ai`
