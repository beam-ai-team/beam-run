import { type CopilotPageType } from "./tool-catalog";

export const SUB_AGENT_GENERAL = "beamAgent";
export const SUB_AGENT_GRAPH_BUILDER = "agentSetup";
export const SUB_AGENT_AGENT_TASKS = "pageAgentTasks";
export const SUB_AGENT_TASKS_GLOBAL = "pageTasksGlobal";
export const SUB_AGENT_AGENT_FLOW = "pageAgentFlow";
export const SUB_AGENT_INTEGRATIONS = "pageIntegrations";
export const SUB_AGENT_AGENT_CONFIG = "pageAgentConfig";
export const SUB_AGENT_AGENT_ANALYTICS = "pageAgentAnalytics";
export const SUB_AGENT_INBOX = "pageInbox";
export const SUB_AGENT_TEMPLATES = "pageTemplates";
export const SUB_AGENT_VIEWS = "pageViews";
export const SUB_AGENT_LEARNING_HUB = "pageLearningHub";

export type SupervisorTarget =
  | typeof SUB_AGENT_GENERAL
  | typeof SUB_AGENT_GRAPH_BUILDER
  | typeof SUB_AGENT_AGENT_TASKS
  | typeof SUB_AGENT_TASKS_GLOBAL
  | typeof SUB_AGENT_AGENT_FLOW
  | typeof SUB_AGENT_INTEGRATIONS
  | typeof SUB_AGENT_AGENT_CONFIG
  | typeof SUB_AGENT_AGENT_ANALYTICS
  | typeof SUB_AGENT_INBOX
  | typeof SUB_AGENT_TEMPLATES
  | typeof SUB_AGENT_VIEWS
  | typeof SUB_AGENT_LEARNING_HUB;

export type SupervisorRoutingRow = {
  pageType: CopilotPageType | "*";
  target: SupervisorTarget;
  handles: string;
};

export const SUPERVISOR_ROUTING_TABLE: readonly SupervisorRoutingRow[] = [
  {
    pageType: "home",
    target: SUB_AGENT_GENERAL,
    handles:
      "The Beam AI home — handled by the general workspace assistant, the same way any unscoped page is. Answers broad and open-world questions (current events, news, and anything needing a live web search), plans and explains, answers Beam product and how-to questions from Beam's documentation, searches the user's agents and recent activity, surfaces connected integrations and inbox items, recommends templates, and owns turns involving connected external integrations. It also owns the user's sandboxed cloud workspace — creating and managing projects, building and running skills, executing code/scripts, and reading/writing/searching their files. Creating a brand-new agent happens here ONLY when the Build agents toggle is on (see the agent-creation rule)."
  },
  {
    pageType: "agent.tasks",
    target: SUB_AGENT_AGENT_TASKS,
    handles:
      "One agent's task history. Lists and filters that agent's runs, reads a task's full execution trace, reports the agent's analytics, and acts on its tasks — retry (including retry-from-a-failed-node), delete, abort, cancel a waiting node, start a new task, rate output, edit a node, update a tool config."
  },
  {
    pageType: "tasks.global",
    target: SUB_AGENT_TASKS_GLOBAL,
    handles:
      "The workspace-wide task list spanning every agent. Lists, filters, and explains tasks across all agents and performs the same task actions as the single-agent tasks page, resolving the target agent or task by searching first."
  },
  {
    pageType: "agent.flow",
    target: SUB_AGENT_AGENT_FLOW,
    handles:
      "Reading or explaining an agent's flow graph — its nodes, configuration, edges, link health, triggers, webhook, sub-agents, enabled tools, history, and settings, plus whether an integration is connected. Building or editing the graph (add/remove a node, change a node's tool, prompt, or parameters, change a trigger or webhook, deploy, publish) goes to the agent-building specialist instead."
  },
  {
    pageType: "integrations",
    target: SUB_AGENT_INTEGRATIONS,
    handles:
      "The workspace's third-party integration connections. Browses the catalog, reports what is connected and each connection's status, lists a provider's connections, and checks whether the integration behind a tool is connected. Acts on connections — add a credential-based connection, rename, set default, remove (with confirmation) — and creates, updates, or removes custom integrations. Interactive OAuth connects are linked out to the UI; it cannot enumerate which agents use an integration."
  },
  {
    pageType: "agent.config",
    target: SUB_AGENT_AGENT_CONFIG,
    handles:
      "One agent's configuration. Reports its model, instructions, suggested prompts, enabled tools and integrations, category, intro/setup messages, sub-agents, triggers, and webhook from a live fetch; manages its context/memory files; bulk-removes enabled tools; and deletes the agent (with confirmation). It can update the agent's name, description, and suggested prompts; switching the model or changing avatar, category, personality, or restrictions is not available from chat (it declines and links out). Graph, trigger, and webhook edits go to the agent-building specialist."
  },
  {
    pageType: "agent.analytics",
    target: SUB_AGENT_AGENT_ANALYTICS,
    handles:
      "One agent's performance over a date range — total/completed/failed task counts, average and total runtime, average evaluation score, feedback counts, consent-required counts, the period-over-period change for each, and a task-and-evaluation chart. Drills into the runs behind a metric, correlates a dip with graph-change history, and exports the analytics as a shareable file. Defaults the range from the agent's creation date to today; it cannot change the on-screen date range."
  },
  {
    pageType: "inbox",
    target: SUB_AGENT_INBOX,
    handles:
      "The notification inbox. Triages notifications about agent tasks, resolves the underlying task and reads its trace to explain why the user was pinged or classify a failure, marks notifications read and deletes them (single, by parent, or sweep), and resolves an agent's parked checkpoints — approve or reject a consent request, or supply the values a task is waiting on — confirming before approving a gated action or rejecting. When a checkpoint needs a value to be inferred from the agent's own memory, that turn goes to the general workspace assistant (which holds the memory-search tool); route it there, then return its proposed value for the user to confirm."
  },
  {
    pageType: "templates",
    target: SUB_AGENT_TEMPLATES,
    handles:
      "The agent template gallery. Searches and filters templates and recommends one for a stated goal, explains a template's flow and tools, reports which integrations a template requires and which are not yet connected, compares two templates, and creates a new agent from a template (fetching its graph first) before linking the new agent's flow. It cannot list which existing agents came from a given template."
  },
  {
    pageType: "views",
    target: SUB_AGENT_VIEWS,
    handles:
      "Saved data Views (tables over agent records). Lists views, explains a view's column schema, reads its rows with filtering/sorting/field selection, follows link columns, creates or deletes a view (with confirmation), edits or deletes columns, and exports to CSV. It cannot create, edit, or delete the rows inside a view — only the agent's runs write record data — so it declines row edits and points to the agent's flow; a node-mapped column it cannot reliably resolve is deferred to the column builder rather than guessed."
  },
  {
    pageType: "agent.learningHub",
    target: SUB_AGENT_LEARNING_HUB,
    handles:
      "One agent's Learning Hub — the tool-tuner surface. Reports state (issues per tool with bucket, feedbacks per issue, job history + detail with prompt-before/after and failureReason, per-tool accuracy rollups, daily accuracy trend, tuner config) AND performs actions (submit per-node feedback or task-level feedback with LLM mapper; merge same-tool issues; dispatch tuner optimization job on an issue; discard an issue; approve/reject/re-optimize/cancel/run a job; bulk-resume on-hold jobs; upsert tuner config). Destructive and credit-consuming writes use a two-call confirmation gate — the first invocation (with `confirmed:false`) returns a chat-ready confirmation message that the specialist forwards to the user; on user approval, the specialist re-invokes with `confirmed:true` to execute. Additive writes (submit_feedback, submit_task_feedback) auto-execute."
  },
  {
    pageType: "agent.learning",
    target: SUB_AGENT_LEARNING_HUB,
    handles:
      "Learning Hub landing (studio-v2 alias: `/learning`) — same tool surface as `agent.learningHub`. FE sends this pageType from the `/learning` route family, so it needs to reach the same specialist."
  },
  {
    pageType: "*",
    target: SUB_AGENT_GENERAL,
    handles:
      "The general workspace assistant — and the catch-all for anything no page specialist owns. Besides the workspace-wide read pool (the user's agents and recent activity) and turns involving the user's connected external integrations (Gmail, Slack, or any other Pipedream-connected tool), it holds LIVE WEB SEARCH and answers open-world questions — current events, news, market/competitor research, 'what is X', and any general-knowledge or look-it-up-online request — plus Beam product and how-to questions from Beam's documentation. It also owns the user's sandboxed cloud workspace — projects, skills, code/script execution, and file management. Route here every turn that is not specifically about the in-focus page's own data, including a value-inference (memory-search) sub-task handed off from another page. Unrecognized pages route here too."
  }
] as const;

