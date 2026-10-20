# Host-managed execution

A host supplies `BEAM_MANAGED_CONTEXT=1`, `BEAM_API_KEY`, `BEAM_API_URL`,
`BEAM_WORKSPACE_ID`, and `BEAM_SESSION_ID` for one admitted command. The host
must authenticate the caller, enforce workspace membership, validate operation
arguments, park required approvals, and reconcile ambiguous mutations before retry.

Managed mode never reads a local profile. Checkout is read-only and locked;
login, logout, registration, local MCP and instance/workspace selection are
unavailable. Credential values must remain outside command arguments, persistent
environments, images, snapshots and logs. Use a private work/config directory and
destroy it after execution.

`beam manifest` exports the canonical operation contract as JSON. Each operation
has a closed JSON input schema, argument/file serializer, effect class,
confirmation floor, and any verification operation. The exporter fails on an
incomplete mapping. Pin this CLI, exporter, Python builder, skill and playbooks
from the same source revision. The host stages JSON/text files and resolves
artifact handles before invoking the generated argument array without a shell.

`BEAM_MANAGED_HTTP_STATUS_FILE`, when supplied by the host, receives only the latest numeric
API response status, including successful fallback responses. This lets hosts distinguish reconnect-required
credentials from insufficient permissions without exposing HTTP headers.

Run managed boundary checks with:

```sh
python3 -m unittest discover -s beam/scripts/tests -p test_managed_runtime.py
python3 beam/scripts/check_playbooks.py
```

## Standalone browser Connect compatibility

The standalone Connect flow in [PR #21](https://github.com/beam-ai-team/beam-run/pull/21)
uses Studio's `/api/cli/authorize` and Platform's `/auth/cli/*` endpoints with a
loopback callback. It owns local profiles, pending login state and key revocation.
Managed execution must never invoke that flow, including `login --wait`,
`--paste`, `--callback` or `--replace`; the host owns authorization and revocation.
Prism's registered HTTPS callback and confidential application grant remain a
separate adapter over Platform's existing API-key service. Do not widen the
standalone loopback allowlist to arbitrary hosted callbacks.

The managed regression curl fixture supports both direct headers and Connect's
private `curl -K` header transport. Compose the managed changes with PR #21,
rerun both suites, then pin the combined immutable revision in Prism's source
lock and runner image. The existing Prism pin does not advance automatically.
