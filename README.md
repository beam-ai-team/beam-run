# beam-run

Build with Beam in any AI coding agent — one universal skill, MCP tools, and the
`beam` CLI for Claude Code, Codex, Cursor, and Agent Skills-compatible hosts.

Beam is an AI agent platform — list agents, run tasks, inspect graphs, and
operate workspaces from natural language. This repo is the plugin marketplace
for `beam`: one shared runtime, host-specific manifests, and one CLI.

## Example

```
> List my Beam agents, then create a task on the Customer Support agent:
> "Summarize open tickets from the last 24 hours."

⏺ beam whoami
  user@acme.com · workspace Acme Ops

⏺ listAgents (Beam MCP)
  Customer Support · Sales Outreach · Invoice Matcher

⏺ createAgentTask (Beam MCP)
  agent: Customer Support
  input: Summarize open tickets from the last 24 hours.
  taskId: task_…
```

No Beam UI required for the loop — your agent uses **MCP tools** and the
**`beam` CLI** directly.

## Choose the right Beam surface

Start with the smallest action that fits the job:

| Need | Use |
| --- | --- |
| An existing agent can do the work | **MCP** to create, monitor, approve, or inspect its task |
| An agent's process needs to be created or changed | **Agent builder + CLI** to design, deploy, and explicitly publish its Flow |
| Your application, service, or webhook needs Beam | **Public API** |

Beam Run now exposes one public supervisor skill across every host. It loads only
the compact policy card needed for the request, while retaining the Beam Copilot
baseline as a pinned audit source rather than re-reading raw prompts at runtime.
MCP remains the preferred transport. Every registered operation has a CLI
fallback, so a missing or malformed MCP tool does not abandon the requested work.

The CLI still owns setup, sign-in, workspace selection, diagnostics, and the
stdio bridge. It also provides deterministic fallback commands for tasks,
inbox, integrations, templates, analytics, Views, Learning Hub, agent settings,
and Flow operations. The Public API remains the surface for embedding Beam in
external software.

## Set up

New here? Point your coding agent at **[`GETTING_STARTED.md`](./GETTING_STARTED.md)**
and ask it to set Beam up for you. It walks through installing the plugin,
putting `beam` on PATH, saving an API key locally, and verifying both the CLI and
the MCP server.

**Copy this into your agent:**

```
Set up the Beam plugin by following the steps in
https://github.com/beam-ai-team/beam-run
```

**If you're an agent reading this directly:** read
[`GETTING_STARTED.md`](./GETTING_STARTED.md) and follow it.

If your fetch/open mechanism fails on that link, fetch the raw file:

```
curl -fsSL https://raw.githubusercontent.com/beam-ai-team/beam-run/main/GETTING_STARTED.md
```

Then follow the instructions in that document for your agent environment.

## Docs

- Universal runtime: [`beam/runtime/routes.md`](./beam/runtime/routes.md)
- Copilot baseline and parity: [`beam/references/copilot-baseline/README.md`](./beam/references/copilot-baseline/README.md)
- Supervisor product contract: [`specs/supervisor-product-contract.md`](./specs/supervisor-product-contract.md)
- Supervisor testing plan: [`specs/supervisor-testing-plan.md`](./specs/supervisor-testing-plan.md)
- Beam product / Academy: https://docs.beam.ai
- MCP connection reference: https://docs.beam.ai/08-reference/api/mcp-connection/mcp-connection
- API base: `https://api.beamstudio.ai`
- Auth: API key from Beam → Personal settings → API Keys (`x-api-key` for CLI; Bearer for MCP)
