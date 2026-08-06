# Design a flow

This is an on-demand design playbook, not a required phase.

Search every named integration before adding it. Confirm its `toolFunctionName`,
required inputs, provider, and consent behavior. Choose the correct node shapes:
execution for processing, condition for exclusive routing, waiting for delayed
work, and looping for a collection.

Use linked params where the upstream output is known and `ai_fill` where input
is free-form or an integration output has no schema. Prefer the cheapest model
that reliably performs the task. Show cost only when it affects the decision or
the user asks.

When the proposed flow is new or materially changed, present its Mermaid diagram
and integration list for natural-language approval.
