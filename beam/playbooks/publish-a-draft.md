# Publish a draft

## When to use

- "Publish it", "make it live", "push the draft to production", "go live".
- Only when the user clearly asks for it. A build, a change or a passing test is
  never a reason to publish on its own.

## What you need first

- The agent and its `draftGraphId` from `agent.get`. If there is no draft, say so.
- A draft that passes its readiness check.

## Steps

1. Read `agent.get` for the draft and live graph ids.
2. Check the draft with `graph.readiness`. Do not publish while any check fails.
3. Publish with `graph.publish` using the draft graph id.
4. Read back with `graph.get` and `agent.get`.

## Stop and ask

- `graph.publish`: needs a clear request to publish or go live. If the request is
  vague ("ship it?", "looks good"), ask: "Publish the draft of <agent> so live runs
  use it?" Say what changes for live runs and triggers.

## Done when

- `agent.get` shows the published graph as the active graph, and the user is told
  that live runs and any active trigger now use it.

## If it goes wrong

- Readiness fails: fix it with `change-an-agents-flow.md` first.
- Publish times out: re-read `agent.get` before trying again.

## Actions

Generated from `../contracts/operations.yaml`; do not edit by hand. Run each
action through its MCP tool, or its CLI command when MCP is unavailable (always
the CLI in Codex). Re-read with the re-check action after a change.

| Action | MCP tool | CLI | Needs OK | Re-check | Notes |
| --- | --- | --- | --- | --- | --- |
| `agent.get` | `getAgentGraph` | `beam agents get <agentId>` | no | — | Shows activeGraphId (live) and draftGraphId (unpublished). Report the model token exactly as returned. createdAt is the default start date for analytics. |
| `graph.get` | `getAgentGraph` | `beam agent-builder get-graph <agentId>` | no | — | Large (around 136 KB). Prefer graph.nodes for structure; fetch the full graph only for a node id or when the user asks for the whole thing. |
| `graph.publish` | — | `beam agent-builder publish <graphId> --agent-id <agentId>` | explicit-publish-intent | `graph.get` | Makes the draft live. Only on a clear request to publish or go live, and only after graph.readiness passes. |
| `graph.readiness` | — | `beam agent-builder readiness <agentId>` | no | — | Every graph change returns this report. Resolve every failure before testing or publishing. |
