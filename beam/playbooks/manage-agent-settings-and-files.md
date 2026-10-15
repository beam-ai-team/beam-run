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

## Actions

Generated from `../contracts/operations.yaml`; do not edit by hand. Run each
action through its MCP tool, or its CLI command when MCP is unavailable (always
the CLI in Codex). Re-read with the re-check action after a change.

| Action | MCP tool | CLI | Needs OK | Re-check | Notes |
| --- | --- | --- | --- | --- | --- |
| `agent.change-file-agent` | `agent_change_file_agent` | `beam agents change-file-agent <agentId> <payloadFile>` | no | — | — |
| `agent.context-file-delete` | `agent_delete_context_file` | `beam agents context-file-delete <agentId> <fileKey> --confirm <fileKey>` | always | `agent.files` | — |
| `agent.delete` | — | `beam agents delete <agentId> --confirm <agentId>` | explicit-agent-name-and-id | `agent.list` | Irreversible. Confirm with the agent's exact name and id. |
| `agent.external-files-add` | `agent_upload_external_file` | `beam agents external-files-add <agentId> <payloadFile>` | no | `agent.files` | — |
| `agent.external-files-delete` | `agent_delete_external_file` | `beam agents external-files-delete <agentId> <payloadFile> --confirm <agentId>` | always | `agent.files` | — |
| `agent.files` | `beam_list_context_files` | `beam agents files <agentId>` | no | — | The result is a list whose first entry holds the files. |
| `agent.get` | `getAgentGraph` | `beam agents get <agentId>` | no | — | Shows activeGraphId (live) and draftGraphId (unpublished). Report the model token exactly as returned. createdAt is the default start date for analytics. |
| `agent.list` | `listAgents` | `beam agents list` | no | — | When more than one agent matches a name, ask which one; never pick by display name alone. |
| `agent.remove-tools` | `agent_remove_tools` | `beam agents remove-tools <agentId> <payloadFile> --confirm <agentId>` | explicit | `agent.tools` | Show the exact list first; removing more than five always needs a second look. |
| `agent.sub-agents` | `beam_list_sub_agents` | `beam agents sub-agents <agentId>` | no | — | — |
| `agent.tools` | `beam_get_agent_tools` | `beam agents tools <agentId>` | no | — | Report toolName, description and requiresConsent per tool. Each tool's toolFunctionName is the key for integration.is-connected. |
| `agent.transcribe` | `agent_transcribe_audio` | `beam agents transcribe <localAudioFile>` | no | — | — |
| `agent.update-metadata` | `agent_update_metadata` | `beam agent-builder update-metadata <agentId> ...` | no | `agent.get` | Changes name, description, suggested prompts, personality and restrictions. The model of a step changes with graph.update-node; the agent's icon and category cannot be changed from here, so say so and link beam://agent.config?agentId=<id>. |
| `agent.upload-file` | `agent_upload_context_file` | `beam agents upload-file <agentId> <localFile>` | no | `agent.files` | — |
| `task.update-tool` | `task_update_agent_tool` | `beam tasks update-tool <toolFunctionName> <payloadFile>` | no | `agent.tools` | — |
| `user.current` | `getCurrentUser` | `beam whoami` | no | — | Gives the user id that Learning Hub writes need. Never invent a user id. |
