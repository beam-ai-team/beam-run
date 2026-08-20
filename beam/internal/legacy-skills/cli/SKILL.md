---
name: cli
description: Beam CLI — agent-oriented commands (JSON output, typed exit codes). Discover login, whoami, workspace, agents list, and mcp proxy usage.
---

# The `beam` CLI

Auth via API key stored in `~/.config/beam/credentials` (or `BEAM_API_KEY`).
Workspace via `BEAM_WORKSPACE_ID` / `beam workspace <id>`.

```bash
beam --help
beam setup                     # install + PATH + register + verify (guided)
beam doctor                    # self-diagnose; every red line names its fix
beam login                     # hidden API-key prompt
beam register                  # add Beam as an HTTP MCP server in the host config
beam whoami                    # compact identity/workspace summary
beam whoami --raw              # full profile; use only when explicitly needed
beam workspace                 # show
beam workspace list [search]   # list/search (accounts can have thousands)
beam workspace <id>            # set
beam agents list
beam agents get <id>
beam agents deploy <spec> [--agent-id ID] [--publish] [--dry-run]
beam agents publish <graphId>
beam agents delete <id>        # irreversible — confirm by name first
beam tasks list [flags]
beam tasks create <agentId> <input> [--draft]
beam tasks retry <taskId> [--task-node-id ID --feedback text]
beam tasks approve <taskId> <taskNodeId>
beam tasks reject <taskId> <taskNodeId> [reason]
beam tasks abort <taskId> --confirm <taskId> [--reason text]
beam tasks delete <taskId> --confirm <taskId>
beam tasks rate <taskId> <up|down> [feedback]
beam mcp check [--tool name]    # endpoint/auth/tool inventory health
beam mcp                       # stdio MCP bridge (long-running; hosts spawn it)
beam logout
beam uninstall
```

**Never** run `beam login --api-key <key>` — it leaks the key to shell history.
Use the hidden prompt. Automation may use `BEAM_API_KEY=… beam login` or `--api-key -`.

## Workspace

The key is global and login does not choose a workspace. The CLI keeps a
still-accessible remembered default, auto-selects the only membership, and otherwise
leaves context unset. Use an explicit workspace from the user's request when present.
When multiple workspaces are still possible, ask once, then run
`beam workspace list <search>` and `beam workspace <id>` to remember the answer.
On empty/not-found results, name the active workspace and ask before switching;
never search every workspace or change context silently.

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

For supervisor diagnostics on a read-only operation, set `BEAM_TRACE_TRANSPORT=1`.
The CLI writes a small trace record to stderr without changing the JSON result on stdout.

The supervisor and specialists use CLI commands as deterministic fallbacks, not
only as a setup surface. Use the exact mapping in `../../../contracts/operations.yaml`.
If an individual fallback is marked `planned`, report `blocked-platform` with the
missing operation rather than improvising an unverified API call.

## Docs

- Plugin / setup: https://github.com/beam-ai-team/beam-run
- MCP: https://docs.beam.ai/08-reference/api/mcp-connection/mcp-connection
- API base: `https://api.beamstudio.ai`
