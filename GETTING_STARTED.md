# Getting started with Beam

> This file is written to be handed to your coding agent. Point it here (paste
> the link or the file itself) and ask it to set Beam up for you — installing,
> putting `beam` on PATH, and authenticating are all things the agent can do on
> your behalf by following the steps below.

Build with Beam in your AI coding agent — skills, MCP tools, and the Beam CLI.

## Installation

### Claude Code

How you install depends on **which Claude Code you're using** — this matters, because
the slash commands below exist only in the terminal CLI.

**Desktop app (Mac/Windows):** there is no `/plugin` command. Typing one does nothing
and shows no error. Use the UI instead:

> **+** button next to the prompt box → **Plugins** → **Add plugin** → add the
> marketplace `beam-ai-team/beam-run`, then install **beam**.

**Terminal (`claude` CLI):**

```
/plugin marketplace add beam-ai-team/beam-run
/plugin install beam@beam-plugins
```

Either way, **fully restart** Claude Code afterwards. The desktop app and the CLI share
the same `~/.claude/plugins/` registry, so installing in one shows up in the other.

**No plugin at all?** You don't need one for the MCP tools — install the CLI to a
durable location and let it register itself (you'll miss only the bundled skills):

```
mkdir -p ~/.config/beam-plugin/beam/bin
base=https://raw.githubusercontent.com/beam-ai-team/beam-run/main/beam/bin
curl -fsSL $base/beam        -o ~/.config/beam-plugin/beam/bin/beam
curl -fsSL $base/mcp_proxy.py -o ~/.config/beam-plugin/beam/bin/mcp_proxy.py
chmod +x ~/.config/beam-plugin/beam/bin/beam
~/.config/beam-plugin/beam/bin/beam setup
```

### Codex

```
codex plugin marketplace add beam-ai-team/beam-run
```

Then open **Plugins** and install **beam**.

### Cursor

A plain local copy into `~/.cursor/plugins/local/beam` can silently fail on Teams/Enterprise org
policy — don't guess. Clone the marketplace repo, then hand off to the bundled **`setup` skill**,
which reads the effective policy and picks a path that works (see the skill's own **Cursor
only** step for why and how):

```
git clone https://github.com/beam-ai-team/beam-run.git /tmp/beam-run
```

Then read `/tmp/beam-run/beam/skills/setup/SKILL.md` and follow it like a runbook —
see [Run the `setup` skill](#run-the-setup-skill) below. Once setup finishes, delete the clone
(`rm -rf /tmp/beam-run`) — whichever path the skill picked already copied what it
needs to a permanent location.

## Run the `setup` skill

Once installed, run the bundled **`setup` skill** — when run in a terminal, `beam setup` immediately opens the masked API-key prompt. When an agent or CI runs it without a terminal, it prints the exact next command instead. Either path ends with one restart. Workspace choice stays in the coding-agent conversation: a sole or remembered workspace is automatic, and the agent asks only when the request is genuinely ambiguous.

Installing the plugin wires up the connection, but it can't authenticate you: until you run `beam login`, the Beam server has no key and exposes a single `beam_setup_status` tool that tells your agent exactly what to do next. `beam login` then stores the key and registers the connection with your agent automatically — including the Claude desktop app, which has no `claude` CLI.

**Important — restarting your agent afterward is not optional:** MCP servers resolve credentials at startup. An already-running MCP server won't see a key that was saved after it launched — skipping the restart is the most common reason `beam whoami` looks like it worked but the MCP tools still fail. How you restart is platform-specific; see the skill for the exact steps.

- Try invoking the plugin's `setup` skill directly by its fully qualified name, `beam:setup` — Claude Code's Skill tool supports this, and Codex or Cursor may too depending on version.
- If it doesn't, or the skill doesn't show up right after installing (some platforms don't register a newly installed plugin until restarted), locate `SKILL.md` yourself and follow it like a runbook:

  ```
  find ~/.codex ~/.cursor ~/.claude ~/.config -type f -path '*/skills/setup/SKILL.md' 2>/dev/null | sort | grep -i beam | tail -n1
  ```

  If that prints nothing, use the clone path from the Cursor install step above:
  `/tmp/beam-run/beam/skills/setup/SKILL.md`.

  Read the path that prints and carry out its steps directly.

If something doesn't work, the skill's own **Troubleshooting** table covers the common
symptoms — a plugin that never appears, missing tools after install, and auth failures.

## What's next

Once you're set up, run the bundled **`beam` skill** — it's the entry point for what Beam can do: agents, tasks, graphs, MCP tools, CLI, and the Public API.
