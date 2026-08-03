# SPEC — Browser login for the `beam` CLI

**Status:** proposal · **Owner:** Beam platform + beam-run · **Supersedes:** the
"OAuth is a future iteration" note in `TESTING.md`

Replace "paste an API key into a terminal" with "approve it in the browser you
already have open". Most of the work is server-side; the CLI change is small.

---

## 1. Problem

Signing in is the only step in the whole install that forces the user out of
their coding agent, and it is the step most likely to strand them.

Three things collide:

1. **`beam login` needs a real TTY.** It gates the masked prompt on `[ -t 0 ]`
   (`beam/bin/beam`). Tool shells inside Claude Code, Cursor and Codex are not
   TTYs, so the prompt is unreachable and the command exits 3. The user must
   open a separate terminal, then come back.
2. **The agent must not handle the key.** Even with a working TTY, an agent
   typing the user's API key would put a long-lived credential into the chat
   transcript. beam-run's own `setup` skill forbids it. This is a boundary we
   *want*, so the fix cannot be "let the agent do it".
3. **Workspace selection is unsolved at the CLI.** After `beam login` the user
   still has to pick a workspace. Real accounts are large — the account this was
   tested on has **2596** — so a terminal list is a poor picker, and guessing is
   worse (it used to auto-select `workspaces[0]`, dropping users into an
   unrelated workspace whose agent list looked empty).

A browser flow fixes all three: no TTY needed, no secret passes through the
agent, and the workspace picker becomes a normal web UI.

---

## 2. Goals / non-goals

**Goals**
- `beam login` completes without a TTY, so an agent can start it in-place.
- No secret is ever typed into, or visible to, the coding agent.
- The user picks their workspace during login, in a UI that can search.
- Existing non-interactive paths keep working unchanged (CI, scripting).

**Non-goals**
- Replacing API keys. They remain the credential for REST and `/mcp`.
- SSO/SAML federation. Orthogonal; do not couple to this.
- Changing how the MCP server is registered with a host.

---

## 3. Chosen flow: OAuth 2.0 Device Authorization Grant (RFC 8628)

Device code, not a loopback redirect.

| | Device code (RFC 8628) | Loopback redirect (RFC 8252) |
|---|---|---|
| Needs a local HTTP listener | no | yes |
| Works over SSH / in a container / headless | **yes** | no |
| Works when an agent spawns the process | **yes** | fragile |
| Browser can be on a different device | **yes** | no |
| Clicks for the user | one extra (enter code) | fewer |

The extra code entry is worth it: beam-run installs are frequently driven by an
agent, sometimes on a remote box, and a loopback listener is exactly what fails
in those environments. Add loopback later as an opportunistic fast path
(§8), keeping device code as the fallback.

---

## 4. Server work (Beam platform)

Three endpoints and one page. Naming follows RFC 8628 so any standard client
library works.

### `POST /auth/device/code`
Request: `{ "clientId": "beam-cli", "scope": "workspace:read agents:write" }`

```json
{
  "deviceCode": "…opaque, 32+ bytes…",
  "userCode": "BEAM-7Q4X",
  "verificationUri": "https://app.beam.ai/activate",
  "verificationUriComplete": "https://app.beam.ai/activate?code=BEAM-7Q4X",
  "expiresIn": 600,
  "interval": 5
}
```

- `userCode`: short, unambiguous alphabet (no `0/O`, `1/I/l`), ~8 chars, single
  use, TTL ≤ 10 min.
- `deviceCode` is the secret; never display it.

### `POST /auth/device/token`
Request: `{ "clientId": "beam-cli", "deviceCode": "…" }`

Poll. Errors use RFC 8628 codes so the CLI can branch without string matching:

| Response | CLI behaviour |
|---|---|
| `authorization_pending` | keep polling at `interval` |
| `slow_down` | increase interval by 5s |
| `access_denied` | stop, exit 3, tell the user they declined |
| `expired_token` | stop, exit 3, tell them to re-run `beam login` |
| success | store credential, print the workspace, exit 0 |

Success payload — **this is the important design decision:**

```json
{
  "apiKey": "…long-lived, scoped, named…",
  "workspaceId": "227e402a-…",
  "workspaceName": "Saqib",
  "keyName": "Claude Code on Saqibs-MacBook"
}
```

**Return a named API key, not a short-lived access token.** Rationale: the
preferred MCP registration writes a **static** `Authorization: Bearer <key>`
header into the host's config (`~/.claude.json`, `~/.cursor/mcp.json`). Nothing
re-reads that header, so a 1-hour token would silently break every MCP tool an
hour after login — the worst possible failure mode, because it looks like the
product broke rather than the session expiring.

