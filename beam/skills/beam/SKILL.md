---
name: beam
description: Beam — start here. Table of contents for working with Beam Core — agents, tasks, graphs, MCP tools, the CLI, and the Public API. Read this first to answer "what can I do with Beam?"
---

# Working with Beam

Beam is an AI agent platform: build and run agents, execute tasks, inspect workflow
graphs, and operate workspaces. This skill is a table of contents — find what you
want and open that skill.

## How to work

- **Narrate as you go.** Say what you're about to do and why, then what happened —
  in plain language, using agent/task names the user recognizes.
- **Summarize, don't dump.** Turn raw JSON into a short takeaway or table. Reserve
  raw output for when the user asks.
- **Confirm the workspace once.** First use in a session: run `beam whoami` and tell
  the user which user/workspace you're on. If wrong, `beam workspace <id>` or
  re-run `beam login`. If whoami fails on auth, run the `setup` skill.

## Answering "what can I do with Beam?"

Describe **Beam's product**, not your own abilities:

- Say "Beam lets you…" / "you can…", not "skills I have."
- Lead with concrete outcomes, then offer to run one:
  - "List the agents in my workspace and show which ones ran today."
  - "Create a task on the Customer Support agent with this brief…"
  - "Show the workflow graph for Invoice Matcher and highlight the consent nodes."
  - "Monitor a running task and approve it when it asks for consent."
  - "Pull analytics for an agent over the last 7 days."

## Choose the right Beam action first

Before choosing a technical surface, choose the smallest Beam action that fits:

| Need | Start with |
| --- | --- |
| An existing agent can do the work | Create and monitor a task on that agent |
| No existing agent fits, or its process must change | Build or update its Flow with `agent-builder` |
| Your own app, backend, or webhook must call Beam | Use the Public API |

Do not create a new agent when an existing agent can complete the requested task.

## Choose the right technical surface

| Surface | What it's for |
| --- | --- |
| **MCP tools** | Default in-editor surface: run, monitor, approve, and inspect existing agent work |
| **CLI (`cli` skill)** | Authentication, workspace administration, scripts, and Flow deployment/publishing |
| **Public API (`public-api` skill)** | Building services, apps, and webhooks on `https://api.beamstudio.ai` |

Escalation order:

1. **MCP** — prefer for interactive agent/task work inside the coding agent.
2. **CLI** — prefer for auth checks, workspace switching, and simple scripts.
3. **Public API** — when building an integration, backend, or non-agent client.

If auth fails or tools are missing, run **`setup`** before anything else.

## Related skills

- `setup` — install plugin, PATH, API key, MCP verify, restart
- `agents` — list/inspect agents and graphs
- `tasks` — create, monitor, approve/reject tasks
- `mcp` — what MCP tools exist and when to use them
- `cli` — `beam` command reference
- `public-api` — HTTP API patterns and auth
