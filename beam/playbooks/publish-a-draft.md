# Publish a draft

## When to use

- "Publish it", "make it live", "push the draft to production", "go live".
- Only when the user clearly asks for it. A build, a change or a passing test is
  never a reason to publish on its own.

## What you need first

- The agent and its `draftGraphId` from `agent.get`. If there is no draft, say so.
- Healthy links on the draft.

## Steps

1. Read `agent.get` for the draft and live graph ids.
2. Check links with `graph.verify-links`. Do not publish a draft with broken links.
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

- Links fail: fix them with `change-an-agents-flow.md` first.
- Publish times out: re-read `agent.get` before trying again.
