#!/usr/bin/env python3
"""Helpers for `beam login` (browser Connect). Standard library only.

  pkce              print code_verifier, state, S256 challenge and a spare port (one per line)
  start <pending>   bind 127.0.0.1, detach, print the port; serve /callback once, then exit
  query             read a pasted callback address on stdin; print code, state and error (one per line)

The listener writes CODE=... or ERROR=... into the pending file; it never prints them.
"""
import base64
import hashlib
import http.server
import os
import re
import secrets
import sys
import time
import urllib.parse

TTL = int(os.environ.get("BEAM_TEST_LISTENER_TTL") or 300)  # seconds the listener stays up (override is for tests)
SAFE = re.compile(r"^[A-Za-z0-9._~-]{1,512}$")
GOOD = "Connected — you can close this tab and return to your coding tool."
BAD = "Sign-in did not complete — go back to your tool and try again."


def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def pkce():
    verifier = b64(secrets.token_bytes(48))  # 64 characters
    print(verifier)
    print(b64(secrets.token_bytes(16)))
    print(b64(hashlib.sha256(verifier.encode()).digest()))
    print(49152 + secrets.randbelow(16000))


def query():
    url = sys.stdin.read().strip()  # read from stdin: the code stays off the command line
    values = urllib.parse.parse_qs(urllib.parse.urlparse(url).query or url)
    for name in ("code", "state", "error"):
        print(values.get(name, [""])[0])


def pending_value(path, name):
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                key, _, value = line.rstrip("\n").partition("=")
                if key == name:
                    return value
    except OSError:
        pass
    return ""


def start(path):
    done = []

    class Handler(http.server.BaseHTTPRequestHandler):
        timeout = 5  # an idle or half-open connection must not stall the listener

        def log_message(self, *args):
            pass

        def reply(self, status, text):
            body = ("<!doctype html><meta charset=utf-8><title>Beam</title><p>%s</p>"
                    "<script>window.close()</script>" % text).encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urllib.parse.urlparse(self.path)
            if url.path != "/callback":
                return self.reply(404, "Not found")
            values = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
            expected = pending_value(path, "STATE")
            if not expected or not secrets.compare_digest(values.get("state", "").encode(), expected.encode()):
                return self.reply(400, BAD)  # not our sign-in: keep waiting for the real one
            error, code = values.get("error", ""), values.get("code", "")
            line = "CODE=%s" % code if SAFE.match(code) and not error else "ERROR=%s" % (
                error if SAFE.match(error) else "invalid_callback")
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
            done.append(1)
            self.reply(200 if line.startswith("CODE=") else 400, GOOD if line.startswith("CODE=") else BAD)

    try:
        if os.environ.get("BEAM_TEST_BIND_BLOCKED"):  # test hook: simulate a sandbox that blocks binds
            raise PermissionError(1, "Operation not permitted")
        server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    except OSError as exc:
        print("cannot bind 127.0.0.1: %s" % exc, file=sys.stderr)
        sys.exit(3)
    if os.fork():
        print(server.server_port)
        sys.stdout.flush()
        os._exit(0)
    os.setsid()
    null = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(null, fd)
    server.timeout = 1
    deadline = time.time() + TTL
    while not done and time.time() < deadline:
        server.handle_request()
    os._exit(0)


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "pkce":
        pkce()
    elif command == "start" and len(sys.argv) == 3:
        start(sys.argv[2])
    elif command == "query" and len(sys.argv) == 2:
        query()
    else:
        sys.exit("usage: login_listener.py pkce | start <pending-file> | query")
