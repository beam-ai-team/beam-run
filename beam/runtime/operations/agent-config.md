# Beam Run operations — agent-config

Generated from `beam/contracts/operations.yaml`. Prefer MCP; on an unavailable or malformed tool, use the mapped CLI command. Reconcile an ambiguous write before retrying.

| Operation | Safety | MCP | CLI fallback | Confirmation | Verify |
| --- | --- | --- | --- | --- | --- |
| agent.get | read | getAgentGraph | `beam agents get <agentId>` | none | not-required |
| agent.delete | destructive-write | null | `beam agents delete <agentId> --confirm <agentId>` | explicit-agent-name-and-id | agent.list |
| agent.tools | read | beam_get_agent_tools | `beam agents tools <agentId>` | none | not-required |
| agent.sub-agents | read | beam_list_sub_agents | `beam agents sub-agents <agentId>` | none | not-required |
| agent.files | read | beam_list_context_files | `beam agents files <agentId>` | none | not-required |
| agent.history | read | beam_get_graph_history | `beam agents history <agentId>` | none | not-required |
| agent.update-metadata | reversible-write | agent_update_metadata | `beam agent-builder update-metadata <agentId> ...` | none | agent.get |
| agent.remove-tools | destructive-write | agent_remove_tools | `beam agents remove-tools <agentId> <payloadFile> --confirm <agentId>` | explicit | agent.tools |
| agent.external-files-add | reversible-write | agent_upload_external_file | `beam agents external-files-add <agentId> <payloadFile>` | none | agent.files |
| agent.upload-file | reversible-write | agent_upload_context_file | `beam agents upload-file <agentId> <localFile>` | none | agent.files |
| agent.context-file-delete | destructive-write | agent_delete_context_file | `beam agents context-file-delete <agentId> <fileKey> --confirm <fileKey>` | always | agent.files |
| agent.external-files-delete | destructive-write | agent_delete_external_file | `beam agents external-files-delete <agentId> <payloadFile> --confirm <agentId>` | always | agent.files |
| agent.change-file-agent | reversible-write | agent_change_file_agent | `beam agents change-file-agent <agentId> <payloadFile>` | none | not-required |
| agent.transcribe | read | agent_transcribe_audio | `beam agents transcribe <localAudioFile>` | none | not-required |
| task.update-tool | reversible-write | task_update_agent_tool | `beam tasks update-tool <toolFunctionName> <payloadFile>` | none | agent.tools |