export function resolveTargetForPage(pageType: string | null | undefined): SupervisorTarget {
  const row = SUPERVISOR_ROUTING_TABLE.find((r) => r.pageType === pageType);
  return row ? row.target : SUB_AGENT_GENERAL;
}

export function isBuilderAllowedForPage(
  pageType: string | null | undefined,
  buildMode?: boolean
): boolean {
  // agent.flow → edit the in-focus agent's graph. home + buildMode → create a brand-new agent
  // (the "Build agents" pill is on). Creation is forbidden everywhere else.
  return pageType === "agent.flow" || (pageType === "home" && buildMode === true);
}

export const DELEGATION_TOOL_PREFIX = "agent-";

export function delegationToolName(target: SupervisorTarget): string {
  return `${DELEGATION_TOOL_PREFIX}${target}`;
}

const TARGET_AGENT_ID: Record<SupervisorTarget, string> = {
  [SUB_AGENT_GENERAL]: "beam-agent",
  [SUB_AGENT_GRAPH_BUILDER]: "beam-agent-builder",
  [SUB_AGENT_AGENT_TASKS]: "beam-page-agent-tasks",
  [SUB_AGENT_TASKS_GLOBAL]: "beam-page-tasks-global",
  [SUB_AGENT_AGENT_FLOW]: "beam-page-agent-flow",
  [SUB_AGENT_INTEGRATIONS]: "beam-page-integrations",
  [SUB_AGENT_AGENT_CONFIG]: "beam-page-agent-config",
  [SUB_AGENT_AGENT_ANALYTICS]: "beam-page-agent-analytics",
  [SUB_AGENT_INBOX]: "beam-page-inbox",
  [SUB_AGENT_TEMPLATES]: "beam-page-templates",
  [SUB_AGENT_VIEWS]: "beam-page-views",
  [SUB_AGENT_LEARNING_HUB]: "beam-page-learning-hub"
};

export function targetAgentId(target: SupervisorTarget): string {
  return TARGET_AGENT_ID[target];
}

export function renderRoutingTable(): string {
  const rows = SUPERVISOR_ROUTING_TABLE.map((row) => {
    const page = row.pageType === "*" ? "any other page (and unrecognized pages)" : row.pageType;
    return `- page \`${page}\` → \`${delegationToolName(row.target)}\`: ${row.handles}`;
  }).join("\n");
  return rows;
}
