# Explain how an agent works

## When to use

- "Walk me through the Invoice Matcher", "what triggers it?", "is its Gmail step
  connected?", "what's its webhook URL?", "what changed recently?", "are its links
  healthy?"
- Reading only. Any change goes to `change-an-agents-flow.md`.

## What you need first

- The agent, resolved with `agent.list` (ask if more than one matches).
- Whether the user means the live or the draft version, when both exist.

## Steps

1. Read the agent with `agent.get`: name, model, live and draft graph ids.
2. Read the structure with `graph.nodes`. Use `graph.node` for the steps that
   matter; fetch `graph.get` only when the full graph is truly needed.
3. Explain in order: how it starts (trigger or manual) → each step and what it
   does → branches, waits and loops → how it finishes.
4. As asked:
   - trigger: `graph.triggers` with the entry node id
   - webhook: `graph.webhook`
   - tools and whether their integrations are connected: `agent.tools`, then
     `integration.is-connected` per tool
   - sub-agents: `agent.sub-agents`
   - link health: `graph.verify-links`
   - recent changes: `agent.history`

## Stop and ask

- Nothing here changes anything. No confirmation is needed.

## Done when

- The explanation follows the flow from start to finish, uses the real step names,
  and says which version (live or draft) it describes. Offer a short diagram when the
  flow has branches.

## If it goes wrong

- The user asks to change something: continue with `change-an-agents-flow.md`.
- A webhook URL is shown: remind the user that anyone with it can start runs.
