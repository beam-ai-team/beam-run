# Manage an agent's settings and files

## When to use

- "Rename it", "update its description", "change its starter prompts", "which tools
  does it have?", "remove these tools", "what files does it know?", "add this PDF /
  this URL to its memory", "transcribe this recording", "move that file to the other
  agent", "update the tool's config", "delete this agent".
- Changing the flow itself (steps, prompts, model, trigger) uses
  `change-an-agents-flow.md`.

## What you need first

- The agent, resolved with `agent.list` and read live with `agent.get`. Never answer
  a setting from memory.
- For file actions: the file key or URL, from `agent.files`.

## Steps

1. Read: `agent.get` (settings), `agent.tools` (enabled tools), `agent.sub-agents`,
   `agent.files` (memory files).
2. Act:
   - name, description, suggested prompts, personality, restrictions:
     `agent.update-metadata`
   - remove tools: `agent.remove-tools`
   - a tool's configuration: `task.update-tool`
   - add a local file: `agent.upload-file`; add web pages: `agent.external-files-add`
   - turn audio into text first: `agent.transcribe`
   - move a file to another agent: `agent.change-file-agent`
   - delete files: `agent.context-file-delete`, `agent.external-files-delete`
   - delete the agent: `agent.delete`
3. Re-read with the matching read (`agent.get`, `agent.tools` or `agent.files`).

## Stop and ask

- `agent.remove-tools`: confirm the exact list.
- `agent.context-file-delete`, `agent.external-files-delete`: always confirm,
  naming each file.
- `agent.delete`: always confirm with the agent's exact name and id. It cannot be
  undone, and its runs stop.
- Updates to name, description and prompts need no confirmation.

## Done when

- The re-read shows the new value, list or file set, and the user is told exactly
  what changed.

## If it goes wrong

- Icon or category changes are not available here: say so and link
  `beam://agent.config?agentId=<id>`.
- A file upload fails on size or type: report the actual error.
