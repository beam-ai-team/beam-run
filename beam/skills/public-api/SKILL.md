---
name: public-api
description: Beam Public API — HTTP patterns for building services on api.beamstudio.ai (auth headers, user/agents/tasks). Use when integrating Beam outside the coding-agent plugin.
---

# Beam Public API

Base URL: `https://api.beamstudio.ai`

## Auth

Every request:

```
x-api-key: <API_KEY>
```

Most workspace-scoped routes also need:

```
current-workspace-id: <WORKSPACE_ID>
```

Create keys in Beam → Personal settings → API Keys. Keep keys server-side.

## Quick checks

```bash
curl -sS -H "x-api-key: $BEAM_API_KEY" \
  https://api.beamstudio.ai/v2/user/me
```

```bash
curl -sS \
  -H "x-api-key: $BEAM_API_KEY" \
  -H "current-workspace-id: $BEAM_WORKSPACE_ID" \
  "https://api.beamstudio.ai/agent?pageNum=1&pageSize=20"
```

## When to use API vs plugin

| Building… | Use |
| --- | --- |
| Coding-agent workflows | Plugin (MCP + skills + `beam` CLI) |
| Backend jobs, apps, webhooks | Public API |

## Docs

- Overview: https://docs.beam.ai/08-reference/api/overview/overview
- Auth: https://docs.beam.ai/08-reference/api/authentication/authentication
- MCP (separate from REST): https://docs.beam.ai/08-reference/api/mcp-connection/mcp-connection
