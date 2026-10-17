#!/usr/bin/env python3
"""A fake Beam (Studio + API) for test/connect.sh. Paths are /<host>/<real path>.

Control files in <dir>: ws.json {host: [{id, name}]}, old (hosts without Connect, one per
line), deny (exists: the browser step returns error=access_denied). Writes port, revoked
(host key), lastcode and tokens (host key) back into <dir>.
"""
import base64
import hashlib
import http.server
import json
import os
import sys
import urllib.parse

DIR = sys.argv[1]
codes, keys, counter = {}, {}, [0]


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
        if path == "/api/cli/authorize":
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
        host, path, _ = self.split()
        size = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(size) or b"{}") if size else {}
        if path == "/auth/cli/token":
            challenge, redirect = codes.pop(body.get("code"), (None, None))
            digest = base64.urlsafe_b64encode(hashlib.sha256(body.get("code_verifier", "").encode()).digest()).rstrip(b"=").decode()
            if challenge is None or digest != challenge or body.get("redirect_uri") != redirect or not body.get("client_name"):
                return self.send(400, {"errorCode": "invalid_grant"})
            counter[0] += 1
            key = "key-%s-%d" % (host, counter[0])
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
