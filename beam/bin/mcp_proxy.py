#!/usr/bin/env python3
"""Local stdio bridge for Beam with one instance/workspace per host session."""

import glob
import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

PRODUCTION_API_BASE = "https://api.beamstudio.ai"
PRODUCTION_MCP_URL = PRODUCTION_API_BASE + "/mcp"
TIMEOUT = float(os.environ.get("BEAM_API_TIMEOUT") or 120)
PROTOCOL = "2025-06-18"


def _is_loopback_url(url):
    try:
        host = urllib.parse.urlparse(url).hostname
    except ValueError:
        return False
    return host in {"localhost", "127.0.0.1", "::1"}


def _resolve_url(name, default):
    candidate = os.environ.get(name) or ""
    if _is_loopback_url(candidate) and os.environ.get("BEAM_LOCAL_DEV") != "1":
        return default
    return candidate or default


MCP_URL = _resolve_url("BEAM_MCP_URL", PRODUCTION_MCP_URL)
API_URL = _resolve_url("BEAM_API_URL", PRODUCTION_API_BASE)
API_KEY = os.environ.get("BEAM_API_KEY") or ""
CONFIG_DIR = os.environ.get("BEAM_CONFIG_DIR") or os.path.expanduser("~/.config/beam")
SESSION_ID = os.environ.get("BEAM_SESSION_ID") or "mcp-%s" % os.getppid()
SESSION_FILE = os.path.join(CONFIG_DIR, "sessions", SESSION_ID)


def read_values(path):
    values = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                key, sep, value = line.rstrip("\n").partition("=")
                if sep and key.startswith("BEAM_"):
                    values[key] = value
    except OSError:
        pass
    return values


def profile_paths():
    return [p for p in glob.glob(os.path.join(CONFIG_DIR, "instances", "*")) if os.path.isfile(p)]


def profile_path(instance_id):
    return os.path.join(CONFIG_DIR, "instances", instance_id)


def load_context():
    session = read_values(SESSION_FILE)
    profiles = profile_paths()
    instance_id = session.get("BEAM_INSTANCE_ID", "")
    if not instance_id and len(profiles) == 1:
        instance_id = read_values(profiles[0]).get("BEAM_INSTANCE_ID") or os.path.basename(profiles[0])
    if instance_id:
        profile = read_values(profile_path(instance_id))
        if profile.get("BEAM_API_KEY"):
            return {
                "key": profile["BEAM_API_KEY"],
                "api": profile.get("BEAM_API_URL") or PRODUCTION_API_BASE,
                "mcp": profile.get("BEAM_MCP_URL") or (profile.get("BEAM_API_URL") or PRODUCTION_API_BASE).rstrip("/") + "/mcp",
                "instance_id": instance_id,
                "instance_name": profile.get("BEAM_INSTANCE_NAME") or instance_id,
                "workspace_id": session.get("BEAM_WORKSPACE_ID", ""),
                "workspace_name": session.get("BEAM_WORKSPACE_NAME", ""),
                "previous_workspace_id": profile.get("BEAM_WORKSPACE_ID", ""),
                "previous_workspace_name": profile.get("BEAM_WORKSPACE_NAME", ""),
                "locked": session.get("BEAM_SESSION_LOCKED") == "1",
            }
    if profiles:
        return None
    if API_KEY:
        return {
            "key": API_KEY, "api": API_URL, "mcp": MCP_URL,
            "instance_id": "environment", "instance_name": "Beam",
            "workspace_id": os.environ.get("BEAM_WORKSPACE_ID", ""),
            "workspace_name": "", "locked": False,
        }
    return None


def atomic_values(path, values):
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".beam-", dir=os.path.dirname(path), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for key, value in values.items():
                if value != "":
                    fh.write("%s=%s\n" % (key, value))
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def save_session(context, locked=False):
    atomic_values(SESSION_FILE, {
        "BEAM_INSTANCE_ID": context["instance_id"],
        "BEAM_WORKSPACE_ID": context.get("workspace_id", ""),
        "BEAM_WORKSPACE_NAME": context.get("workspace_name", ""),
        "BEAM_SESSION_LOCKED": "1" if locked else "0",
    })


