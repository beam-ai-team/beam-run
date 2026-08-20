import { LH_READ_TOOL_KEYS, LH_WRITE_TOOL_KEYS } from "../tools/beam-api/learning-hub";
import {
  AGENT_TOOLS,
  ANALYTICS_TOOLS,
  GRAPH_TOOLS,
  INBOX_TOOLS,
  INTEGRATION_TOOLS,
  SEARCH_TOOLS,
  TASK_TOOLS,
  TEMPLATE_TOOLS,
  TRIGGER_TOOLS,
  USER_TOOLS,
  VIEW_TOOLS,
} from "./tool-keys";

export const COPILOT_PAGE_TYPES = [
  "global",
  "home",
  "inbox",
  "tasks.global",
  "templates",
  "integrations",
  "views",
  "agent.flow",
  "agent.tasks",
  "agent.config",
  "agent.analytics",
  "agent.learningHub",
  "agent.learning"
] as const;

export type CopilotPageType = (typeof COPILOT_PAGE_TYPES)[number];

interface CopilotToolBucket {
  writes: readonly string[];
}

const INBOX_WRITES = [
  INBOX_TOOLS.writes.MARK_READ,
  INBOX_TOOLS.writes.DELETE,
  INBOX_TOOLS.writes.APPROVE_CONSENT,
  INBOX_TOOLS.writes.REJECT_CONSENT,
  INBOX_TOOLS.writes.SUBMIT_INPUT,
] as const;

export const TASKS_WRITES = [
  TASK_TOOLS.writes.DELETE,
  TASK_TOOLS.writes.RETRY,
  TASK_TOOLS.writes.CREATE,
  TASK_TOOLS.writes.SUBMIT_OUTPUT_RATING,
  TASK_TOOLS.writes.EDIT_NODE,
  TASK_TOOLS.writes.CANCEL_WAIT_NODE,
  TASK_TOOLS.writes.UPDATE_AGENT_TOOL,
  TASK_TOOLS.writes.ABORT,
] as const;

const TEMPLATES_WRITES = [
  TEMPLATE_TOOLS.writes.CREATE_AGENT_FROM,
] as const;

const INTEGRATIONS_WRITES = [
  INTEGRATION_TOOLS.writes.CONNECT,
  INTEGRATION_TOOLS.writes.UPDATE_CONNECTION,
  INTEGRATION_TOOLS.writes.REMOVE_CONNECTION,
  INTEGRATION_TOOLS.writes.SET_DEFAULT,
  INTEGRATION_TOOLS.writes.REMOVE_CUSTOM,
  INTEGRATION_TOOLS.writes.CREATE_CUSTOM,
  INTEGRATION_TOOLS.writes.UPDATE_CUSTOM,
] as const;

const VIEWS_WRITES = [
  VIEW_TOOLS.writes.CREATE,
  VIEW_TOOLS.writes.DELETE,
  VIEW_TOOLS.writes.CREATE_COLUMN,
  VIEW_TOOLS.writes.UPDATE_COLUMN,
  VIEW_TOOLS.writes.DELETE_COLUMN,
  VIEW_TOOLS.writes.EXPORT_CSV,
] as const;

const AGENT_CONFIG_WRITES = [
  AGENT_TOOLS.writes.UPDATE_METADATA,
  AGENT_TOOLS.writes.DELETE,
  AGENT_TOOLS.writes.UPDATE_INTERFACE,
  AGENT_TOOLS.writes.REMOVE_TOOLS,
  AGENT_TOOLS.writes.UPLOAD_CONTEXT_FILE,
  AGENT_TOOLS.writes.UPLOAD_EXTERNAL_FILE,
  AGENT_TOOLS.writes.TRANSCRIBE_AUDIO,
  AGENT_TOOLS.writes.DELETE_CONTEXT_FILE,
  AGENT_TOOLS.writes.DELETE_EXTERNAL_FILE,
  AGENT_TOOLS.writes.CHANGE_FILE_AGENT,
] as const;

const AGENT_ANALYTICS_WRITES = [
  ANALYTICS_TOOLS.writes.EXPORT,
] as const;

