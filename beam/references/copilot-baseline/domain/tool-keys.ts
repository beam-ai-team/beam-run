export const AGENT_TOOLS = {
  reads: {
    GET: "beam_get_agent",
    SEARCH: "beam_search_agents",
    GET_TOOLS: "beam_get_agent_tools",
    LIST_SUB_AGENTS: "beam_list_sub_agents",
    LIST_CONTEXT_FILES: "beam_list_context_files",
  },
  writes: {
    UPDATE_METADATA: "agent_update_metadata",
    UPDATE_INTERFACE: "agent_update_interface",
    DELETE: "agent_delete",
    REMOVE_TOOLS: "agent_remove_tools",
    UPLOAD_CONTEXT_FILE: "agent_upload_context_file",
    UPLOAD_EXTERNAL_FILE: "agent_upload_external_file",
    TRANSCRIBE_AUDIO: "agent_transcribe_audio",
    DELETE_CONTEXT_FILE: "agent_delete_context_file",
    DELETE_EXTERNAL_FILE: "agent_delete_external_file",
    CHANGE_FILE_AGENT: "agent_change_file_agent",
  },
} as const;

export const GRAPH_TOOLS = {
  reads: {
    GET: "beam_get_agent_graph",
    GET_NODES: "beam_get_nodes",
    GET_NODE: "beam_get_node",
    GET_HISTORY: "beam_get_graph_history",
  },
} as const;

export const TRIGGER_TOOLS = {
  reads: {
    LIST: "beam_get_triggers",
    ACTIONS: "beam_get_trigger_actions",
    WEBHOOK: "beam_get_webhook",
  },
} as const;

export const TASK_TOOLS = {
  reads: {
    LIST: "beam_list_tasks",
    DETAIL: "beamTaskDetailTool",
    GET_LATEST_EXECUTIONS: "beam_get_latest_task_executions",
    GET_STATUSES: "beam_get_task_statuses",
    LIST_AGENTS: "beam_list_task_agents",
  },
  writes: {
    DELETE: "task_delete",
    RETRY: "task_retry",
    CREATE: "task_create",
    SUBMIT_OUTPUT_RATING: "task_submit_output_rating",
    EDIT_NODE: "task_edit_node",
    CANCEL_WAIT_NODE: "task_cancel_wait_node",
    UPDATE_AGENT_TOOL: "task_update_agent_tool",
    ABORT: "task_abort",
  },
} as const;

export const INTEGRATION_TOOLS = {
  reads: {
    LIST: "beam_list_integrations",
    LIST_CATEGORIES: "beam_list_integration_categories",
    LIST_CONNECTED: "beam_list_connected_integrations",
    GET_CONNECTIONS: "beam_get_integration_connections",
    IS_CONNECTED: "beam_is_integration_connected",
  },
  writes: {
    CONNECT: "integration_connect",
    UPDATE_CONNECTION: "integration_update_connection",
    REMOVE_CONNECTION: "integration_remove_connection",
    SET_DEFAULT: "integration_set_default",
    REMOVE_CUSTOM: "integration_remove_custom",
    CREATE_CUSTOM: "integration_create_custom",
    UPDATE_CUSTOM: "integration_update_custom",
  },
} as const;

export const ANALYTICS_TOOLS = {
  reads: {
    AGENT: "beamAgentAnalyticsTool",
  },
  writes: {
    EXPORT: "analytics_export",
  },
} as const;

export const INBOX_TOOLS = {
  reads: {
    GET_UNREAD_COUNT: "beam_get_inbox_unread_count",
    LIST_NOTIFICATIONS: "beam_list_inbox_notifications",
  },
  writes: {
    MARK_READ: "inbox_mark_notification_read",
    DELETE: "inbox_delete_notification",
    APPROVE_CONSENT: "inbox_approve_consent",
    REJECT_CONSENT: "inbox_reject_consent",
    SUBMIT_INPUT: "inbox_submit_input",
  },
} as const;

export const TEMPLATE_TOOLS = {
  reads: {
    LIST: "beam_list_templates",
    GET: "beam_get_template",
    GET_WITH_PREREQS: "beam_get_template_with_prerequisites",
    LIST_CATEGORIES: "beam_list_template_categories",
    GET_RECOMMENDATIONS: "beam_get_agent_recommendations",
  },
  writes: {
    CREATE_AGENT_FROM: "template_create_agent_from",
  },
} as const;

export const VIEW_TOOLS = {
  reads: {
    LIST: "beam_list_views",
    GET: "beam_get_view",
    LIST_RECORDS: "beam_list_view_records",
    LIST_LINKED_RECORDS: "beam_list_linked_records",
  },
  writes: {
    CREATE: "view_create",
    DELETE: "view_delete",
    CREATE_COLUMN: "view_create_column",
    UPDATE_COLUMN: "view_update_column",
    DELETE_COLUMN: "view_delete_column",
    EXPORT_CSV: "view_export_csv",
  },
} as const;

export const SEARCH_TOOLS = {
  reads: {
    GLOBAL: "beam_search",
    TOOLS: "beam_search_tools",
    VERIFY_LINKS: "beam_verify_links",
  },
} as const;

export const USER_TOOLS = {
  reads: {
    GET_CURRENT: "beam_get_current_user",
  },
} as const;
