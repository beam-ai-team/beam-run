#!/usr/bin/env python3
"""Vendored stdio <-> HTTP MCP bridge for Beam.

Why this exists: the Beam MCP endpoint speaks HTTP, but stdio-only hosts spawn
`beam mcp` and talk newline-delimited JSON-RPC over stdin/stdout. The public
bridges (uvx `mcp-proxy`, npx `mcp-remote`) need a uv or Node runtime the user
may not have, so we ship our own — standard library only, no install step.

Two modes:
  * signed in -> forward every JSON-RPC message to $BEAM_MCP_URL.
  * no key    -> serve a VALID but degraded session exposing one tool that
                 explains how to finish setup. A live server that can explain
                 itself beats a dead one that fails to start: on a fresh
                 install the host launches this before the user has ever run
                 `beam login`.

Env: BEAM_API_KEY (may be empty), BEAM_MCP_URL, BEAM_LOCAL_DEV=1 (for a
loopback endpoint), BEAM_API_TIMEOUT (seconds).
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

PRODUCTION_MCP_URL = "https://api.beamstudio.ai/mcp"


def _is_loopback_url(url):
    """Return whether *url* targets localhost or a loopback address."""
    try:
        host = urllib.parse.urlparse(url).hostname
    except ValueError:
        return False
    return host in {"localhost", "127.0.0.1", "::1"}


def _resolve_mcp_url():
    candidate = os.environ.get("BEAM_MCP_URL") or ""
    if _is_loopback_url(candidate) and os.environ.get("BEAM_LOCAL_DEV") != "1":
        return PRODUCTION_MCP_URL
    return candidate or PRODUCTION_MCP_URL


MCP_URL = _resolve_mcp_url()
API_KEY = os.environ.get("BEAM_API_KEY") or ""
TIMEOUT = float(os.environ.get("BEAM_API_TIMEOUT") or 120)
PROTOCOL = "2025-06-18"

SETUP_HINT = (
    "Beam is not signed in yet, so no Beam tools are available.\n\n"
    "To finish setup:\n"
    "  1. Create an API key: app.beam.ai -> Personal settings -> API Keys\n"
    "  2. Run in a terminal:  beam login\n\n"
    "Then ask 'list my Beam agents'."
)

STATUS_TOOL = {
    "name": "beam_setup_status",
    "description": (
        "Report Beam connection status and the exact next step to finish setup. "
        "Call this when Beam tools are missing or a Beam action fails."
    ),
    "inputSchema": {"type": "object", "properties": {}},
}


def write(msg):
    """Emit one JSON-RPC message as a single line and flush."""
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def error(msg_id, code, message):
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def parse_body(raw, content_type):
    """Return the JSON-RPC payload from a JSON or text/event-stream body."""
    text = raw.decode("utf-8", "replace").strip()
    if not text:
        return None
    if "text/event-stream" in (content_type or ""):
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if chunk and chunk != "[DONE]":
                    try:
                        return json.loads(chunk)
                    except ValueError:
                        continue
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


def forward(msg):
    """POST one JSON-RPC message upstream; return the reply (or None)."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        # The endpoint accepts either header; send both so any server build works.
        "Authorization": "Bearer " + API_KEY,
        "x-api-key": API_KEY,
    }
    req = urllib.request.Request(
        MCP_URL, data=json.dumps(msg).encode("utf-8"), headers=headers, method="POST"
    )
    resp = urllib.request.urlopen(req, timeout=TIMEOUT)
    with resp:
        return parse_body(resp.read(), resp.headers.get("Content-Type"))


AUTH_MARKERS = ("invalid api key", "authentication required", "unauthorized")

FIX_AUTH = (
    "\n\nTo fix: run `beam login` in a terminal with a fresh key from "
    "app.beam.ai -> Personal settings -> API Keys, then `beam register`, "
    "then fully restart this agent."
)


def enrich_auth_error(reply):
    """Append the concrete fix to the server's terse auth failures.

    Beam answers auth problems with HTTP 200 + {"isError": true} and text like
    "Invalid API key" — true but not actionable. Name the next command so the
    agent can resolve it instead of just relaying the failure.
    """
    try:
        result = reply.get("result")
        if not isinstance(result, dict) or not result.get("isError"):
            return reply
        content = result.get("content")
        if not isinstance(content, list):
            return reply
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "text":
                continue
            text = item.get("text") or ""
            low = text.lower()
            if any(m in low for m in AUTH_MARKERS) and "beam login" not in low:
                item["text"] = text + FIX_AUTH
    except Exception:
        pass
    return reply


def handle_degraded(msg):
    """Serve a minimal, valid MCP session when there is no API key."""
    method = msg.get("method")
    msg_id = msg.get("id")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": PROTOCOL,
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {"name": "beam (setup required)", "version": "0.6.0"},
                "instructions": SETUP_HINT,
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": [STATUS_TOOL]}}
    if method == "tools/call":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"content": [{"type": "text", "text": SETUP_HINT}], "isError": False},
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    return error(msg_id, -32001, SETUP_HINT)


def main():
    degraded = not API_KEY
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            write(error(None, -32700, "parse error: invalid JSON"))
            continue

        is_notification = "id" not in msg
        if degraded:
            if is_notification:
                continue
            write(handle_degraded(msg))
            continue

        try:
            reply = forward(msg)
        except urllib.error.HTTPError as exc:
            if is_notification:
                continue
            if exc.code in (401, 403):
                write(error(
                    msg.get("id"), -32001,
                    "Beam rejected the API key. Run `beam login` with a fresh key "
                    "(app.beam.ai -> Personal settings -> API Keys), then fully "
                    "restart this agent.",
                ))
            else:
                write(error(
                    msg.get("id"), -32003,
                    "Beam API error (HTTP %s) calling %s. Run `beam doctor` to diagnose."
                    % (exc.code, MCP_URL),
                ))
            continue
        except Exception as exc:  # network, timeout, DNS
            if is_notification:
                continue
            write(error(
                msg.get("id"), -32002,
                "Could not reach Beam at %s (%s). Check your connection, then "
                "run `beam doctor`." % (MCP_URL, type(exc).__name__),
            ))
            continue

        # Notifications get HTTP 202 with an empty body — nothing to write back.
        if reply is not None:
            write(enrich_auth_error(reply))


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, BrokenPipeError):
        pass