def write(msg):
    sys.stdout.write(json.dumps(msg, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def error(msg_id, code, message):
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def tool_result(msg_id, text, is_error=False):
    return {"jsonrpc": "2.0", "id": msg_id, "result": {
        "content": [{"type": "text", "text": text}], "isError": is_error,
    }}


def parse_body(raw, content_type):
    text = raw.decode("utf-8", "replace").strip()
    if not text:
        return None
    if "text/event-stream" in (content_type or ""):
        for line in text.splitlines():
            if line.strip().startswith("data:"):
                chunk = line.strip()[5:].strip()
                if chunk and chunk != "[DONE]":
                    try:
                        return json.loads(chunk)
                    except ValueError:
                        pass
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


def request_json(url, key):
    headers = {"Accept": "application/json", "x-api-key": key, "Authorization": "Bearer " + key}
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def forward(msg, context):
    headers = {
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream",
        "Authorization": "Bearer " + context["key"], "x-api-key": context["key"],
    }
    if context.get("workspace_id"):
        headers["current-workspace-id"] = context["workspace_id"]
    req = urllib.request.Request(
        context["mcp"], data=json.dumps(msg).encode("utf-8"), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        return parse_body(response.read(), response.headers.get("Content-Type"))


STATUS_TOOL = {
    "name": "beam_session_status",
    "description": "Initialize or show the structured Beam instance and workspace setup for this session.",
    "inputSchema": {"type": "object", "properties": {}},
}
CHECKOUT_TOOL = {
    "name": "beam_checkout",
    "description": "Choose and lock one saved Beam instance and workspace for this session. If status suggests a previous workspace, ask the user to confirm it before calling this tool with that workspace.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "instance": {"type": "string", "description": "Saved instance id or exact name."},
            "workspace": {"type": "string", "description": "Workspace id or exact name."},
        },
        "required": ["instance"],
    },
}
SETUP_TOOL = {
    "name": "beam_setup_status", "description": "Report Beam setup status and the next safe action.",
    "inputSchema": {"type": "object", "properties": {}},
}


def connections_text():
    profiles = profile_paths()
    if not profiles:
        return (
            "🚀 Beam session setup\n"
            "✅ Beam Run ready\n"
            "⬜ Connect Beam\n\n"
            "Next: run `beam login` in a terminal.\n"
            "1. Paste a Beam workspace URL\n"
            "2. Enter the API key in the hidden prompt\n"
            "3. Select or create a workspace\n\n"
            "Never ask the user to paste an API key into chat."
        )
    rows = []
    for number, path in enumerate(profiles, 1):
        profile = read_values(path)
        rows.append("%s. %s" % (number, profile.get("BEAM_INSTANCE_NAME") or os.path.basename(path)))
    return (
        "🚀 Beam session setup\n"
        "⬜ Instance\n"
        "⬜ Workspace\n\n"
        "Connected instances:\n%s\n"
        "%s. + Add another\n\n"
        "Ask the user to choose an instance. Then select a workspace."
    ) % ("\n".join(rows), len(rows) + 1)


def context_text(context):
    if not context:
        return connections_text()
    workspace = context.get("workspace_name") or context.get("workspace_id")
    if workspace and context.get("locked"):
        return (
            "✅ Beam session ready\n"
            "✅ Instance: %s\n"
            "✅ Workspace: %s\n"
            "🔒 Locked for this session"
        ) % (context["instance_name"], workspace)
    previous = context.get("previous_workspace_name") or context.get("previous_workspace_id")
    suggestion = "\n\nPreviously used: %s\nAsk the user: “Use %s again?”" % (previous, previous) if previous else (
        "\n\nAsk the user for a workspace name, or offer to create a new workspace."
    )
    return (
        "🚀 Beam session setup\n"
        "✅ Instance: %s\n"
        "⬜ Workspace%s"
    ) % (context["instance_name"], suggestion)


def context_badge(context):
    workspace = context.get("workspace_name") or context.get("workspace_id")
    if not workspace:
        return context_text(context)
    state = "locked" if context.get("locked") else "ready"
    return "Beam context: %s / %s [%s]" % (context["instance_name"], workspace, state)


def choose_checkout(arguments):
    selector = str(arguments.get("instance") or "")
    workspace_selector = str(arguments.get("workspace") or "")
    current = load_context()
    matches = []
    for path in profile_paths():
        profile = read_values(path)
        instance_id = profile.get("BEAM_INSTANCE_ID") or os.path.basename(path)
        name = profile.get("BEAM_INSTANCE_NAME") or instance_id
        if selector.lower() in {instance_id.lower(), name.lower()}:
            matches.append((profile, instance_id, name))
    if len(matches) != 1:
        return None, "No unique saved instance matches '%s'.\n%s" % (selector, connections_text())
    profile, instance_id, name = matches[0]
    keep_locked = bool(current and current.get("locked"))
    if keep_locked and current.get("instance_id") != instance_id:
        return None, "This session is locked to another Beam instance. Start a new session to change it."
    if keep_locked and current.get("workspace_id"):
        same = not workspace_selector or workspace_selector.lower() in {
            current["workspace_id"].lower(), current.get("workspace_name", "").lower()
        }
        if same:
            return current, None
        return None, "This session is locked to another Beam workspace. Start a new session to change it."
    context = {
        "key": profile.get("BEAM_API_KEY", ""),
        "api": profile.get("BEAM_API_URL") or PRODUCTION_API_BASE,
        "mcp": profile.get("BEAM_MCP_URL") or (profile.get("BEAM_API_URL") or PRODUCTION_API_BASE).rstrip("/") + "/mcp",
        "instance_id": instance_id, "instance_name": name,
        "workspace_id": "", "workspace_name": "", "locked": False,
    }
    try:
        user = request_json(context["api"].rstrip("/") + "/v2/user/me", context["key"])
    except urllib.error.HTTPError as exc:
        problem = "The saved key for %s was rejected. Run `beam login --replace`." % name
        return None, problem if exc.code in (401, 403) else "Beam API error (HTTP %s)." % exc.code
    except Exception as exc:
        return None, "Could not reach %s (%s). Nothing changed." % (name, type(exc).__name__)
    workspaces = user.get("workspaces") or ([user["workspace"]] if user.get("workspace") else [])
    workspaces = [w for w in workspaces if isinstance(w, dict) and w.get("id")]
    preferred = workspace_selector
    choices = [w for w in workspaces if isinstance(w, dict) and w.get("id") and preferred.lower() in {
        str(w["id"]).lower(), str(w.get("name") or "").lower()
    }] if preferred else []
    if len(choices) == 1:
        selected = choices[0]
    elif workspace_selector:
        return None, "No unique workspace matches '%s' in %s." % (workspace_selector, name)
    elif len(workspaces) == 1:
        selected = workspaces[0]
    else:
        previous_id = profile.get("BEAM_WORKSPACE_ID", "")
        previous = next((w for w in workspaces if str(w["id"]) == previous_id), None)
        if previous:
            previous_name = str(previous.get("name") or previous["id"])
            return None, (
                "🚀 Beam session setup\n"
                "✅ Instance: %s\n"
                "⬜ Workspace\n\n"
                "Previously used: %s\n"
                "Ask the user: “Use %s again?”"
            ) % (name, previous_name, previous_name)
        return None, (
            "🚀 Beam session setup\n"
            "✅ Instance: %s\n"
            "⬜ Workspace\n\n"
            "Ask the user for a workspace name, or offer to create a new workspace. "
            "Do not list every workspace."
        ) % name
    context["workspace_id"] = str(selected["id"])
    context["workspace_name"] = str(selected.get("name") or "")
    context["locked"] = True
    save_session(context, True)
    return context, None


def handle_local(msg, context):
    method, msg_id = msg.get("method"), msg.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {
            "protocolVersion": PROTOCOL, "capabilities": {"tools": {"listChanged": True}},
            "serverInfo": {"name": "beam local", "version": "0.6.0"},
            "instructions": context_text(context),
        }}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    if method == "tools/list":
        tools = [STATUS_TOOL]
        if not context or not context.get("locked") or not context.get("workspace_id"):
            tools.append(CHECKOUT_TOOL)
        if not profile_paths() and not API_KEY:
            tools.append(SETUP_TOOL)
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools}}
    if method == "tools/call":
        name = (msg.get("params") or {}).get("name")
        if name in {"beam_session_status", "beam_setup_status"}:
            return tool_result(msg_id, context_text(context))
        if name == "beam_checkout":
            selected, problem = choose_checkout((msg.get("params") or {}).get("arguments") or {})
            if problem:
                return tool_result(msg_id, problem, True)
            write({"jsonrpc": "2.0", "method": "notifications/tools/list_changed"})
            return tool_result(msg_id, context_text(selected))
    return error(msg_id, -32001, context_text(context))