export const COPILOT_TOOL_NAMES: Readonly<Record<CopilotPageType, CopilotToolBucket>> = {
  global: { writes: [] },
  home: { writes: [] },
  inbox: { writes: INBOX_WRITES },
  "tasks.global": { writes: TASKS_WRITES },
  templates: { writes: TEMPLATES_WRITES },
  integrations: { writes: INTEGRATIONS_WRITES },
  views: { writes: VIEWS_WRITES },
  "agent.flow": { writes: [] },
  "agent.tasks": { writes: TASKS_WRITES },
  "agent.config": { writes: AGENT_CONFIG_WRITES },
  "agent.analytics": { writes: AGENT_ANALYTICS_WRITES },
  "agent.learningHub": { writes: LH_WRITE_TOOL_KEYS },
  "agent.learning": { writes: [] }
} as const;

export const COPILOT_READ_TOOL_NAMES = [
  SEARCH_TOOLS.reads.TOOLS,
  AGENT_TOOLS.reads.SEARCH,
  GRAPH_TOOLS.reads.GET_NODES,
  GRAPH_TOOLS.reads.GET_NODE,
  GRAPH_TOOLS.reads.GET,
  AGENT_TOOLS.reads.GET,
  SEARCH_TOOLS.reads.VERIFY_LINKS,
  TRIGGER_TOOLS.reads.ACTIONS,
  TRIGGER_TOOLS.reads.LIST,
  TRIGGER_TOOLS.reads.WEBHOOK,
  TASK_TOOLS.reads.LIST,
  TASK_TOOLS.reads.GET_STATUSES,
  TASK_TOOLS.reads.LIST_AGENTS,
  TASK_TOOLS.reads.GET_LATEST_EXECUTIONS,
  TASK_TOOLS.reads.DETAIL,
  ANALYTICS_TOOLS.reads.AGENT,
  INBOX_TOOLS.reads.LIST_NOTIFICATIONS,
  INBOX_TOOLS.reads.GET_UNREAD_COUNT,
  TEMPLATE_TOOLS.reads.LIST,
  TEMPLATE_TOOLS.reads.GET,
  TEMPLATE_TOOLS.reads.GET_WITH_PREREQS,
  TEMPLATE_TOOLS.reads.LIST_CATEGORIES,
  TEMPLATE_TOOLS.reads.GET_RECOMMENDATIONS,
  INTEGRATION_TOOLS.reads.LIST,
  INTEGRATION_TOOLS.reads.LIST_CATEGORIES,
  INTEGRATION_TOOLS.reads.LIST_CONNECTED,
  INTEGRATION_TOOLS.reads.GET_CONNECTIONS,
  INTEGRATION_TOOLS.reads.IS_CONNECTED,
  VIEW_TOOLS.reads.LIST,
  VIEW_TOOLS.reads.GET,
  VIEW_TOOLS.reads.LIST_RECORDS,
  VIEW_TOOLS.reads.LIST_LINKED_RECORDS,
  AGENT_TOOLS.reads.LIST_CONTEXT_FILES,
  AGENT_TOOLS.reads.LIST_SUB_AGENTS,
  GRAPH_TOOLS.reads.GET_HISTORY,
  AGENT_TOOLS.reads.GET_TOOLS,
  SEARCH_TOOLS.reads.GLOBAL,
  USER_TOOLS.reads.GET_CURRENT,
  ...LH_READ_TOOL_KEYS
] as const;

const COPILOT_WRITE_TOOLS_BY_PAGE: Readonly<Record<CopilotPageType, readonly string[]>> =
  Object.freeze(
    Object.fromEntries(
      COPILOT_PAGE_TYPES.map((p) => [p, COPILOT_TOOL_NAMES[p].writes] as const)
    )
  ) as Readonly<Record<CopilotPageType, readonly string[]>>;

export const COPILOT_ALL_WRITE_TOOL_NAMES: readonly string[] = Array.from(
  new Set(Object.values(COPILOT_WRITE_TOOLS_BY_PAGE).flat())
);

export const COPILOT_TOOL_KEYS = [
  ...COPILOT_READ_TOOL_NAMES,
  ...INBOX_WRITES,
  ...TASKS_WRITES,
  ...TEMPLATES_WRITES,
  ...INTEGRATIONS_WRITES,
  ...VIEWS_WRITES,
  ...AGENT_CONFIG_WRITES,
  ...AGENT_ANALYTICS_WRITES,
  ...LH_WRITE_TOOL_KEYS
] as const;

export type CopilotToolKey = (typeof COPILOT_TOOL_KEYS)[number];
