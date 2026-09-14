# SPEC — API-key login for the `beam` CLI

`beam login` takes a Beam workspace URL, then stores an API key locally after
validating it against that instance's `GET /v2/user/me`. The user enters the key
only in their own terminal.

## Supported inputs

```sh
beam login                                      # URL, masked key, workspace
BEAM_WORKSPACE_URL=… BEAM_API_KEY=… beam login  # automation / CI
printf '%s' "$KEY" | beam login --url "$WORKSPACE_URL" --api-key -
```

Never use `beam login --api-key <key>`: command arguments can leak to shell
history and process listings.

## Behaviour

1. Require a workspace URL; never assume Beam App.
2. Derive the instance as Beam App, Beam Enterprise, or Beam `{Region}`.
3. Reject an already-connected instance unless `--replace` was requested.
4. Validate the key before saving it with mode `0600`.
5. Let the user select a workspace or create one in the chosen instance.
6. Lock the instance and workspace for the current session.
7. Preserve legacy credentials until a verified profile has been written.
8. Register the MCP server using `Authorization: Bearer <key>`.

Regional workspace hosts follow `app.{region}.beam.ai`; Beam Run derives the API
origin as `api.{region}.beamstudio.ai`, so adding a region requires no registry
change in Beam Run.

The CLI uses `x-api-key` for Beam API requests; the MCP endpoint uses Bearer
authentication. No callback listener, OAuth endpoint, instance registry, or
Studio change is part of this flow.
