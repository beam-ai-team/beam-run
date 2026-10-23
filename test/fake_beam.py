#!/usr/bin/env python3
"""A fake Beam (Studio + API) for test/connect.sh. Paths are /<host>/<real path>.

Control files in <dir>: ws.json {host: [{id, name}]}, old (hosts without Connect, one per
line), bad ("<host> <status>" probe answers), slow (hosts whose probe stalls), deny (exists: the browser step returns error=access_denied), badkey (exists: the token holds a line break). Writes port, revoked
(host key), lastcode and tokens (host key) back into <dir>.

Test mode and connections (host api.test): one agent, agent-1, with a published and a draft
graph, triggers, connections and a test-mode session, all in memory. Control files: deny403
(test-mode start answers 403), race409 (a test task answers 409 exhausted). Writes mints (one
line per Bearer token minted), lastpatch (the last update-node body), connections (one JSON
body per node connection PATCH) and lasttask (the last POST /agent-tasks body). Like the real
update-node, the fake one gives input params new ids and drops output examples.
"""
import base64
import hashlib
import http.server
import json
import os
import sys
import time
import urllib.parse

DIR = sys.argv[1]
codes, keys, counter = {}, {}, [0]
TM_HOST, TM_KEY, TM_TOKEN, TM_AGENT = "api.test", "test-key", "jwt-test", "agent-1"


def _tool(fn, integration_id, identifier, live=None, test=None, kind="beam_tool", config_id=None):
    return {"id": config_id or "cfg-" + fn, "toolFunctionName": fn, "toolName": fn,
            "integrationProviderId": live, "testIntegrationProviderId": test,
            "inputParams": [{"id": "param-" + fn, "paramName": "to"}],
            "outputParams": [{"id": "out-" + fn, "outputExample": "{\"id\": \"1\"}"}],
            "originalTool": {"type": kind, "integrationId": integration_id,
                             "isIntegrationRequired": bool(integration_id) and kind != "custom_integration_tool",
                             "integration": {"systemIntegrationIdentifier": identifier,
                                             "systemIntegrationProvider": "nango_cloud" if identifier else None}}}


def _initial_state():
    live_mail = {"id": "n-live-mail", "customId": "c-mail", "objective": "Send the reply",
                 "toolConfiguration": _tool("GoogleMail_Send", "int-gmail", "google-mail", live="conn-gmail-1")}
    draft_mail = {"id": "n-draft-mail", "customId": "c-mail", "objective": "Send the reply",
                  "toolConfiguration": _tool("GoogleMail_Send", "int-gmail", "google-mail", live="conn-gmail-1",
                                             config_id="cfg-draft-mail")}
    draft_llm = {"id": "n-draft-llm", "objective": "Draft the answer",
                 "toolConfiguration": _tool("GPTAction_Answer", None, None, kind="gpt_tool", config_id="cfg-llm"),
                 "agentGraphNodeTools": [_tool("Slack_Post", "int-slack", "slack", live="conn-slack-1",
                                               config_id="tool-slack")],
                 "agentGraphNodeMcpIntegrations": [{"id": "mcp-1", "integrationId": "int-notion",
                                                    "integrationProviderId": "conn-notion-1", "tools": [],
                                                    "integration": {"name": "Notion"}}]}
    draft_sheet = {"id": "n-draft-sheet", "customId": "c-sheet", "objective": "Log the ticket",
                   "toolConfiguration": _tool("GoogleSheets_Append", "int-sheets", "google-sheets",
                                              live="conn-sheets-1", config_id="cfg-sheet")}
    draft_api = {"id": "n-draft-api", "objective": "Call the CRM",
                 "toolConfiguration": _tool("CustomApiTool_Crm", "int-crm", "crm-api",
                                            kind="custom_integration_tool", config_id="cfg-crm")}
    return {
        "graphs": {"g-live": {"id": "g-live", "agentId": TM_AGENT, "isActive": True, "isDraft": False,
                              "nodes": [{"id": "n-live-entry", "objective": "Entry"}, live_mail]},
                   "g-draft": {"id": "g-draft", "agentId": TM_AGENT, "isActive": False, "isDraft": True,
                               "nodes": [{"id": "n-draft-entry", "objective": "Entry"}, draft_mail, draft_llm,
                                         draft_sheet, draft_api]}},
        "connections": [
            {"id": "conn-gmail-1", "connectionName": "Support inbox", "integration": "google-mail",
             "integrationId": "int-gmail", "status": "active", "isDefault": True,
             "credentials": {"secret": "must-not-leak"}},
            {"id": "conn-gmail-2", "connectionName": "Test inbox", "integration": "google-mail",
             "integrationId": "int-gmail", "status": "active", "isDefault": False},
            {"id": "conn-gmail-3", "connectionName": "QA inbox", "integration": "google-mail",
             "integrationId": "int-gmail", "status": "active", "isDefault": False},
            {"id": "conn-slack-1", "connectionName": "Ops Slack", "integration": "slack",
             "integrationId": "int-slack", "status": "active", "isDefault": True},
            {"id": "conn-slack-2", "connectionName": "Test Slack", "integration": "slack",
             "integrationId": "int-slack", "status": "active", "isDefault": False},
            {"id": "conn-sheets-1", "connectionName": "Ops sheet", "integration": "google-sheets",
             "integrationId": "int-sheets", "status": "active", "isDefault": True},
            {"id": "conn-notion-1", "connectionName": "Wiki", "integration": "notion",
             "integrationId": "int-notion", "status": "active", "isDefault": True}],
        "triggers": [
            {"id": "trig-1", "title": "New support email", "agentGraphNodeId": "n-live-entry",
             "integrationProviderId": "conn-gmail-1", "isTestTrigger": False,
             "configuration": {"beamAction": "GoogleMail_NewEmail", "integrationIdentifier": "google-mail"},
             "integrationData": {"id": "int-gmail", "name": "Gmail"}},
            {"id": "trig-timer", "title": "Every morning", "agentGraphNodeId": "n-live-entry",
             "integrationProviderId": None, "isTestTrigger": False, "prompt": "Check the inbox",
             "configuration": {"beamAction": "Timer"}}],
        "test": {"isTestModeEnabled": False, "currentTestRuns": 0, "maxTestRuns": None, "testStartedAt": None},
        "tasks": 0,
    }