def enrich(reply, context, msg):
    try:
        result = reply.get("result")
        if isinstance(result, dict) and result.get("isError"):
            for item in result.get("content") or []:
                text = item.get("text") or ""
                if any(marker in text.lower() for marker in ("invalid api key", "authentication required", "unauthorized")) and "beam login" not in text.lower():
                    item["text"] = text + "\n\nRun `beam login --replace` in a terminal, then retry."
        if isinstance(result, dict) and isinstance(result.get("tools"), list):
            names = {tool.get("name") for tool in result["tools"]}
            if STATUS_TOOL["name"] not in names:
                result["tools"].append(STATUS_TOOL)
            if (not context.get("locked") or not context.get("workspace_id")) and CHECKOUT_TOOL["name"] not in names:
                result["tools"].append(CHECKOUT_TOOL)
        if isinstance(result, dict) and "serverInfo" in result:
            result["instructions"] = context_text(context) + "\n\n" + (result.get("instructions") or "")
            result.setdefault("capabilities", {}).setdefault("tools", {})["listChanged"] = True
        if msg.get("method") == "tools/call" and isinstance(result, dict) and isinstance(result.get("content"), list):
            result["content"].append({"type": "text", "text": context_badge(context)})
    except Exception:
        pass
    return reply


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            write(error(None, -32700, "parse error: invalid JSON"))
            continue
        context = load_context()
        if "id" not in msg:
            if context:
                try:
                    forward(msg, context)
                except Exception:
                    pass
            continue
        name = ((msg.get("params") or {}).get("name") if msg.get("method") == "tools/call" else "")
        needs_checkout = not context or not context.get("workspace_id")
        local = needs_checkout or msg.get("method") == "ping" or name in {
            "beam_session_status", "beam_checkout", "beam_setup_status"
        }
        if msg.get("method") == "tools/list" and needs_checkout:
            local = True
        if local:
            write(handle_local(msg, context))
            continue
        if msg.get("method") == "tools/call" and context.get("instance_id") != "environment":
            save_session(context, True)
            context["locked"] = True
        try:
            reply = forward(msg, context)
        except urllib.error.HTTPError as exc:
            message = "Beam rejected the saved key; run `beam login --replace`." if exc.code in (401, 403) else "Beam API error (HTTP %s)." % exc.code
            write(error(msg.get("id"), -32001, message))
            continue
        except Exception as exc:
            write(error(msg.get("id"), -32002, "Could not reach %s (%s)." % (context["instance_name"], type(exc).__name__)))
            continue
        if reply is not None:
            write(enrich(reply, context, msg))


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, BrokenPipeError):
        pass
