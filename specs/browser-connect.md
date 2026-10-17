# SPEC — Browser Connect for `beam login`

`beam login <workspace URL>` signs the user in through their browser and saves a
Beam Run key for them. Nobody copies an API key. Supersedes the key-first part of
[`api-key-login.md`](api-key-login.md), which stays as the fallback.

## Flow

1. Derive the instance from the URL as before, plus its **app address** (stored as
   `BEAM_APP_URL` in the profile). A typed app address is used as typed; a typed API
   address is mapped (`api.beamstudio.ai` to `app.beam.ai`, `api.staging.beamstudio.ai`
   to `app.staging.beamstudio.ai`, `api.enterprise.beamstudio.ai` to
   `enterprise.beamstudio.ai`, `api.<region>.beamstudio.ai` to `app.<region>.beam.ai`).
   Custom API hosts need `--app-url`. Local development (`BEAM_LOCAL_DEV=1`): the typed
   address is the app, the API is `BEAM_LOCAL_API_URL` (default `http://localhost:4000`).
2. Probe `GET <app>/api/cli/authorize`. `200 {"ok":true,"version":1}` means Connect is
   available. Anything else (including `404`) falls back to the key prompt.
3. `beam login` generates a PKCE verifier and state, starts a one-shot listener on
   `127.0.0.1` (`beam/bin/login_listener.py`, gone after the first callback or 300 s),
   writes `~/.config/beam/pending/<instance-id>` (mode 0600), prints
   `{"ok":true,"status":"waiting","mode":"listener","connectUrl":...}` plus
   `Connect Beam: <url>`, tries to open the browser and exits 0.
4. The browser ends at `http://127.0.0.1:<port>/callback?code=..&state=..` (or
   `?error=..`). The listener checks `state` and records the code or error.
5. `beam login --wait [instance]` returns within about two seconds with one status:
   `waiting`, `connected`, `choose_workspace` (with `workspaces`), `no_workspace`
   (message: "Create a workspace in Beam first: <app address>"; the connection is kept),
   or `failed` (with `reason`, exit 2). On a code it calls `POST <api>/auth/cli/token`,
   saves the profile, picks the only workspace or leaves the choice to `beam checkout`.
6. `beam login --paste` skips the listener (the browser shows a "can't connect" page
   whose address bar holds the result); `beam login --callback '<address>'` finishes
   from that pasted address. A sandbox that refuses even a loopback bind gives
   `{"ok":false,"status":"sandbox_blocked"}` (exit 2): re-run with network access
   approved, or use `--paste`.

## Keys

- Connect keys are marked `BEAM_CONNECT=1` in the profile. `beam logout` and
  `beam login --replace` call `POST <api>/auth/cli/revoke` for those keys first (`401`
  counts as already gone). If Beam cannot be reached the key is still removed locally and
  the CLI prints: Delete the key named 'Beam Run · …' under API keys in Beam.
- Keys the user pasted (`--api-key`, `BEAM_API_KEY`, the prompt) are never revoked.
- The key, verifier and code are never printed. `BEAM_API_KEY`, `--api-key -` and bare
  `--api-key` keep today's behaviour and skip Connect.

## After connecting

The MCP bridge re-reads the saved connection on every message, so no restart is needed.