TM = _initial_state()


def _tm_node(node_id):
    for graph in TM["graphs"].values():
        for node in graph["nodes"]:
            if node["id"] == node_id:
                return graph, node
    return None, None


def _tm_apply_ids(target, incoming):
    for key in ("integrationProviderId", "testIntegrationProviderId"):
        if key in incoming:
            target[key] = incoming[key]


def read(name, default=""):
    try:
        with open(os.path.join(DIR, name), encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return default


def append(name, line):
    with open(os.path.join(DIR, name), "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def tm_authorized(self):
        return (self.headers.get("x-api-key") == TM_KEY
                or self.headers.get("Authorization") == "Bearer " + TM_TOKEN)

    def tm_body(self):
        size = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(size) or b"{}") if size else {}

    def tm_route(self, method, path, query):
        if method == "POST" and path == "/auth/access-token":
            if self.tm_body().get("apiKey") != TM_KEY:
                return self.send(401, {"message": "Unauthorized"})
            append("mints", "1")
            return self.send(200, {"idToken": TM_TOKEN})
        if not self.tm_authorized():
            return self.send(401, {"message": "Unauthorized"})
        test = TM["test"]
        base = "/agents/%s/test-mode/" % TM_AGENT
        if path == base + "status" and method == "GET":
            return self.send(200, test)
        if path == base + "start" and method == "POST":
            body = self.tm_body()
            if os.path.exists(os.path.join(DIR, "deny403")):
                return self.send(403, {"statusCode": 403, "message": "Forbidden resource"})
            if not isinstance(body.get("maxTestRuns"), int) or not 2 <= body["maxTestRuns"] <= 200:
                return self.send(400, {"statusCode": 400, "message": ["maxTestRuns must not be less than 2"]})
            if test["isTestModeEnabled"]:
                return self.send(409, {"statusCode": 409, "message": "Test mode is already active for this agent"})
            test.update(isTestModeEnabled=True, currentTestRuns=0, maxTestRuns=body["maxTestRuns"],
                        testStartedAt="2026-10-22T10:00:00.000Z")
            for override in body.get("testTriggerOverrides") or []:
                live = next(t for t in TM["triggers"] if t["id"] == override["triggerId"])
                copy = dict(live, id="test-" + live["id"], isTestTrigger=True,
                            integrationProviderId=override.get("integrationProviderId"))
                for key in ("title", "prompt", "timezone", "onlyOnce"):
                    if override.get(key) is not None:
                        copy[key] = override[key]
                TM["triggers"].append(copy)
            for override in body.get("toolOverrides") or []:
                for graph in TM["graphs"].values():
                    for node in graph["nodes"]:
                        for tool in [node.get("toolConfiguration")] + (node.get("agentGraphNodeTools") or []):
                            if tool and tool["id"] == override["agentToolConfigurationId"]:
                                tool["testIntegrationProviderId"] = override["integrationProviderId"]
            return self.send(201, test)
        if path == base + "stop" and method == "DELETE":
            if not test["isTestModeEnabled"]:
                return self.send(404, {"statusCode": 404, "message": "No active test session found for this agent"})
            test.update(isTestModeEnabled=False, currentTestRuns=0)
            TM["triggers"] = [t for t in TM["triggers"] if not t["isTestTrigger"]]
            return self.send(200)
        if path == "/agent-graphs/history/" + TM_AGENT:
            return self.send(200, {"graphs": [{"id": g["id"], "isActive": g["isActive"], "isDraft": g["isDraft"]}
                                              for g in TM["graphs"].values()]})
        if path == "/agent-graphs/" + TM_AGENT and method == "GET":
            graph = TM["graphs"].get(query.get("graphId", "g-draft"))
            return self.send(200, {"graph": graph})
        if path.startswith("/agent-graphs/%s/nodes/" % TM_AGENT) and method == "GET":
            _, node = _tm_node(path.rsplit("/", 1)[1])
            if node is None:
                return self.send(400, {"message": "Invalid nodeId"})
            entity = {k: v for k, v in node.items() if k not in ("agentGraphNodeTools", "agentGraphNodeMcpIntegrations")}
            return self.send(200, dict(json.loads(json.dumps(entity)), agentGraph={"id": "graph"}))
        if path.startswith("/agent-graphs/%s/nodes/" % TM_AGENT) and path.endswith("/connection") and method == "PATCH":
            body = self.tm_body()
            append("connections", json.dumps(body, sort_keys=True))
            node_id = path.split("/")[4]
            graph, node = _tm_node(node_id)
            if node is None:
                return self.send(404, {"statusCode": 404, "message": "Node not found for this agent"})
            if body.get("toolConfigurationId"):
                tool = next((t for t in node.get("agentGraphNodeTools") or [] if t["id"] == body["toolConfigurationId"]), None)
                if tool is None:
                    return self.send(404, {"statusCode": 404, "message": "Tool configuration is not attached to this node"})
            else:
                tool = node.get("toolConfiguration")
            connection = next((c for c in TM["connections"] if c["id"] == body.get("connectionId")), None)
            if connection is None:
                return self.send(404, {"statusCode": 404, "message": "Connection not found in this workspace"})
            if connection["integrationId"] != tool["originalTool"]["integrationId"]:
                return self.send(400, {"statusCode": 400, "message": "Connection belongs to a different integration than this tool"})
            field = "integrationProviderId" if body.get("mode") == "live" else "testIntegrationProviderId"
            tool[field] = connection["id"]
            return self.send(200, {"nodeId": node_id, "toolConfigurationId": tool["id"], "mode": body.get("mode"),
                                   "integrationProviderId": tool["integrationProviderId"],
                                   "testIntegrationProviderId": tool["testIntegrationProviderId"]})
        if path == "/agent-graphs/update-node" and method == "PATCH":
            body = self.tm_body()
            with open(os.path.join(DIR, "lastpatch"), "w", encoding="utf-8") as fh:
                json.dump(body, fh)
            graph, node = _tm_node(body["node"]["id"])
            if graph is None or graph["id"] != body.get("graphId"):
                return self.send(404, {"message": "Node not found"})
            incoming = body["node"]
            if "toolConfiguration" not in incoming or incoming["toolConfiguration"] is None:
                node.pop("toolConfiguration", None)
            else:
                tool = node["toolConfiguration"]
                _tm_apply_ids(tool, incoming["toolConfiguration"])
                tool["inputParams"] = [dict(p, id="new-" + p["id"]) for p in tool.get("inputParams") or []]
                tool["outputParams"] = [dict(p, outputExample=None) for p in tool.get("outputParams") or []]
            if incoming.get("agentGraphNodeTools") is not None:
                kept = []
                for tool in node.get("agentGraphNodeTools") or []:
                    match = next((t for t in incoming["agentGraphNodeTools"] if t.get("id") == tool["id"]), None)
                    if match is not None:
                        _tm_apply_ids(tool, match)
                        kept.append(tool)
                node["agentGraphNodeTools"] = kept
            return self.send(200, node)
        if path == "/integration-provider/connected-integrations":
            return self.send(200, {"connectedIntegrations": TM["connections"]})
        if path.startswith("/integration-provider/get-connections/"):
            wanted = path.rsplit("/", 1)[1]
            return self.send(200, [c for c in TM["connections"] if c["integrationId"] == wanted])
        if path == "/agent-trigger/" + TM_AGENT:
            want_test = query.get("isTestTrigger") == "true"
            return self.send(200, [t for t in TM["triggers"] if t["isTestTrigger"] == want_test])
        if path == "/agent-tasks" and method == "POST":
            body = self.tm_body()
            with open(os.path.join(DIR, "lasttask"), "w", encoding="utf-8") as fh:
                json.dump(body, fh)
            if body.get("isTestTask"):
                if os.path.exists(os.path.join(DIR, "race409")):
                    return self.send(409, {"statusCode": 409, "message": "Test runs exhausted: 3 of 3 used. Start test mode again to reset."})
                if not test["isTestModeEnabled"]:
                    used, cap = test["currentTestRuns"], test["maxTestRuns"]
                    if cap is not None and used >= cap:
                        return self.send(409, {"statusCode": 409, "message": "Test runs exhausted: %d of %d used. Start test mode again to reset." % (used, cap)})
                    return self.send(409, {"statusCode": 409, "message": "Test mode is not active"})
                test["currentTestRuns"] += 1
                if test["currentTestRuns"] >= test["maxTestRuns"]:
                    test["isTestModeEnabled"] = False
                    TM["triggers"] = [t for t in TM["triggers"] if not t["isTestTrigger"]]
            TM["tasks"] += 1
            return self.send(201, {"id": "task-%d" % TM["tasks"], "status": "QUEUED"})
        return self.send(404, {"message": "Cannot %s %s" % (method, path)})

    def do_PATCH(self):
        host, path, query = self.split()
        if host == TM_HOST:
            return self.tm_route("PATCH", path, query)
        self.send(404, {})

    def do_DELETE(self):
        host, path, query = self.split()
        if host == TM_HOST:
            return self.tm_route("DELETE", path, query)
        self.send(404, {})

    def send(self, status, body=None, headers=()):
        raw = json.dumps(body).encode() if body is not None else b""
        self.send_response(status)
        for name, value in headers:
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def split(self):
        url = urllib.parse.urlparse(self.path)
        host, _, path = url.path.lstrip("/").partition("/")
        return host, "/" + path, {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}

    def do_GET(self):
        host, path, query = self.split()
        if host == TM_HOST:
            return self.tm_route("GET", path, query)
        if path == "/api/cli/authorize":
            for line in read("bad").splitlines():  # "<host> <status>": answer the probe with that status
                bad_host, _, status = line.partition(" ")
                if bad_host == host:
                    return self.send(int(status), {})
            if host in read("slow").split():  # longer than the CLI's probe timeout
                time.sleep(7)
            if host in read("old").split():
                return self.send(404, {"error": "not found"})
            if not query:
                return self.send(200, {"ok": True, "version": 1})
            redirect, state = query["redirect_uri"], query["state"]
            if os.path.exists(os.path.join(DIR, "deny")):
                return self.send(302, headers=[("Location", "%s?error=access_denied&state=%s" % (redirect, state))])
            counter[0] += 1
            code = "code%dx" % counter[0]
            codes[code] = (query["code_challenge"], redirect)
            with open(os.path.join(DIR, "lastcode"), "w", encoding="utf-8") as fh:
                fh.write(code)
            return self.send(302, headers=[("Location", "%s?code=%s&state=%s" % (redirect, code, state))])
        if path == "/v2/user/me":
            if keys.get(self.headers.get("x-api-key")) != host:
                return self.send(401, {"error": "unauthorized"})
            workspaces = json.loads(read("ws.json", "{}")).get(host, [{"id": "ws-" + host, "name": "Main"}])
            return self.send(200, {"id": "u", "workspaces": workspaces})
        self.send(404, {})

    def do_POST(self):
        host, path, query = self.split()
        if host == TM_HOST:
            return self.tm_route("POST", path, query)
        size = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(size) or b"{}") if size else {}
        if path == "/auth/cli/token":
            challenge, redirect = codes.pop(body.get("code"), (None, None))
            digest = base64.urlsafe_b64encode(hashlib.sha256(body.get("code_verifier", "").encode()).digest()).rstrip(b"=").decode()
            if challenge is None or digest != challenge or body.get("redirect_uri") != redirect or not body.get("client_name"):
                return self.send(400, {"errorCode": "invalid_grant"})
            counter[0] += 1
            key = "key-%s-%d" % (host, counter[0])
            if os.path.exists(os.path.join(DIR, "badkey")):  # a hostile server: a key that smuggles a curl option
                key = key + '\nurl = "http://127.0.0.1:1/x"'
            keys[key] = host
            append("tokens", "%s %s" % (host, key))
            return self.send(200, {"api_key": key, "user": {"id": "u", "email": "u@example.com"}})
        if path == "/auth/cli/revoke":
            key = self.headers.get("x-api-key")
            if keys.pop(key, None) is None:
                return self.send(401, {"error": "unauthorized"})
            append("revoked", "%s %s" % (host, key))
            return self.send(204)
        self.send(404, {})


server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
keys["legacy-key"] = "api.us.beamstudio.ai"  # a pasted key, for the not-upgraded fallback
with open(os.path.join(DIR, "port"), "w", encoding="utf-8") as fh:
    fh.write(str(server.server_port))
server.serve_forever()
