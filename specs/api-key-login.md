# SPEC — API-key login for the `beam` CLI

`beam login` stores a Beam API key locally after validating it against
`GET /v2/user/me`. The user creates the key in Beam → Personal settings → API
Keys and enters it only in their own terminal.

## Supported inputs

```sh
beam login                         # masked terminal prompt
BEAM_API_KEY=… beam login          # automation / CI
printf '%s' "$KEY" | beam login --api-key -  # stdin
```

Never use `beam login --api-key <key>`: command arguments can leak to shell
history and process listings.

## Behaviour

1. Validate the key before saving it.
2. Store credentials with mode `0600`.
3. Keep a remembered workspace only when it is still accessible; automatically
   select the sole workspace and leave multiple workspaces unresolved.
4. Register the MCP server using `Authorization: Bearer <key>`.
5. Tell the user to fully restart their agent because MCP reads credentials at
   startup.

The CLI uses `x-api-key` for Beam API requests; the MCP endpoint uses Bearer
authentication. No browser, callback listener, OAuth endpoint, or Studio
change is part of this flow.
