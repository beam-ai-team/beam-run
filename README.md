# beam-run

Build with Beam in your AI coding agent — skills, MCP tools, and the `beam`
CLI, for Claude Code, Codex, and Cursor.

Beam is an AI agent platform — list agents, run tasks, inspect graphs, and
operate workspaces from natural language. This repo is the plugin marketplace
for `beam`: one plugin source, three coding-agent targets, sharing one set of
skills and one CLI.

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

This keeps Beam Run simple: MCP operates live agent work, the CLI administers and
deploys Beam assets, and the API embeds Beam in software.

## Set up

New here? Point your coding agent at **[`GETTING_STARTED.md`](./GETTING_STARTED.md)**
and ask it to set Beam up for you. It walks through installing the plugin,
putting `beam` on PATH, saving your API key, and verifying both the CLI and
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

- Beam product / Academy: https://docs.beam.ai
- MCP connection reference: https://docs.beam.ai/08-reference/api/mcp-connection/mcp-connection
- API base: `https://api.beamstudio.ai`
- Auth: `x-api-key` header (create a key in Beam → Personal settings → API Keys)