`POST /auth/access-token` already exchanges an API key for `idToken` +
`refreshToken`, so short-lived tokens remain available to anything that can
refresh (the stdio bridge, JWT-gated routes like agent delete). Keep that split:
**long-lived key at rest, short-lived JWT minted on demand.**

The key must be:
- named after the host (`Claude Code on <hostname>`) so users can tell devices apart;
- listed and revocable under Personal settings → API Keys;
- scoped to the workspace chosen during approval.

### `POST /auth/device/revoke` (optional, v1.1)
Lets `beam logout` revoke server-side instead of only deleting the local file.

### Page: `app.beam.ai/activate`
1. Authenticate with the user's existing session (or prompt).
2. Show the code and the requesting device name; require an explicit **Approve**.
3. **Workspace picker with search** — this is where the 2596-workspace problem
   is actually solved. Default to their most recently used workspace.
4. Show granted scopes and that a named API key will be created.

Accept `?code=` prefilled from `verificationUriComplete`.

---

## 5. CLI work (this repo)

```
beam login                 # device flow (new default)
beam login --api-key -     # unchanged: read a key from stdin (CI)
BEAM_API_KEY=… beam login  # unchanged: env
beam login --paste         # opt back into today's masked TTY prompt
```

No-TTY behaviour is the whole point — this must work when an agent runs it:

```
Sign in to Beam
  1. Open  https://app.beam.ai/activate
  2. Enter code  BEAM-7Q4X
Waiting for approval… (expires in 10:00)
```

- Open the browser automatically when possible (`open` / `xdg-open`), but
  **always print the URL and code** — the agent may be on a remote host.
- Poll at `interval`, honour `slow_down`, stop at `expiresIn`.
- On success: write `BEAM_API_KEY` + `BEAM_WORKSPACE_ID` via the existing
  `write_creds`, then call `cmd_register` exactly as today, then print the
  existing onboarding checklist. The workspace is already chosen, so the
  "pick a workspace" step disappears from the happy path.
- Exit codes keep the established contract: 2 validation, 3 auth/denied/expired,
  5 network. Every failure names its `next` step.

Est. ~120 lines of POSIX sh: two `_http_send` calls, a poll loop, a printer.
No new dependency.

---

## 6. Security requirements

- `userCode` is single-use, rate-limited per client and per IP, TTL ≤ 10 min.
- Rate-limit `/auth/device/token`; reject polling faster than `interval`.
- Bind `deviceCode` ↔ `userCode` ↔ approving user; never allow approval to
  choose a workspace the approver cannot access.
- The consent screen must name the device and the scopes. No silent grants.
- Never log `deviceCode` or the issued key.
- The issued key inherits **no more** than the approver's own permissions.

**Related finding, worth fixing alongside:** `POST /mcp` currently performs no
authentication on `initialize` or `tools/list` — the full tool catalogue is
served with no credential at all (verified against production). Tool *calls* do
authenticate, but they answer failures with **HTTP 200 + `isError: true`** and
terse text (`"Invalid API key"`), never 401/403. That combination makes clients
hard to write correctly and leaks the tool surface. Independent of this spec, but
the same team owns it.

---

## 7. Test plan

Extend `test/e2e.sh`:

- Device-code happy path against a staging mock: code issued → token polled →
  credentials written → `register` called → `doctor` all green.
- `authorization_pending` → keeps polling; `slow_down` → interval grows.
- `access_denied` → exit 3, message says the user declined.
- `expired_token` → exit 3, message says to re-run `beam login`.
- **No TTY:** run with stdin closed and assert login still completes — the
  regression that motivates this whole spec.
- `--api-key -` and `BEAM_API_KEY` still work (no regression for CI).
- Workspace is set from the token response, so `beam workspace` is populated
  without a second step.

---

## 8. Rollout

1. Server ships the three endpoints + `/activate` behind a flag.
2. CLI adds the flow behind `beam login --browser`; `beam login` keeps prompting.
3. Once staging is clean, flip the default: `beam login` → browser,
   `--paste` → old prompt. Bump minor version; update
   `GETTING_STARTED.md` and the `setup` skill (which currently tells users to
   open a terminal).
4. v1.1: loopback-redirect fast path when a local browser is present; keep
   device code as fallback. Add `/auth/device/revoke` for `beam logout`.

## 9. Open questions

1. Can API keys be **scoped to one workspace** today, or is that new work? The
   whole design assumes a key can be minted scoped and named.
2. Is there an existing OAuth client registry, or is `clientId: "beam-cli"` new?
3. Should re-running `beam login` on the same host reuse its existing named key
   or mint a second one? (Prefer: reuse, and show `lastUsedAt`.)
4. Max keys per user — could a fleet of dev machines hit a cap?
