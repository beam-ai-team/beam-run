#!/usr/bin/env python3
"""Vendored stdio <-> HTTP MCP bridge for Beam.

Why this exists: the Beam MCP endpoint speaks HTTP, but stdio-only hosts spawn
`beam mcp` and talk newline-delimited JSON-RPC over stdin/stdout. The public
bridges (uvx `mcp-proxy`, npx `mcp-remote`) need a uv or Node runtime the user
may not have, so we ship our own — standard library only, no install step.

Two modes:
  * signed in -> forward operational JSON-RPC messages to $BEAM_MCP_URL.
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


def _resolve_api_url():
    """Resolve the REST origin that corresponds to the configured MCP URL."""
    explicit = (os.environ.get("BEAM_API_URL") or "").strip().rstrip("/")
    if explicit:
        return explicit
    parsed = urllib.parse.urlparse(MCP_URL)
    if parsed.scheme and parsed.netloc:
        return "%s://%s" % (parsed.scheme, parsed.netloc)
    return "https://api.beamstudio.ai"


API_URL = _resolve_api_url()

SETUP_HINT = (
    "Beam is not signed in yet, so no Beam tools are available.\n\n"
    "To finish setup:\n"
    "  1. Create an API key: app.beam.ai -> Personal settings -> API Keys\n"
    "  2. Run in a terminal:  beam login\n"
    "  3. Fully quit and reopen this agent (MCP reads the key only at startup)\n\n"
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

# Flow configuration is intentionally not part of the general MCP surface. It
# has dependencies (draft/live selection, link integrity, consent and
# integration configuration) that the Agent Builder owns. Keep those raw
# server tools unavailable even when an upstream Beam MCP server advertises
# them. This is a policy boundary, not a permission boundary: callers can use
# `beam agent-builder` for the guarded workflow.
FLOW_INTERNAL_TOOLS = frozenset(
    {
        "getAgentGraph",
        "getTaskNodesByTool",
        "getToolOutputSchema",
        "testGraphNode",
        "updateGraphNode",
        "startTask",
    }
)

# These tools are implemented in the local proxy rather than the hosted MCP
# server. Each one is read-only and describes workspace state that exists
# outside an agent's Flow, so it remains useful without duplicating the Agent
# Builder's guarded graph/configuration surface.
LOCAL_OPERATION_TOOLS = (
    {
        "name": "listPreferredModels",
        "description": "List preferred AI models for one Beam workspace. Read-only.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspaceId": {"type": "string", "description": "Beam workspace ID."},
            },
            "required": ["workspaceId"],
        },
    },
    {
        "name": "listActiveTools",
        "description": "List a bounded page of active tools in one Beam workspace. Read-only.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspaceId": {"type": "string", "description": "Beam workspace ID."},
                "searchKeyword": {"type": "string"},
                "type": {"type": "string"},
                "pageNum": {"type": "integer", "minimum": 1, "default": 1},
                "pageSize": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25},
                "categoryId": {"type": "string"},
                "agentId": {"type": "string"},
                "creatorType": {"type": "string"},
                "includedFunctionNames": {"type": "string"},
                "excludedFunctionNames": {"type": "string"},
                "excludeAgentTools": {"type": "boolean"},
            },
            "required": ["workspaceId"],
        },
    },
    {
        "name": "listAgentViews",
        "description": "List Agent Views in one Beam workspace. Read-only.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspaceId": {"type": "string", "description": "Beam workspace ID."},
                "agentId": {"type": "string"},
                "search": {"type": "string"},
                "pageNum": {"type": "integer", "minimum": 1},
                "pageSize": {"type": "integer", "minimum": 1, "maximum": 100},
            },
            "required": ["workspaceId"],
        },
    },
    {
        "name": "getAgentView",
        "description": "Get an Agent View definition. Read-only.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "viewId": {"type": "string"},
                "workspaceId": {"type": "string", "description": "Optional Beam workspace ID."},
            },
            "required": ["viewId"],
        },
    },
    {
        "name": "listAgentViewRecords",
        "description": "List records in an Agent View. Read-only.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "viewId": {"type": "string"},
                "workspaceId": {"type": "string", "description": "Optional Beam workspace ID."},
                "pageNum": {"type": "integer", "minimum": 1},
                "pageSize": {"type": "integer", "minimum": 1, "maximum": 100},
                "fields": {"type": "string", "description": "Comma-separated field IDs."},
                "sort": {"type": "string"},
                "where": {"type": "string"},
            },
            "required": ["viewId"],
        },
    },
    {
        "name": "listLinkedAgentViewRecords",
        "description": "List records linked to an Agent View record. Read-only.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "viewId": {"type": "string"},
                "columnId": {"type": "string"},
                "recordId": {"type": "string"},
                "workspaceId": {"type": "string", "description": "Optional Beam workspace ID."},
                "pageNum": {"type": "integer", "minimum": 1},
                "pageSize": {"type": "integer", "minimum": 1, "maximum": 100},
            },
            "required": ["viewId", "columnId", "recordId"],
        },
    },
)
LOCAL_OPERATION_NAMES = frozenset(tool["name"] for tool in LOCAL_OPERATION_TOOLS)


def bare_tool_name(name):
    """Return an upstream tool name from a host-qualified MCP name."""
    if not isinstance(name, str):
        return ""
    return name.rsplit("__", 1)[-1]


def is_flow_internal_tool(name):
    return bare_tool_name(name) in FLOW_INTERNAL_TOOLS


def filter_tools_list_reply(reply):
    """Remove Flow internals and advertise the local read-only operations."""
    try:
        result = reply.get("result")
        tools = result.get("tools") if isinstance(result, dict) else None
        if isinstance(tools, list):
            result["tools"] = [
                tool
                for tool in tools
                if not is_flow_internal_tool(tool.get("name") if isinstance(tool, dict) else None)
            ]
            existing = {
                tool.get("name") for tool in result["tools"] if isinstance(tool, dict)
            }
            result["tools"].extend(
                tool for tool in LOCAL_OPERATION_TOOLS if tool["name"] not in existing
            )
    except Exception:
        # A malformed upstream response should remain visible for diagnosis.
        pass
    return reply


def flow_internal_tool_reply(msg):
    name = bare_tool_name((msg.get("params") or {}).get("name"))
    return {
        "jsonrpc": "2.0",
        "id": msg.get("id"),
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": (
                        "%s is Flow-internal and is intentionally unavailable through "
                        "the general Beam MCP surface. Use the Beam Agent Builder skill "
                        "and `beam agent-builder` instead; it preserves draft, dependency, "
                        "consent, and publish safeguards."
                    ) % name,
                }
            ],
            "isError": True,
        },
    }


def local_operation_error(msg, message):
    return {
        "jsonrpc": "2.0",
        "id": msg.get("id"),
        "result": {"content": [{"type": "text", "text": message}], "isError": True},
    }


def local_operation_reply(msg, data):
    # `structuredContent` must be a record. Lists remain lossless in the text
    # block and are wrapped for hosts that choose to consume structured output.
    structured = data if isinstance(data, dict) else {"data": data}
    return {
        "jsonrpc": "2.0",
        "id": msg.get("id"),
        "result": {
            "content": [{"type": "text", "text": json.dumps(data)}],
            "structuredContent": structured,
        },
    }


def rest_get(path, workspace_id=None, params=None):
    """Call a read-only Beam REST endpoint with its documented headers."""
    query = urllib.parse.urlencode(
        {key: value for key, value in (params or {}).items() if value is not None and value != ""}
    )
    url = API_URL + path + (("?" + query) if query else "")
    headers = {"Accept": "application/json", "x-api-key": API_KEY}
    if workspace_id:
        headers["current-workspace-id"] = workspace_id
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        raw = response.read().decode("utf-8", "replace")
    return json.loads(raw) if raw else {}


def local_operation_request(msg):
    """Run a local read-only operation, or return None for upstream forwarding."""
    params = (msg.get("params") or {})
    name = bare_tool_name(params.get("name"))
    if name not in LOCAL_OPERATION_NAMES:
        return None
    arguments = params.get("arguments") or {}
    if not isinstance(arguments, dict):
        return local_operation_error(msg, "Tool arguments must be an object.")

    required = {
        "listPreferredModels": ("workspaceId",),
        "listActiveTools": ("workspaceId",),
        "listAgentViews": ("workspaceId",),
        "getAgentView": ("viewId",),
        "listAgentViewRecords": ("viewId",),
        "listLinkedAgentViewRecords": ("viewId", "columnId", "recordId"),
    }[name]
    missing = [key for key in required if not arguments.get(key)]
    if missing:
        return local_operation_error(msg, "Missing required argument(s): %s." % ", ".join(missing))

    workspace_id = arguments.get("workspaceId")
    try:
        if name == "listPreferredModels":
            data = rest_get("/custom-tool/preferred-models", workspace_id)
        elif name == "listActiveTools":
            data = rest_get(
                "/tool/active-tools",
                workspace_id,
                _pick(
                    arguments,
                    "searchKeyword",
                    "type",
                    "categoryId",
                    "agentId",
                    "creatorType",
                    "includedFunctionNames",
                    "excludedFunctionNames",
                    "excludeAgentTools",
                    pageNum=arguments.get("pageNum", 1),
                    pageSize=arguments.get("pageSize", 25),
                ),
            )
        elif name == "listAgentViews":
            data = rest_get(
                "/agent-views",
                workspace_id,
                _pick(arguments, "agentId", "search", "pageNum", "pageSize"),
            )
        elif name == "getAgentView":
            data = rest_get("/agent-views/%s" % _path_id(arguments["viewId"]), workspace_id)
        elif name == "listAgentViewRecords":
            data = rest_get(
                "/agent-views/%s/records" % _path_id(arguments["viewId"]),
                workspace_id,
                _pick(arguments, "pageNum", "pageSize", "fields", "sort", "where"),
            )
        else:
            data = rest_get(
                "/agent-views/%s/columns/%s/links/%s"
                % (_path_id(arguments["viewId"]), _path_id(arguments["columnId"]), _path_id(arguments["recordId"])),
                workspace_id,
                _pick(arguments, "pageNum", "pageSize"),
            )
    except urllib.error.HTTPError as exc:
        return local_operation_error(
            msg, "Beam API error (HTTP %s) calling %s. Run `beam doctor` to diagnose." % (exc.code, API_URL)
        )
    except (ValueError, TypeError) as exc:
        return local_operation_error(msg, "Beam returned invalid JSON: %s." % exc)
    except Exception as exc:
        return local_operation_error(
            msg, "Could not reach Beam at %s (%s). Check your connection, then run `beam doctor`." % (API_URL, type(exc).__name__)
        )
    return local_operation_reply(msg, data)


def _pick(values, *keys, **defaults):
    picked = {key: values.get(key) for key in keys}
    picked.update(defaults)
    return picked


def _path_id(value):
    return urllib.parse.quote(str(value), safe="")


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
                "serverInfo": {"name": "beam (setup required)", "version": "0.5.0"},
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

        if msg.get("method") == "tools/call" and is_flow_internal_tool(
            (msg.get("params") or {}).get("name")
        ):
            if not is_notification:
                write(flow_internal_tool_reply(msg))
            continue

        if msg.get("method") == "tools/call":
            local_reply = local_operation_request(msg)
            if local_reply is not None:
                if not is_notification:
                    write(local_reply)
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
            if msg.get("method") == "tools/list":
                reply = filter_tools_list_reply(reply)
            write(enrich_auth_error(reply))


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, BrokenPipeError):
        pass
