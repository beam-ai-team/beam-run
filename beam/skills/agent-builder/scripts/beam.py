#!/usr/bin/env python3
"""
beam.py - Beam Agent Builder CLI

A single, dependency-free command-line tool for building and deploying
Beam AI agents. It turns an agent spec (JSON) into a deployed Beam agent:
creating/updating the graph, attaching integration tools, re-linking
parameters, verifying links, configuring triggers/webhooks, and publishing.

Standard library only - no pip install, no node_modules. Runs anywhere
Python 3.8+ exists.

--------------------------------------------------------------------------
CREDENTIALS
--------------------------------------------------------------------------
Resolved automatically, first hit wins. There is no .env file:

  BEAM_API_KEY        env var, else ~/.config/beam/credentials (from `beam login`)
  BEAM_WORKSPACE_ID   env var, else ~/.config/beam/credentials
  BEAM_API_URL        env var, else https://api.beamstudio.ai

So the normal invocation carries no credentials at all:

  beam agent-builder validate

NEVER ask the user to paste an API key into the chat. If the key is missing the
command exits 3 and says to run `beam login`; if the workspace is missing it
exits 2 and says to run `beam workspace list` / `beam workspace <id>`.

--------------------------------------------------------------------------
ERRORS
--------------------------------------------------------------------------
Failures print {"ok": false, "code", "error", "next"} to stdout and exit with a
categorical status matching the `beam` shell CLI: 1 internal, 2 validation,
3 auth, 5 network. "next" names the command to run. Human progress goes to
stderr - callers must not merge it into stdout with 2>&1 before parsing.

--------------------------------------------------------------------------
QUICK START
--------------------------------------------------------------------------
  python3 beam.py validate                         # check credentials
  python3 beam.py search-tools gmail               # find integration tools
  python3 beam.py deploy spec.json                 # create agent (DRAFT)
  python3 beam.py deploy spec.json --agent-id ID   # update existing agent
  python3 beam.py deploy spec.json --publish       # create + go live
  python3 beam.py get-nodes AGENT_ID               # inspect an agent

Run `python3 beam.py --help` or `python3 beam.py <command> --help` for the
full command list. Every command prints a JSON result to stdout; progress
and diagnostics go to stderr. A non-zero exit code means the command failed.

--------------------------------------------------------------------------
SPEC FORMAT
--------------------------------------------------------------------------
See references/spec-format.md in the skill folder for the full schema.
A minimal spec:

  {
    "agentName": "My Agent",
    "agentDescription": "What it does",
    "nodes": [
      { "key": "entry", "name": "Entry", "objective": "Entry Node",
        "is_entry": true, "edges": [{ "target": "do-work" }] },
      { "key": "do-work", "name": "Do Work", "objective": "Process input",
        "prompt": "## Role:\n...\n## Task:\n...\n## Context:\n```\n{input}\n```\n## Rules:\n1. ...",
        "input_params": [{ "name": "input", "description": "...",
                           "type": "string", "fill_type": "ai_fill", "position": 0 }],
        "output_params": [{ "name": "result", "description": "...",
                            "type": "string", "position": 0 }],
        "edges": [] }
    ],
    "integrations": []
  }
"""

import argparse
import concurrent.futures
import copy
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

DEFAULT_NODE_MODEL = "BEDROCK_CLAUDE_SONNET_4"
HTTP_TIMEOUT = 120
MAX_PARALLEL = 8


class BeamError(Exception):
    """Any expected, user-facing failure (bad input, API error, missing creds).

    Carries a machine-branchable `code` and, wherever possible, the concrete
    `next_step` to take. Codes and the exit codes they map to match the `beam`
    shell CLI, so an agent can branch the same way against either tool.
    """

    def __init__(self, message, code="internal_error", next_step=None):
        super().__init__(message)
        self.code = code
        self.next_step = next_step


# code -> process exit status (mirrors bin/beam: 1 internal, 2 validation,
# 3 auth, 5 network). Anything unmapped is an internal error.
EXIT_CODES = {
    "internal_error": 1,
    "validation_error": 2,
    "auth_error": 3,
    "network_error": 5,
    "api_error": 5,
}


# ===========================================================================
# Credentials
# ===========================================================================

DEFAULT_API_URL = "https://api.beamstudio.ai"


def _creds_file_values():
    """Read BEAM_* values from the `beam` CLI's credentials file, if present.

    The CLI already stores the key and workspace after `beam login`; reading
    them here means the agent never has to ask the user to paste an API key
    into the chat (which the plugin's setup skill explicitly forbids).
    Parsed line by line - the file is never sourced or executed.
    """
    config_dir = os.environ.get("BEAM_CONFIG_DIR") or os.path.expanduser("~/.config/beam")
    path = os.path.join(config_dir, "credentials")
    values = {}
    try:
        with open(path) as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, _, value = line.partition("=")
                values[name.strip()] = value.strip()
    except OSError:
        pass
    return values


def resolve_creds():
    """Return (api_key, workspace_id, base_url).

    Resolution order, first hit wins:
      1. environment variables (explicit caller intent)
      2. ~/.config/beam/credentials, written by `beam login`
      3. for the URL only: the public Beam API

    Never ask the user to paste an API key into the chat - if nothing resolves,
    the fix is `beam login`, which stores it once for the CLI and this script.
    """
    stored = _creds_file_values()
    api_key = os.environ.get("BEAM_API_KEY", "").strip() or stored.get("BEAM_API_KEY", "")
    workspace_id = (os.environ.get("BEAM_WORKSPACE_ID", "").strip()
                    or stored.get("BEAM_WORKSPACE_ID", ""))
    base_url = os.environ.get("BEAM_API_URL", "").strip() or DEFAULT_API_URL

    if not api_key:
        raise BeamError(
            "Not signed in to Beam.",
            code="auth_error",
            next_step="Run `beam login` in a terminal (it prompts for the key without "
                      "echoing it). Do not ask the user to paste the key into the chat.",
        )
    if not workspace_id:
        raise BeamError(
            "No Beam workspace selected.",
            code="validation_error",
            next_step="Run `beam workspace list <search>` to find the right one, then "
                      "`beam workspace <id>`. Do not guess - picking the wrong workspace "
                      "makes the agent list look empty.",
        )
    return api_key, workspace_id, base_url.rstrip("/")


# ===========================================================================
# HTTP layer (stdlib urllib)
# ===========================================================================

def _http(method, url, headers, body=None, params=None, timeout=HTTP_TIMEOUT):
    """Perform an HTTP request; return parsed JSON (or {} when the body is empty)."""
    if params:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        url = url + ("&" if "?" in url else "?") + query
    data = None
    headers = dict(headers)
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        path = urllib.parse.urlparse(url).path
        if exc.code in (401, 403):
            raise BeamError(
                f"Authentication failed ({exc.code}) on {path}. "
                f"Your Beam API key may be invalid or expired. {detail}",
                code="auth_error",
                next_step="Run `beam login` with a fresh key from app.beam.ai -> "
                          "Personal settings -> API Keys, then retry.",
            )
        raise BeamError(
            f"{method} {path} failed ({exc.code}): {detail}",
            code="api_error",
            next_step="Check the request payload against references/spec-format.md; "
                      "if it looks right, run `beam doctor`.",
        )
    except urllib.error.URLError as exc:
        raise BeamError(
            f"{method} {url} failed: cannot reach the Beam API ({exc.reason}).",
            code="network_error",
            next_step="Check your connection and BEAM_API_URL, then run `beam doctor`.",
        )
    except (TimeoutError, OSError) as exc:
        raise BeamError(f"{method} {url} failed: {exc}", code="network_error",
                        next_step="Retry; if it persists, run `beam doctor`.")
    if not text.strip():
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}


def _api_headers(api_key, workspace_id):
    return {"x-api-key": api_key, "current-workspace-id": workspace_id}


class Api:
    """Thin client carrying credentials so commands stay terse."""

    def __init__(self, api_key, workspace_id, base_url):
        self.api_key = api_key
        self.workspace_id = workspace_id
        self.base = base_url
        self._bearer = None
        self._bearer_expires = 0

    # -- x-api-key endpoints (agent-graphs, tools) --------------------------
    def get(self, path, params=None):
        return _http("GET", self.base + path,
                     _api_headers(self.api_key, self.workspace_id), params=params)

    def post(self, path, body):
        return _http("POST", self.base + path,
                     _api_headers(self.api_key, self.workspace_id), body=body)

    def put(self, path, body):
        return _http("PUT", self.base + path,
                     _api_headers(self.api_key, self.workspace_id), body=body)

    def patch(self, path, body=None):
        return _http("PATCH", self.base + path,
                     _api_headers(self.api_key, self.workspace_id), body=body)

    # -- Bearer-JWT endpoints (triggers, webhooks) --------------------------
    def _bearer_token(self):
        """Triggers/webhooks need a JWT; exchange the API key and cache it."""
        if self._bearer and time.time() < self._bearer_expires - 300:
            return self._bearer
        try:
            req = urllib.request.Request(
                self.base + "/auth/access-token",
                data=json.dumps({"apiKey": self.api_key}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            raise BeamError(f"Could not obtain a Bearer token ({exc.code}): {detail}")
        except urllib.error.URLError as exc:
            raise BeamError(f"Could not reach {self.base}/auth/access-token: {exc.reason}")
        token = data.get("idToken")
        if not token:
            raise BeamError("auth/access-token did not return an idToken.")
        self._bearer = token
        self._bearer_expires = time.time() + 55 * 60
        return token

    def _bearer_headers(self):
        return {"Authorization": "Bearer " + self._bearer_token(),
                "current-workspace-id": self.workspace_id}

    def t_get(self, path, params=None):
        return _http("GET", self.base + path, self._bearer_headers(), params=params)

    def t_post(self, path, body):
        return _http("POST", self.base + path, self._bearer_headers(), body=body)

    def t_patch(self, path, body):
        return _http("PATCH", self.base + path, self._bearer_headers(), body=body)

    def t_delete(self, path):
        return _http("DELETE", self.base + path, self._bearer_headers())


def _parallel(fn, items):
    """Run fn over items concurrently, preserving order. Used for batch GETs."""
    items = list(items)
    if not items:
        return []
    if len(items) == 1:
        return [fn(items[0])]
    workers = min(MAX_PARALLEL, len(items))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(fn, items))


# ===========================================================================
# Helpers
# ===========================================================================

def _g():
    return str(uuid.uuid4())


def _to_camel(name):
    """'Send Email' -> 'SendEmail'. Mirrors the platform's toCamel exactly."""
    spaced = re.sub(r"[^a-zA-Z0-9]", " ", name or "")
    upped = re.sub(r"\b\w", lambda m: m.group(0).upper(), spaced)
    return upped.replace(" ", "")


def _tool_function_name(tool_name):
    return "GPTAction_Custom_" + _to_camel(tool_name or "")


def _provider_priority(provider):
    """Sort key for integration tools: nango first, then pipedream, then rest."""
    p = (provider or "").lower()
    if "nango" in p:
        return 0
    if "pipedream" in p:
        return 1
    return 2


def _coerce_fallback_models(value):
    """The API wants fallbackModels as a comma-separated string with no spaces
    (or null). Accept a spec value that is a list, a string, or None."""
    if value is None or value == "":
        return None
    if isinstance(value, (list, tuple)):
        parts = [str(v).strip() for v in value if str(v).strip()]
        return ",".join(parts) or None
    return str(value).replace(" ", "") or None


def _read_json_file(path, label="file"):
    p = Path(path)
    if not p.is_file():
        raise BeamError(f"{label} not found: {path}")
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError as exc:
        raise BeamError(f"{label} is not valid JSON ({path}): {exc}")


def _read_text_file(path, label="file"):
    p = Path(path)
    if not p.is_file():
        raise BeamError(f"{label} not found: {path}")
    return p.read_text()


def _resolve_condition_group_refs(groups, node_ids):
    """Resolve spec-key references inside rule_based condition_groups to UUIDs.

    sourceNodeKey -> sourceNodeId, comparisonNodeKey -> comparisonNodeId.
    A rule that already carries a UUID is left untouched.
    """
    if not isinstance(groups, list):
        return groups
    out = []
    for group in groups:
        if not isinstance(group, dict):
            out.append(group)
            continue
        new_group = dict(group)
        rules = group.get("rules")
        if isinstance(rules, list):
            new_rules = []
            for rule in rules:
                if not isinstance(rule, dict):
                    new_rules.append(rule)
                    continue
                r = dict(rule)
                if r.get("sourceNodeKey") and not r.get("sourceNodeId"):
                    key = r["sourceNodeKey"]
                    if key not in node_ids:
                        raise BeamError(
                            f"condition_groups: sourceNodeKey '{key}' is not a node key. "
                            f"Available: {sorted(node_ids)}"
                        )
                    r["sourceNodeId"] = node_ids[key]
                    r.pop("sourceNodeKey", None)
                if r.get("comparisonNodeKey") and not r.get("comparisonNodeId"):
                    key = r["comparisonNodeKey"]
                    if key not in node_ids:
                        raise BeamError(
                            f"condition_groups: comparisonNodeKey '{key}' is not a node key. "
                            f"Available: {sorted(node_ids)}"
                        )
                    r["comparisonNodeId"] = node_ids[key]
                    r.pop("comparisonNodeKey", None)
                new_rules.append(r)
            new_group["rules"] = new_rules
        out.append(new_group)
    return out


def _resolve_wait_node_refs(config, node_ids):
    """Resolve a waitingNode's linkedNodeKey (spec key) to linkedAgentGraphNodeId."""
    if not isinstance(config, dict) or not config.get("linkedNodeKey"):
        return config
    out = dict(config)
    if out.get("linkedAgentGraphNodeId"):
        out.pop("linkedNodeKey", None)
        return out
    key = out["linkedNodeKey"]
    if key not in node_ids:
        raise BeamError(
            f"waitingNode: linkedNodeKey '{key}' is not a node key. "
            f"Available: {sorted(node_ids)}"
        )
    out["linkedAgentGraphNodeId"] = node_ids[key]
    out.pop("linkedNodeKey", None)
    return out


def _resolve_loop_node_refs(config, node_ids):
    """Resolve a loopingNode's nodeConfigurations spec-key references to UUIDs.

    A variable-based loop supplies linkedVariableId as "<sourceNodeKey>:<param>";
    this resolves the key to a node UUID (producing "<uuid>:<param>") and fills
    linkedAgentGraphNodeId with the same UUID. A count-based loop (iterationCount
    only) is returned unchanged.
    """
    if not isinstance(config, dict):
        return config
    out = dict(config)
    lvid = out.get("linkedVariableId")
    if isinstance(lvid, str) and ":" in lvid:
        src_key, _, param = lvid.partition(":")
        if src_key in node_ids:
            out["linkedVariableId"] = f"{node_ids[src_key]}:{param}"
            out.setdefault("linkedAgentGraphNodeId", node_ids[src_key])
    lagn = out.get("linkedAgentGraphNodeId")
    if isinstance(lagn, str) and lagn in node_ids:
        out["linkedAgentGraphNodeId"] = node_ids[lagn]
    return out


# Graph layout spacing (pixels). Tunable; explicit spec coords override these.
_LAYOUT_Y_GAP = 200
_LAYOUT_X_GAP = 400
_LAYOUT_BASE_X = 100
# A loopingNode renders as a container box wrapping its body nodes. On the Beam
# Studio canvas (React Flow) a body node carries `parentId` + `extent:'parent'`,
# so its coordinates are read RELATIVE to the loop container, not as absolute
# canvas coordinates - body nodes therefore get small in-container offsets.
# These constants mirror studio-v2's LOOP_LAYOUT (FIT_GAP, CHILD_NODE_HEIGHT,
# INTERNAL_RANK_SPACING); keep them in sync with the frontend.
_LOOP_FIT_GAP = 50      # gap between a body node and the container border
_LOOP_CHILD_H = 88      # body-node height
_LOOP_CHILD_GAP = 62    # vertical gap between stacked body nodes


def compute_layout(nodes_spec):
    """Assign each node an (x, y) so the graph reads cleanly in the UI.

    Main-flow nodes are placed in rows by their longest distance from the entry
    node (one row per depth, top to bottom; siblings spread along x). A
    `loopingNode` is a container box: its body nodes (those whose `parent`
    points at it) get coordinates RELATIVE to that container - small offsets
    inside it, since the Studio canvas positions a child node relative to its
    parent - and the loop's main-flow row is made tall enough (matching the
    frontend's container-sizing) that the node after the loop clears the box.
    The Beam API keeps whatever coordinate it is given, so a spec that omits
    coordinates would otherwise stack every node on one point.

    Returns {nodeKey: (x, y)}. A node that supplies explicit x/y in the spec is
    handled by the caller, which prefers the spec values over this result.
    """
    keys = [n["key"] for n in nodes_spec]
    key_set = set(keys)
    by_key = {n["key"]: n for n in nodes_spec}
    children = {k: [] for k in keys}
    for ns in nodes_spec:
        for edge in ns.get("edges", []) or []:
            target = edge.get("target")
            if target in key_set:
                children[ns["key"]].append(target)

    # Loop body nodes: those whose `parent` points at a loopingNode. They are
    # laid out inside their loop's container, off the main flow.
    body_of, loop_bodies = {}, {}
    for ns in nodes_spec:
        parent = ns.get("parent")
        if parent in key_set and by_key[parent].get("node_type") == "loopingNode":
            body_of[ns["key"]] = parent
            loop_bodies.setdefault(parent, []).append(ns["key"])

    # Main-flow ("spine") children: tunnel through body nodes so the loop node
    # connects straight to whatever follows the loop, keeping bodies off the spine.
    def spine_children(src):
        out, seen, stack = [], set(), list(children[src])
        while stack:
            tgt = stack.pop(0)
            if tgt in seen:
                continue
            seen.add(tgt)
            if tgt in body_of:
                stack.extend(children[tgt])
            elif tgt not in out:
                out.append(tgt)
        return out

    spine = [k for k in keys if k not in body_of]
    spine_kids = {k: spine_children(k) for k in spine}

    # Longest-path depth on the spine (capped against a malformed cyclic spec).
    depth = {k: 0 for k in spine}
    for _ in range(len(spine)):
        changed = False
        for k in spine:
            for tgt in spine_kids[k]:
                if tgt in depth and depth[tgt] < depth[k] + 1:
                    depth[tgt] = depth[k] + 1
                    changed = True
        if not changed:
            break

    rows = {}
    for ns in nodes_spec:  # spec order keeps sibling placement stable
        if ns["key"] in depth:
            rows.setdefault(depth[ns["key"]], []).append(ns["key"])

    coords = {}
    cursor_y = 0
    for row_depth in sorted(rows):
        row_keys = rows[row_depth]
        for index, key in enumerate(row_keys):
            coords[key] = (_LAYOUT_BASE_X + index * _LAYOUT_X_GAP, cursor_y)
        # Row height: a loopingNode's row must fit its whole container box so
        # the next main-flow node does not overlap it.
        row_height = _LAYOUT_Y_GAP
        for key in row_keys:
            bodies = loop_bodies.get(key)
            if not bodies:
                continue
            # Body nodes sit inside the loop container; their coordinates are
            # read relative to it, so use small in-container offsets - the
            # same ones the frontend's own loop layout would produce.
            for j, body_key in enumerate(bodies):
                coords[body_key] = (
                    _LOOP_FIT_GAP,
                    _LOOP_FIT_GAP + j * (_LOOP_CHILD_H + _LOOP_CHILD_GAP))
            # Container height = FIT_GAP + stacked bodies + FIT_GAP. Pad the
            # row by a normal node-to-node gap so the next node clears the box.
            container_h = (2 * _LOOP_FIT_GAP + len(bodies) * _LOOP_CHILD_H
                           + (len(bodies) - 1) * _LOOP_CHILD_GAP)
            row_height = max(
                row_height, container_h + _LAYOUT_Y_GAP - _LOOP_CHILD_H)
        cursor_y += row_height
    return coords


def _param_name(param):
    """Every param needs a name; say which one is wrong instead of KeyError-ing."""
    name = (param or {}).get("name")
    if not name:
        raise BeamError(
            "A parameter is missing its 'name': " + json.dumps(param)[:200],
            code="validation_error",
            next_step="Give every input/output param a 'name'. See "
                      "references/spec-format.md for the param shape.",
        )
    return name


def _payload_summary(payload):
    """One compact line per node — the full dry-run payload runs to ~5k tokens."""
    out = []
    for n in payload.get("nodes", []) or []:
        # Tools are not in the create payload by design — see integrationsToAttach.
        out.append({
            "objective": n.get("objective"),
            "nodeType": n.get("nodeType"),
            "entry": bool(n.get("isEntryNode")),
            "exit": bool(n.get("isExitNode")),
            "outgoingEdges": len(n.get("childEdges") or []),
        })
    return out


def _validate_spec(spec):
    """Catch the most common spec mistakes before any UUIDs are generated."""
    if not isinstance(spec, dict):
        raise BeamError("Spec must be a JSON object.", code="validation_error")
    if not spec.get("agentName"):
        raise BeamError("Spec is missing 'agentName'.", code="validation_error")
    nodes = spec.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise BeamError("Spec must contain a non-empty 'nodes' array.", code="validation_error")
    keys = [n.get("key") for n in nodes]
    if any(not k for k in keys):
        raise BeamError("Every node must have a non-empty 'key'.", code="validation_error")
    dupes = {k for k in keys if keys.count(k) > 1}
    if dupes:
        raise BeamError(f"Duplicate node keys: {sorted(dupes)}. Keys must be unique.", code="validation_error")
    key_set = set(keys)
    entries = [n for n in nodes if n.get("is_entry")]
    if len(entries) != 1:
        raise BeamError(f"Spec must have exactly one entry node (is_entry: true); found {len(entries)}.", code="validation_error")
    for node in nodes:
        for edge in node.get("edges", []) or []:
            target = edge.get("target")
            if target not in key_set:
                raise BeamError(
                    f"Node '{node.get('key')}' has an edge to unknown node '{target}'."
                , code="validation_error")
    by_key = {n.get("key"): n for n in nodes}
    for node in nodes:
        parent = node.get("parent")
        if parent is not None:
            if parent not in key_set:
                raise BeamError(
                    f"Node '{node.get('key')}' has parent '{parent}', which is not a node key."
                , code="validation_error")
            if by_key[parent].get("node_type") != "loopingNode":
                raise BeamError(
                    f"Node '{node.get('key')}' has parent '{parent}', but '{parent}' is "
                    f"not a loopingNode. Only a loopingNode can be a parent."
                , code="validation_error")
        if node.get("node_type") == "loopingNode":
            if node.get("is_entry"):
                raise BeamError(f"Looping node '{node.get('key')}' cannot be the entry node.", code="validation_error")
            if parent is not None:
                raise BeamError(
                    f"Looping node '{node.get('key')}' cannot itself sit inside another "
                    f"loop — loops cannot be nested."
                , code="validation_error")

    # Integrations are matched to nodes by exact 'objective' string, so a
    # duplicate silently attaches the tool to the wrong node.
    objectives = [n.get("objective") for n in nodes if n.get("objective")]
    dupe_obj = sorted({o for o in objectives if objectives.count(o) > 1})
    if dupe_obj:
        raise BeamError(
            "Duplicate node 'objective' values: " + repr(dupe_obj) + ". Integrations are "
            "matched to nodes by exact objective text, so duplicates attach the tool to "
            "the wrong node.",
            code="validation_error",
            next_step="Give each node a distinct objective, then re-run deploy.",
        )

    # Node identity on re-deploy is the DERIVED toolFunctionName; two nodes that
    # derive the same name collide and one silently replaces the other.
    derived = {}
    for node in nodes:
        fn = _tool_function_name(node.get("tool_name") or node.get("name") or "")
        derived.setdefault(fn, []).append(node.get("key"))
    collisions = {fn: ks for fn, ks in derived.items() if len(ks) > 1}
    if collisions:
        detail = "; ".join(f"{fn} <- {ks}" for fn, ks in sorted(collisions.items()))
        raise BeamError(
            "Nodes derive the same toolFunctionName: " + detail + ". Re-deploy matches "
            "nodes by this name, so they would collide.",
            code="validation_error",
            next_step="Give the colliding nodes distinct 'name' (or 'tool_name') values.",
        )


# ===========================================================================
# Payload builder - CREATE (port of buildPayload)
# ===========================================================================

def build_payload(spec, integ_outputs=None):
    """Build the POST /agent-graphs/complete payload from a fresh spec.

    `integ_outputs` maps an integration node key to the output-param names
    declared for it in the spec's `integrations` array, letting a downstream
    node `link` to an integration output (the node itself carries none).
    """
    nodes_spec = spec["nodes"]
    node_keys = [n["key"] for n in nodes_spec]

    NODE = {k: _g() for k in node_keys}
    TC = {k: _g() for k in node_keys}
    OP = {}
    for ns in nodes_spec:
        for i, op in enumerate(ns.get("output_params", []) or []):
            OP[f'{ns["key"]}.{_param_name(op)}'] = _g()
    # An integration node carries its output params in the `integrations` array,
    # not on the node. Register them (value None) so a downstream `linked` param
    # builds cleanly; the integration is not attached yet, so deploy's
    # post-attach relink step fills in the real output-param UUID. A wrong name
    # stays unresolved and `verify` flags it BROKEN.
    for nk, names in (integ_outputs or {}).items():
        for nm in names or []:
            if nm:
                OP.setdefault(f"{nk}.{nm}", None)

    layout = compute_layout(nodes_spec)

    EDGES = {}
    for ns in nodes_spec:
        for e in ns.get("edges", []) or []:
            edge = {
                "sourceAgentGraphNodeId": NODE[ns["key"]],
                "targetAgentGraphNodeId": NODE[e["target"]],
                "condition": e.get("condition", ""),
                "isAttachmentDataPulledIn": True,
            }
            if e.get("condition_groups"):
                edge["conditionGroups"] = _resolve_condition_group_refs(
                    e["condition_groups"], NODE)
            EDGES[f'{ns["key"]}->{e["target"]}'] = edge

    def child_edges(src):
        return [v for k, v in EDGES.items() if k.startswith(src + "->")]

    def parent_edges(tgt):
        return [v for k, v in EDGES.items() if k.endswith("->" + tgt)]

    def build_input_param(ip, idx=0):
        ft = ip.get("fill_type", "user_fill")
        base = {
            "position": ip.get("position", idx),
            "paramName": _param_name(ip),
            "paramDescription": ip.get("description", ""),
            "fillType": ft,
            "required": ip.get("required", True),
            "dataType": ip.get("type", "string"),
            "isArray": ip.get("is_array", False),
            "outputExample": ip.get("output_example"),
            "reloadProps": False,
            "remoteOptions": False,
            "question": None,
            "options": None,
            "paramTip": None,
            "staticValue": None,
            "linkParamOutputId": None,
            "linkedOutputParamNodeId": None,
            "linkedOutputParamName": None,
        }
        if ft == "static":
            base["staticValue"] = ip.get("static_value", "")
        elif ft == "linked":
            linked_node = ip.get("linked_node")
            linked_param = ip.get("linked_param")
            op_key = f"{linked_node}.{linked_param}"
            if op_key not in OP:
                raise BeamError(
                    f"Linked param '{op_key}' not found. "
                    f"Available output params: {sorted(OP)}"
                )
            # The graph service resolves the link from the source node id +
            # output param name. linkParamOutputId is kept for the read model
            # but is NOT read by POST /agent-graphs/complete or PUT.
            base["linkParamOutputId"] = OP[op_key]
            base["linkedOutputParamNodeId"] = NODE[linked_node]
            base["linkedOutputParamName"] = linked_param
        return base

    def build_output_param(op, node_key, idx=0):
        return {
            "id": OP[f'{node_key}.{_param_name(op)}'],
            "position": op.get("position", idx),
            "paramName": _param_name(op),
            "paramDescription": op.get("description", ""),
            "dataType": op.get("type", "string"),
            "isArray": op.get("is_array", False),
            "outputExample": op.get("output_example"),
            "agentToolConfigurationId": TC[node_key],
            "parentId": None,
            "paramPath": None,
            "typeOptions": None,
        }

    def build_tool_config(ns):
        fn = _tool_function_name(ns.get("tool_name") or ns.get("name"))
        return {
            "id": TC[ns["key"]],
            "toolFunctionName": fn,
            "toolName": ns.get("tool_name") or ns.get("name"),
            "iconSrc": None,
            "description": ns.get("tool_description", ""),
            "prompt": ns.get("prompt", ""),
            "preferredModel": ns.get("model", DEFAULT_NODE_MODEL),
            "fallbackModels": _coerce_fallback_models(ns.get("fallback_models")),
            "accuracyScore": None,
            "requiresConsent": False,
            "isMemoryTool": False,
            "memoryLookupInstruction": "",
            "isBackgroundTool": False,
            "isBatchExecutionEnabled": False,
            "isCodeExecutionEnabled": False,
            "isAvailableToWorkspace": False,
            "dynamicPropsId": None,
            "integrationProviderId": None,
            "inputParams": [build_input_param(ip, i) for i, ip in enumerate(ns.get("input_params", []) or [])],
            "outputParams": [build_output_param(op, ns["key"], i) for i, op in enumerate(ns.get("output_params", []) or [])],
        }

    def build_node(ns):
        is_entry = ns.get("is_entry", False)
        node_type = ns.get("node_type")
        criteria = ns.get("evaluation_criteria", []) or []
        if not node_type:
            node_type = "entryNode" if is_entry else "executionNode"

        node = {
            "id": NODE[ns["key"]],
            "objective": ns["objective"],
            "evaluationCriteria": criteria,
            "isEntryNode": is_entry,
            "isExitNode": False,
            "nodeType": node_type,
            "parentNodeId": NODE[ns["parent"]] if ns.get("parent") else None,
            "xCoordinate": ns["x"] if "x" in ns else layout[ns["key"]][0],
            "yCoordinate": ns["y"] if "y" in ns else layout[ns["key"]][1],
            "isEvaluationEnabled": bool(criteria),
            "isAttachmentDataPulledIn": True,
            "onError": ns.get("on_error", "STOP"),
            "enableAutoRetryWhenFailure": ns.get("enable_retry", False),
            "autoRetryCountWhenFailure": ns.get("retry_count", 1),
            "autoRetryWaitTimeWhenFailureInMs": ns.get("retry_wait_ms", 1000),
            "autoRetryWhenAccuracyLessThan": 80,
            "autoRetryLimitWhenAccuracyIsLow": 1,
            "enableAutoRetryWhenAccuracyIsLow": False,
            "autoRetryDescription": None,
            "enableAutoRetryDescription": False,
            "isEdited": False,
            "childEdges": child_edges(ns["key"]),
            "parentEdges": parent_edges(ns["key"]),
        }
        if node_type == "conditionNode":
            node["nodeConfigurations"] = ns.get("node_configurations") or {
                "conditionType": "llm_based", "llmModel": "GPT40", "fallbackModels": None}
        if node_type == "waitingNode":
            node["nodeConfigurations"] = _resolve_wait_node_refs(
                ns.get("node_configurations") or {
                    "waitType": "time_based", "timeToWaitValue": 1,
                    "timeToWaitUnit": "hours", "timeoutType": "no_timeout"},
                NODE)
        if node_type == "loopingNode":
            node["nodeConfigurations"] = _resolve_loop_node_refs(
                ns.get("node_configurations") or {"iterationCount": 1}, NODE)
        if node_type in ("executionNode", "waitingNode"):
            node["toolConfiguration"] = build_tool_config(ns)
        return node

    return {
        "agentName": spec["agentName"],
        "agentDescription": spec.get("agentDescription", ""),
        "settings": {
            "prompts": spec.get("prompts", []) or [],
            "agentPersonality": spec.get("personality", ""),
            "agentRestrictions": spec.get("restrictions", ""),
        },
        "nodes": [build_node(ns) for ns in nodes_spec],
    }


# ===========================================================================
# Payload builder - UPDATE (port of buildPayloadUpdate)
# ===========================================================================

def build_payload_update(spec, existing_graph_resp, integ_outputs=None):
    """Merge a spec onto an existing graph for PUT /agent-graphs/{agentId}.

    Existing nodes are matched by toolFunctionName: matched nodes keep their
    UUIDs and manual edits (only edges are rewired); unmatched spec nodes are
    built fresh; existing nodes absent from the spec are dropped.
    """
    nodes_spec = spec["nodes"]
    existing_nodes = (existing_graph_resp.get("graph") or {}).get("nodes", [])

    def get_fn(node):
        return (node.get("toolConfiguration") or {}).get("toolFunctionName", "")

    existing_by_fn = {
        get_fn(n): n for n in existing_nodes
        if not n.get("isEntryNode") and n.get("nodeType") not in ("conditionNode", "loopingNode")
    }
    existing_entry = next((n for n in existing_nodes if n.get("isEntryNode")), None)
    existing_conditions = [n for n in existing_nodes if n.get("nodeType") == "conditionNode"]

    # Objective is the only identity that survives tool attachment: once a node
    # has an integration, its live toolFunctionName becomes e.g.
    # GmailAction_SendEmail, which never matches the derived
    # GPTAction_Custom_<Name>. Without this fallback every integration node is
    # dropped and recreated on each re-deploy (new UUIDs, triggers cascade off).
    existing_by_objective = {
        (n.get("objective") or "").strip(): n
        for n in existing_nodes
        if not n.get("isEntryNode") and n.get("nodeType") not in ("conditionNode", "loopingNode")
        and (n.get("objective") or "").strip()
    }

    def find_existing(spec_fn, objective=None):
        if spec_fn in existing_by_fn:
            return existing_by_fn[spec_fn]
        for fn_key, node in existing_by_fn.items():
            if fn_key.startswith(spec_fn + "_"):
                return node
        if objective:
            return existing_by_objective.get(objective.strip())
        return None

    spec_fn = {
        ns["key"]: _tool_function_name(ns.get("tool_name") or ns.get("name") or "")
        for ns in nodes_spec
        if not ns.get("is_entry") and ns.get("node_type") not in ("conditionNode", "loopingNode")
    }

    # Assign node UUIDs - reuse existing where matched.
    NODE = {}
    remaining_conditions = list(existing_conditions)
    for ns in nodes_spec:
        k = ns["key"]
        if ns.get("is_entry"):
            NODE[k] = existing_entry["id"] if existing_entry else _g()
        elif ns.get("node_type") == "conditionNode":
            NODE[k] = remaining_conditions.pop(0)["id"] if remaining_conditions else _g()
        elif ns.get("node_type") == "loopingNode":
            NODE[k] = _g()
        else:
            ex = find_existing(spec_fn[k], ns.get("objective"))
            NODE[k] = ex["id"] if ex else _g()

    # For new (unmatched) execution/waiting nodes: generate TC + OP UUIDs.
    # For matched nodes: reuse the API's existing TC id and output param ids.
    TC, OP = {}, {}
    for ns in nodes_spec:
        if ns.get("is_entry") or ns.get("node_type") in ("conditionNode", "loopingNode"):
            continue
        k = ns["key"]
        ex = find_existing(spec_fn[k], ns.get("objective"))
        if ex:
            ex_tc = ex.get("toolConfiguration") or {}
            TC[k] = ex_tc.get("id") or _g()
            for op in ex_tc.get("outputParams", []) or []:
                OP[f'{k}.{op["paramName"]}'] = op["id"]
        else:
            TC[k] = _g()
            for op in ns.get("output_params", []) or []:
                OP[f'{k}.{_param_name(op)}'] = _g()
    # Register integration-node output params (see build_payload) so a
    # downstream node may `link` to them. `setdefault` keeps a reused
    # integration node's real output ids intact.
    for nk, names in (integ_outputs or {}).items():
        for nm in names or []:
            if nm:
                OP.setdefault(f"{nk}.{nm}", None)

    EDGES = {}
    for ns in nodes_spec:
        for e in ns.get("edges", []) or []:
            edge = {
                "sourceAgentGraphNodeId": NODE[ns["key"]],
                "targetAgentGraphNodeId": NODE[e["target"]],
                "condition": e.get("condition", ""),
                "isAttachmentDataPulledIn": True,
            }
            if e.get("condition_groups"):
                edge["conditionGroups"] = _resolve_condition_group_refs(
                    e["condition_groups"], NODE)
            EDGES[f'{ns["key"]}->{e["target"]}'] = edge

    def child_edges(src):
        return [v for k, v in EDGES.items() if k.startswith(src + "->")]

    def parent_edges(tgt):
        return [v for k, v in EDGES.items() if k.endswith("->" + tgt)]

    def build_ip(ip, idx=0):
        ft = ip.get("fill_type", "user_fill")
        base = {
            "position": ip.get("position", idx),
            "paramName": _param_name(ip),
            "paramDescription": ip.get("description", ""),
            "fillType": ft,
            "required": ip.get("required", True),
            "dataType": ip.get("type", "string"),
            "isArray": ip.get("is_array", False),
            "outputExample": ip.get("output_example"),
            "reloadProps": False,
            "remoteOptions": False,
            "question": None,
            "options": None,
            "paramTip": None,
            "staticValue": None,
            "linkParamOutputId": None,
            "linkedOutputParamNodeId": None,
            "linkedOutputParamName": None,
        }
        if ft == "static":
            base["staticValue"] = ip.get("static_value", "")
        elif ft == "linked":
            ln, lp = ip.get("linked_node"), ip.get("linked_param")
            op_key = f"{ln}.{lp}"
            if op_key not in OP:
                raise BeamError(
                    f"Linked param '{op_key}' not found. Available: {sorted(OP)}")
            base["linkParamOutputId"] = OP[op_key]
            base["linkedOutputParamNodeId"] = NODE.get(ln)
            base["linkedOutputParamName"] = lp
        return base

    def build_op(op, nk, idx=0):
        return {
            "id": OP[f'{nk}.{_param_name(op)}'],
            "position": op.get("position", idx),
            "paramName": _param_name(op),
            "paramDescription": op.get("description", ""),
            "dataType": op.get("type", "string"),
            "isArray": op.get("is_array", False),
            "outputExample": op.get("output_example"),
            "agentToolConfigurationId": TC[nk],
            "parentId": None,
            "paramPath": None,
            "typeOptions": None,
        }

    def build_new_condition_node(ns):
        return {
            "id": NODE[ns["key"]],
            "objective": ns.get("objective", ""),
            "evaluationCriteria": [],
            "isEntryNode": False,
            "isExitNode": False,
            "nodeType": "conditionNode",
            "nodeConfigurations": ns.get("node_configurations") or {
                "conditionType": "llm_based", "llmModel": "GPT40", "fallbackModels": None},
            "xCoordinate": ns.get("x", 0),
            "yCoordinate": ns.get("y", 300),
            "isEvaluationEnabled": False,
            "isAttachmentDataPulledIn": True,
            "onError": "STOP",
            "autoRetryWhenAccuracyLessThan": 80,
            "autoRetryLimitWhenAccuracyIsLow": 1,
            "autoRetryCountWhenFailure": 1,
            "autoRetryWaitTimeWhenFailureInMs": 1000,
            "enableAutoRetryWhenAccuracyIsLow": False,
            "enableAutoRetryWhenFailure": False,
            "isEdited": False,
            "childEdges": child_edges(ns["key"]),
            "parentEdges": parent_edges(ns["key"]),
        }

    def build_new_node(ns):
        node_type = ns.get("node_type") or "executionNode"
        criteria = ns.get("evaluation_criteria", []) or []
        node = {
            "id": NODE[ns["key"]],
            "objective": ns["objective"],
            "evaluationCriteria": criteria,
            "isEntryNode": False,
            "isExitNode": False,
            "nodeType": node_type,
            "xCoordinate": ns.get("x", 250),
            "yCoordinate": ns.get("y", 150),
            "isEvaluationEnabled": bool(criteria),
            "isAttachmentDataPulledIn": True,
            "onError": ns.get("on_error", "STOP"),
            "enableAutoRetryWhenFailure": ns.get("enable_retry", False),
            "autoRetryCountWhenFailure": ns.get("retry_count", 1),
            "autoRetryWaitTimeWhenFailureInMs": ns.get("retry_wait_ms", 1000),
            "autoRetryWhenAccuracyLessThan": 80,
            "autoRetryLimitWhenAccuracyIsLow": 1,
            "enableAutoRetryWhenAccuracyIsLow": False,
            "autoRetryDescription": None,
            "enableAutoRetryDescription": False,
            "isEdited": False,
            "childEdges": child_edges(ns["key"]),
            "parentEdges": parent_edges(ns["key"]),
        }
        if node_type == "conditionNode":
            node["nodeConfigurations"] = ns.get("node_configurations") or {
                "conditionType": "llm_based", "llmModel": "GPT40", "fallbackModels": None}
        if node_type == "waitingNode":
            node["nodeConfigurations"] = _resolve_wait_node_refs(
                ns.get("node_configurations") or {
                    "waitType": "time_based", "timeToWaitValue": 1,
                    "timeToWaitUnit": "hours", "timeoutType": "no_timeout"},
                NODE)
        if node_type == "loopingNode":
            node["nodeConfigurations"] = _resolve_loop_node_refs(
                ns.get("node_configurations") or {"iterationCount": 1}, NODE)
        if node_type in ("executionNode", "waitingNode"):
            node["toolConfiguration"] = {
                "id": TC[ns["key"]],
                "toolFunctionName": spec_fn[ns["key"]],
                "toolName": ns.get("tool_name") or ns.get("name"),
                "iconSrc": None,
                "description": ns.get("tool_description", ""),
                "prompt": ns.get("prompt", ""),
                "preferredModel": ns.get("model", DEFAULT_NODE_MODEL),
                "fallbackModels": _coerce_fallback_models(ns.get("fallback_models")),
                "accuracyScore": None,
                "requiresConsent": False,
                "isMemoryTool": False,
                "memoryLookupInstruction": "",
                "isBackgroundTool": False,
                "isBatchExecutionEnabled": False,
                "isCodeExecutionEnabled": False,
                "isAvailableToWorkspace": False,
                "dynamicPropsId": None,
                "integrationProviderId": None,
                "inputParams": [build_ip(ip, i) for i, ip in enumerate(ns.get("input_params", []) or [])],
                "outputParams": [build_op(op, ns["key"], i) for i, op in enumerate(ns.get("output_params", []) or [])],
            }
        return node

    def rebuild_linked_params(node, spec_node):
        """Reused node: re-point its linked params at the (re-resolved) UUIDs."""
        tc = node.get("toolConfiguration")
        if not tc:
            return
        spec_ips = {_param_name(ip): ip for ip in spec_node.get("input_params", []) or []}
        for collection in (tc.get("inputParams", []),
                           (tc.get("originalTool") or {}).get("inputParams", [])):
            for ip in collection or []:
                spec_ip = spec_ips.get(ip.get("paramName"))
                if spec_ip and spec_ip.get("fill_type") == "linked":
                    ln, lp = spec_ip.get("linked_node"), spec_ip.get("linked_param")
                    ip["linkParamOutputId"] = OP.get(f"{ln}.{lp}")
                    ip["linkedOutputParamNodeId"] = NODE.get(ln)
                    ip["linkedOutputParamName"] = lp
                    ip["fillType"] = "linked"

    final_nodes = []
    reused_condition_ids = set()
    for ns in nodes_spec:
        k = ns["key"]
        ce, pe = child_edges(k), parent_edges(k)
        if ns.get("is_entry"):
            if existing_entry:
                node = copy.deepcopy(existing_entry)
            else:
                node = {
                    "id": NODE[k], "objective": "Entry Node", "evaluationCriteria": [],
                    "isEntryNode": True, "isExitNode": False, "nodeType": "entryNode",
                    "xCoordinate": ns.get("x", 250), "yCoordinate": ns.get("y", 0),
                    "isEvaluationEnabled": False, "isAttachmentDataPulledIn": True,
                    "onError": "STOP", "enableAutoRetryWhenFailure": False,
                    "autoRetryCountWhenFailure": 1, "autoRetryWaitTimeWhenFailureInMs": 1000,
                    "autoRetryWhenAccuracyLessThan": 80, "autoRetryLimitWhenAccuracyIsLow": 1,
                    "enableAutoRetryWhenAccuracyIsLow": False, "autoRetryDescription": None,
                    "enableAutoRetryDescription": False, "isEdited": False,
                }
            node["childEdges"], node["parentEdges"] = ce, pe
            final_nodes.append(node)
        elif ns.get("node_type") == "conditionNode":
            node_id = NODE[k]
            existing_cond = next(
                (n for n in existing_conditions if n["id"] == node_id), None)
            if existing_cond and node_id not in reused_condition_ids:
                node = copy.deepcopy(existing_cond)
                node["childEdges"], node["parentEdges"] = ce, pe
                if ns.get("node_configurations"):
                    node["nodeConfigurations"] = ns["node_configurations"]
                reused_condition_ids.add(node_id)
                final_nodes.append(node)
            else:
                final_nodes.append(build_new_condition_node(ns))
        elif ns.get("node_type") == "loopingNode":
            final_nodes.append(build_new_node(ns))
        else:
            ex = find_existing(spec_fn[k], ns.get("objective"))
            if ex:
                node = copy.deepcopy(ex)
                node["childEdges"], node["parentEdges"] = ce, pe
                rebuild_linked_params(node, ns)
                final_nodes.append(node)
            else:
                final_nodes.append(build_new_node(ns))

    # Lay nodes out by graph depth so the UI does not stack them on one spot.
    # A spec node that supplies explicit x and y keeps them; this also re-tidies
    # reused nodes on a full redeploy.
    layout = compute_layout(nodes_spec)
    for ns, node in zip(nodes_spec, final_nodes):
        if "x" in ns and "y" in ns:
            node["xCoordinate"], node["yCoordinate"] = ns["x"], ns["y"]
        else:
            node["xCoordinate"], node["yCoordinate"] = layout[ns["key"]]
        node["parentNodeId"] = NODE[ns["parent"]] if ns.get("parent") else None

    return {
        "agentName": spec["agentName"],
        "agentDescription": spec.get("agentDescription", ""),
        "settings": {
            "prompts": spec.get("prompts", []) or [],
            "agentPersonality": spec.get("personality", ""),
            "agentRestrictions": spec.get("restrictions", ""),
        },
        "nodes": final_nodes,
    }


# ===========================================================================
# Shared API operations
# ===========================================================================

def _clean_integration_param(ip):
    """Normalize an integration tool input param for the update-node payload.

    Drops the spec-only `linked_from_*` keys, and accepts the snake_case forms
    (`static_value`, `fill_type`) by mapping them to the camelCase the API
    expects (`staticValue`, `fillType`). This makes a static integration param
    work whether the spec author used snake_case (as on custom-node params) or
    camelCase - the API silently drops an unrecognized key, which previously
    lost static values.
    """
    p = dict(ip)
    p.pop("linked_from_key", None)
    p.pop("linked_from_param", None)
    if p.get("fill_type") is not None and not p.get("fillType"):
        p["fillType"] = p["fill_type"]
    p.pop("fill_type", None)
    if p.get("static_value") is not None and p.get("staticValue") is None:
        p["staticValue"] = p["static_value"]
    p.pop("static_value", None)
    return p


def do_verify(api, agent_id, node_list=None):
    """Verify every input param across the graph is wired: linked params have a
    source, and static params have a non-empty value.

    `node_list` is an optional pre-fetched `/nodes/lite` node array. The deploy
    pipeline already holds one, so passing it skips a redundant fetch.
    """
    if node_list is None:
        node_list = api.get(f"/agent-graphs/{agent_id}/nodes/lite").get("nodes", []) or []
    details = _parallel(
        lambda n: api.get(f'/agent-graphs/{agent_id}/nodes/{n["id"]}'), node_list)
    all_ok = True
    links = []
    for detail in details:
        tc = detail.get("toolConfiguration") or {}
        for ip in tc.get("inputParams", []) or []:
            ft = ip.get("fillType")
            if ft == "linked":
                link_id = ip.get("linkParamOutputId")
                ok = bool(link_id)
                links.append({
                    "status": "OK" if ok else "BROKEN", "fillType": "linked",
                    "nodeName": detail.get("objective", "?"),
                    "paramName": ip.get("paramName"),
                    "detail": link_id or "linked param has no source (linkParamOutputId is null)",
                })
            elif ft == "static":
                val = ip.get("staticValue")
                ok = val is not None and val != ""
                links.append({
                    "status": "OK" if ok else "BROKEN", "fillType": "static",
                    "nodeName": detail.get("objective", "?"),
                    "paramName": ip.get("paramName"),
                    "detail": "static value set" if ok
                    else "static param has an empty staticValue - the value was dropped",
                })
            else:
                continue
            if not ok:
                all_ok = False
    return all_ok, links


# ===========================================================================
# Commands - read / inspect
# ===========================================================================

def cmd_validate(api, args):
    # Must FAIL loudly: this previously returned {"valid": false} wrapped in
    # {"ok": true} with exit 0, so an agent branching on $? treated bad
    # credentials as success and carried on into the build.
    api.get("/agent", params={"searchKeyword": "_validate_"})
    return {"valid": True, "baseUrl": api.base, "workspaceId": api.workspace_id}


def cmd_search_tools(api, args):
    params = {"type": "custom_integration_tool", "searchKeyword": args.keyword}
    if args.wait_only:
        params["allowWaiting"] = "true"
    data = api.get("/tool/active-tools", params=params)
    raw = data.get("tools", []) or []
    raw.sort(key=lambda t: _provider_priority(t.get("integrationProvider")))
    tools = []
    for t in raw:
        meta = t.get("meta") or {}
        if args.wait_only and not t.get("allowWaiting"):
            continue
        # --managed-only drops prompt-only tools (custom_gpt_tool / gpt_tool),
        # keeping every real beam_tool - including Beam-native tools like web
        # search that carry no integrationProvider. Filtering on the provider
        # instead would wrongly hide those real tools.
        if args.managed_only and t.get("type") in ("custom_gpt_tool", "gpt_tool"):
            continue
        # Only the fields the agent needs to pick and configure a tool. The
        # tool's own preferredModel / iconSrc are intentionally omitted - the
        # node should use a current model (see node-authoring.md) and the
        # integration's icon_src is left null.
        tools.append({
            "toolFunctionName": t.get("toolFunctionName", ""),
            "toolName": t.get("toolName", ""),
            "description": meta.get("description", ""),
            "requiredArgs": meta.get("required_extracted_args", []),
            "optionalArgs": meta.get("optional_extracted_args", []),
            "requiresConsent": meta.get("requires_consent", t.get("requiresConsent")),
            "integrationProvider": t.get("integrationProvider"),
            "integrationIdentifier": t.get("integrationIdentifier"),
            "isIntegrationConnected": t.get("isIntegrationConnected", False),
            "toolType": t.get("type", ""),
            "allowWaiting": t.get("allowWaiting", False),
        })
    hint = ("Prefer integrationProvider=nango_cloud, then pipedream. A beam_tool "
            "with no integrationProvider (e.g. web search) is still a real tool. "
            "If only custom_gpt_tools match, ask the user before using one.")
    if args.managed_only and not tools:
        hint = ("No real (beam_tool) tool matched this keyword. Try a different "
                "keyword, or ask the user before using a prompt-only "
                "custom_gpt_tool - re-run without --managed-only to see them.")
    return {"tools": tools, "total": len(tools), "hint": hint}


def cmd_search_agents(api, args):
    data = api.get("/agent", params={"searchKeyword": args.keyword})
    raw = data.get("data") or data.get("agents") or []
    agents = [{"id": a.get("id"), "name": a.get("name")} for a in raw]
    return {"agents": agents, "total": len(agents)}


def cmd_get_nodes(api, args):
    data = api.get(f"/agent-graphs/{args.agent_id}/nodes/lite")
    return {
        "agentName": data.get("agentName"),
        "graphId": data.get("graphId"),
        "nodes": [{"id": n["id"], "objective": n.get("objective")}
                  for n in data.get("nodes", []) or []],
    }


def _node_summary(detail):
    """Compact, link-focused view of a node - the fields needed to wire a graph."""
    tc = detail.get("toolConfiguration") or {}
    summary = {
        "id": detail.get("id"),
        "objective": detail.get("objective"),
        "nodeType": detail.get("nodeType"),
        "isEntryNode": detail.get("isEntryNode", False),
        "tool": {
            "toolFunctionName": tc.get("toolFunctionName"),
            "toolName": tc.get("toolName"),
            "preferredModel": tc.get("preferredModel"),
        },
        "inputParams": [
            {"paramName": ip.get("paramName"), "fillType": ip.get("fillType"),
             "dataType": ip.get("dataType"), "required": ip.get("required"),
             "linkParamOutputId": ip.get("linkParamOutputId"),
             "staticValue": ip.get("staticValue")}
            for ip in tc.get("inputParams", []) or []
        ],
        "outputParams": [
            {"paramName": op.get("paramName"), "id": op.get("id"),
             "dataType": op.get("dataType")}
            for op in tc.get("outputParams", []) or []
        ],
        "childEdges": [
            {"id": e.get("id"), "target": e.get("targetAgentGraphNodeId"),
             "condition": e.get("condition", "")}
            for e in detail.get("childEdges", []) or []
        ],
        "parentEdges": [
            {"id": e.get("id"), "source": e.get("sourceAgentGraphNodeId")}
            for e in detail.get("parentEdges", []) or []
        ],
    }
    if detail.get("nodeConfigurations"):
        summary["nodeConfigurations"] = detail["nodeConfigurations"]
    if detail.get("parentNodeId"):
        summary["parentNodeId"] = detail["parentNodeId"]
    if tc.get("originalTool", {}).get("allowWaiting") is not None:
        summary["tool"]["allowWaiting"] = tc["originalTool"]["allowWaiting"]
    return summary


def cmd_get_node(api, args):
    ids = args.node_ids
    details = _parallel(
        lambda nid: api.get(f"/agent-graphs/{args.agent_id}/nodes/{nid}"), ids)
    if args.full:
        return {"nodes": details} if len(ids) > 1 else {"node": details[0]}
    summaries = [_node_summary(d) for d in details]
    return {"nodes": summaries} if len(ids) > 1 else {"node": summaries[0]}


def cmd_get_graph(api, args):
    data = api.get(f"/agent-graphs/{args.agent_id}")
    if args.full:
        return {"graph": data}
    graph = data.get("graph") or {}
    agent = graph.get("agent") or {}
    return {
        "agentId": graph.get("agentId") or agent.get("id"),
        "agentName": agent.get("name"),
        "graphId": graph.get("id"),
        "isDraft": graph.get("isDraft"),
        "isPublished": graph.get("isPublished"),
        "nodes": [_node_summary(n) for n in graph.get("nodes", []) or []],
    }


def cmd_verify_links(api, args):
    all_ok, links = do_verify(api, args.agent_id)
    return {"allOk": all_ok, "links": links}


# ===========================================================================
# Commands - create / deploy
# ===========================================================================

def cmd_create(api, args):
    spec = _read_json_file(args.spec_file, "Spec file")
    _validate_spec(spec)
    if args.agent_id:
        existing = api.get(f"/agent-graphs/{args.agent_id}")
        payload = build_payload_update(spec, existing)
    else:
        payload = build_payload(spec)
    if args.dry_run and getattr(args, "summary", False):
        return {"dryRun": True, "summary": True, "nodeCount": len(payload["nodes"]),
                "nodes": _payload_summary(payload)}
    if args.dry_run:
        return {"dryRun": True, "nodeCount": len(payload["nodes"]), "payload": payload}
    if args.agent_id:
        result = api.put(f"/agent-graphs/{args.agent_id}", payload)
    else:
        result = api.post("/agent-graphs/complete", payload)
    return {
        "agentId": result.get("agentId"),
        "agentName": result.get("agentName"),
        "draftGraphId": result.get("draftGraphId"),
        "activeGraphId": result.get("activeGraphId"),
        "note": "Saved as a DRAFT. Not live until published.",
    }


def cmd_deploy(api, args):
    """Full pipeline: create/update -> attach integrations -> relink -> verify -> publish."""
    spec = _read_json_file(args.spec_file, "Spec file")
    _validate_spec(spec)
    integrations = spec.get("integrations", []) or []
    # Output-param names each integration declares - lets a downstream node
    # `link` to an integration output (resolved by the relink step post-attach).
    integ_outputs = {
        integ["node_key"]: [op.get("paramName") or op.get("name")
                            for op in (integ.get("output_params") or [])]
        for integ in integrations if integ.get("node_key")
    }
    spec_no_integ = {k: v for k, v in spec.items() if k != "integrations"}
    spec_no_integ["integrations"] = []
    steps = []

    def progress(msg):
        print(f"[beam.deploy] {msg}", file=sys.stderr)

    # Step 1 - create or update --------------------------------------------
    if args.agent_id:
        existing = api.get(f"/agent-graphs/{args.agent_id}")
        payload = build_payload_update(spec_no_integ, existing, integ_outputs)
    else:
        payload = build_payload(spec_no_integ, integ_outputs)

    if args.dry_run and getattr(args, "summary", False):
        return {"dryRun": True, "summary": True,
                "nodeCount": len(payload["nodes"]),
                "integrationCount": len(integrations),
                "nodes": _payload_summary(payload),
                "integrationsToAttach": [i.get("node_key") for i in integrations],
                "note": "Counts only. Re-run without --summary for the full payload."}
    if args.dry_run:
        return {"dryRun": True, "nodeCount": len(payload["nodes"]),
                "integrationCount": len(integrations), "payload": payload,
                "integrationsToAttach": integrations,
                "note": ("'payload' is POSTed to create the agent. Integration "
                         "tool configs are NOT inside it by design - after "
                         "creation each 'integrationsToAttach' entry is PATCHed "
                         "onto its node_key and links are re-resolved.")}

    if args.agent_id:
        result = api.put(f"/agent-graphs/{args.agent_id}", payload)
    else:
        result = api.post("/agent-graphs/complete", payload)
    agent_id = result.get("agentId")
    graph_id = result.get("draftGraphId")
    if not agent_id or not graph_id:
        raise BeamError(f"Create/update did not return agentId/draftGraphId. Response: {result}")
    verb = "Updated" if args.agent_id else "Created"
    progress(f"{verb} agent {agent_id} ({len(payload['nodes'])} nodes), draft graph {graph_id}")
    steps.append({"step": "create_or_update", "status": "ok",
                  "detail": f"{verb} agent with {len(payload['nodes'])} nodes."})

    # No integrations - verify, optionally publish, done.
    if not integrations:
        all_ok, links = do_verify(api, agent_id)
        steps.append({"step": "verify", "status": "ok" if all_ok else "warning",
                      "detail": "All links OK" if all_ok else "Some linked params are broken."})
        published = False
        if args.publish:
            api.patch(f"/agent-graphs/{graph_id}/publish")
            published = True
            steps.append({"step": "publish", "status": "ok", "detail": f"Published {graph_id}"})
            progress("Published.")
        return _deploy_result(agent_id, graph_id, published, all_ok, steps)

    # Step 2 - map spec node keys to created node IDs (matched by objective).
    nodes_data = api.get(f"/agent-graphs/{agent_id}/nodes/lite")
    key_to_id = {}
    for sn in spec["nodes"]:
        for nn in nodes_data.get("nodes", []) or []:
            if nn.get("objective") == sn.get("objective"):
                key_to_id[sn["key"]] = nn["id"]
                break
    steps.append({"step": "map_nodes", "status": "ok",
                  "detail": f"Mapped {len(key_to_id)} node keys to IDs."})
    progress(f"Mapped {len(key_to_id)} nodes.")

    # Step 3 - attach integration tools (parallel) -------------------------
    integ_source_ids = set()
    for integ in integrations:
        for ip in integ.get("input_params", []) or []:
            if ip.get("fillType") == "linked" and ip.get("linked_from_key"):
                sid = key_to_id.get(ip["linked_from_key"])
                if sid:
                    integ_source_ids.add(sid)
    source_details = {}
    for sid, detail in zip(
            integ_source_ids,
            _parallel(lambda s: api.get(f"/agent-graphs/{agent_id}/nodes/{s}"),
                      integ_source_ids)):
        source_details[sid] = detail

    def attach(integ):
        node_key = integ["node_key"]
        node_id = key_to_id.get(node_key)
        if not node_id:
            return {"step": "attach_tool", "status": "warning",
                    "detail": f"node_key '{node_key}' not in graph, skipped."}
        clean_params = []
        for ip in integ.get("input_params", []) or []:
            p = _clean_integration_param(ip)
            ft = ip.get("fillType") or ip.get("fill_type")
            if ft == "linked" and ip.get("linked_from_key"):
                sid = key_to_id.get(ip["linked_from_key"])
                src = source_details.get(sid) if sid else None
                if src:
                    for op in (src.get("toolConfiguration") or {}).get("outputParams", []) or []:
                        if op.get("paramName") == ip.get("linked_from_param"):
                            p["linkParamOutputId"] = op["id"]
                            break
            clean_params.append(p)
        objective = next((sn["objective"] for sn in spec["nodes"]
                          if sn["key"] == node_key), "")
        node_payload = {
            "id": node_id, "objective": objective,
            "isAttachmentDataPulledIn": True, "evaluationCriteria": [],
            "toolConfiguration": {
                "toolFunctionName": integ["tool_function_name"],
                "toolName": integ["tool_name"],
                "shortDescription": integ.get("description", ""),
                "description": integ.get("description", ""),
                "iconSrc": integ.get("icon_src"),
                "preferredModel": integ.get("preferred_model"),
                "requiresConsent": integ.get("requires_consent", False),
                "isMemoryTool": False, "isBackgroundTool": False,
                "isBatchExecutionEnabled": False, "integrationProviderId": None,
                "inputParams": clean_params,
                "outputParams": integ.get("output_params", []) or [],
            },
        }
        api.patch_body = None
        _http("PATCH", api.base + "/agent-graphs/update-node",
              _api_headers(api.api_key, api.workspace_id),
              body={"agentId": agent_id, "graphId": graph_id, "node": node_payload})
        return {"step": "attach_tool", "status": "ok",
                "detail": f"Attached {integ['tool_function_name']} to '{node_key}'."}

    steps.extend(_parallel(attach, integrations))
    progress(f"Attached {len(integrations)} integration tool(s).")

    # Step 4 - re-link every node with linked params (parallel) ------------
    # The API regenerates output-param UUIDs on attach, so all linked inputs
    # must be re-pointed at the live UUIDs.
    relink_targets = []
    needed_ids = set()
    for sn in spec["nodes"]:
        if sn.get("is_entry"):
            continue
        linked = [ip for ip in sn.get("input_params", []) or []
                  if ip.get("fill_type") == "linked" and ip.get("linked_node")]
        if not linked:
            continue
        nid = key_to_id.get(sn["key"])
        if not nid:
            continue
        relink_targets.append((sn, nid))
        needed_ids.add(nid)
        for ip in linked:
            sid = key_to_id.get(ip["linked_node"])
            if sid:
                needed_ids.add(sid)

    detail_cache = {}
    for nid, detail in zip(
            needed_ids,
            _parallel(lambda n: api.get(f"/agent-graphs/{agent_id}/nodes/{n}"), needed_ids)):
        detail_cache[nid] = detail

    relink_ops = []
    for sn, node_id in relink_targets:
        detail = detail_cache.get(node_id, {})
        tc = detail.get("toolConfiguration") or {}
        changed = False
        updated_params = []
        for ip in tc.get("inputParams", []) or []:
            spec_ip = next((s for s in sn.get("input_params", []) or []
                            if s["name"] == ip.get("paramName")), None)
            if spec_ip and spec_ip.get("fill_type") == "linked" and spec_ip.get("linked_node"):
                src = detail_cache.get(key_to_id.get(spec_ip["linked_node"]))
                if src:
                    for op in (src.get("toolConfiguration") or {}).get("outputParams", []) or []:
                        if op.get("paramName") == spec_ip.get("linked_param"):
                            if ip.get("linkParamOutputId") != op["id"]:
                                ip["linkParamOutputId"] = op["id"]
                                changed = True
                            break
            updated_params.append(ip)
        if changed:
            relink_ops.append((sn["key"], {
                "id": node_id, "objective": detail.get("objective", ""),
                "isAttachmentDataPulledIn": True,
                "evaluationCriteria": detail.get("evaluationCriteria", []),
                "toolConfiguration": {**tc, "inputParams": updated_params},
            }))

    def relink(op):
        key, node_payload = op
        _http("PATCH", api.base + "/agent-graphs/update-node",
              _api_headers(api.api_key, api.workspace_id),
              body={"agentId": agent_id, "graphId": graph_id, "node": node_payload})
        return {"step": "relink", "status": "ok", "detail": f"Re-linked '{key}'."}

    steps.extend(_parallel(relink, relink_ops))
    if relink_ops:
        progress(f"Re-linked {len(relink_ops)} downstream node(s).")

    # Step 5 - verify (reuse the node list fetched in step 2) --------------
    all_ok, links = do_verify(api, agent_id, nodes_data.get("nodes", []) or [])
    broken = [f'{l["nodeName"]}.{l["paramName"]}' for l in links if l["status"] == "BROKEN"]
    steps.append({"step": "verify", "status": "ok" if all_ok else "warning",
                  "detail": "All links OK" if all_ok else f"Broken links: {', '.join(broken)}"})
    progress("Verified links: " + ("all OK" if all_ok else f"{len(broken)} broken"))

    # Step 6 - publish -----------------------------------------------------
    published = False
    if args.publish:
        api.patch(f"/agent-graphs/{graph_id}/publish")
        published = True
        steps.append({"step": "publish", "status": "ok", "detail": f"Published {graph_id}"})
        progress("Published.")

    return _deploy_result(agent_id, graph_id, published, all_ok, steps)


def _deploy_result(agent_id, graph_id, published, verified, steps):
    note = ("Agent is LIVE (published)." if published else
            "Agent saved as a DRAFT - it is NOT live. "
            "Ask the user before publishing; publish with: beam.py publish " + str(graph_id))
    return {"agentId": agent_id, "graphId": graph_id, "published": published,
            "verificationPassed": verified, "steps": steps, "note": note}


# ===========================================================================
# Commands - graph mutation
# ===========================================================================

def cmd_publish(api, args):
    api.patch(f"/agent-graphs/{args.graph_id}/publish")
    return {"published": True, "graphId": args.graph_id}


def cmd_attach_tool(api, args):
    tc = _read_json_file(args.toolconfig_file, "Tool-config file")
    node_payload = {
        "id": args.node_id,
        "objective": args.objective or "",
        "isAttachmentDataPulledIn": True,
        "evaluationCriteria": [],
        "toolConfiguration": {
            "toolFunctionName": tc["toolFunctionName"],
            "toolName": tc["toolName"],
            "shortDescription": tc.get("description", ""),
            "description": tc.get("description", ""),
            "iconSrc": tc.get("iconSrc"),
            "preferredModel": tc.get("preferredModel"),
            "requiresConsent": tc.get("requiresConsent", False),
            "isMemoryTool": False, "isBackgroundTool": False,
            "isBatchExecutionEnabled": False, "integrationProviderId": None,
            "inputParams": [_clean_integration_param(ip)
                            for ip in tc.get("inputParams", []) or []],
            "outputParams": tc.get("outputParams", []) or [],
        },
    }
    data = api.patch_with_body("/agent-graphs/update-node", {
        "agentId": args.agent_id, "graphId": args.graph_id, "node": node_payload})
    return {"attached": True, "node": data}


def cmd_update_node(api, args):
    payload = _read_json_file(args.node_file, "Node file")
    node_obj = payload.get("node", payload) if isinstance(payload, dict) else payload
    data = api.patch_with_body("/agent-graphs/update-node", {
        "agentId": args.agent_id, "graphId": args.graph_id, "node": node_obj})
    return {"updated": True, "node": data}


def cmd_update_node_prompt(api, args):
    """Update a node's prompt via the full-node update path, then verify it stuck.

    The dedicated /nodes/:id/prompt endpoint only updates the tool *template*
    (originalTool.prompt), not toolConfiguration.prompt - the per-graph prompt
    the node actually runs - so it appears to succeed while changing nothing.
    This fetches the node, sets the prompt on the tool configuration, PATCHes
    via update-node, and re-reads to confirm the change persisted.
    """
    prompt = _read_text_file(args.prompt_file, "Prompt file")
    node = api.get(f"/agent-graphs/{args.agent_id}/nodes/{args.node_id}")
    node.pop("agentGraph", None)
    tc = node.get("toolConfiguration")
    if not tc:
        raise BeamError(
            f"Node {args.node_id} has no toolConfiguration - it has no prompt to "
            f"update (entry, condition, and looping nodes have no prompt)."
        )
    tc["prompt"] = prompt
    original = tc.get("originalTool")
    if isinstance(original, dict):
        original["prompt"] = prompt
        if isinstance(original.get("meta"), dict):
            original["meta"]["prompt"] = prompt
    nodes_data = api.get(f"/agent-graphs/{args.agent_id}/nodes/lite")
    graph_id = nodes_data.get("graphId")
    if not graph_id:
        raise BeamError("Could not resolve the draft graph id for this agent.")
    api.patch_with_body("/agent-graphs/update-node", {
        "agentId": args.agent_id, "graphId": graph_id, "node": node})
    check = api.get(f"/agent-graphs/{args.agent_id}/nodes/{args.node_id}")
    saved = (check.get("toolConfiguration") or {}).get("prompt")
    if saved != prompt:
        raise BeamError(
            "Prompt update did not persist - toolConfiguration.prompt still "
            "differs after the update. No change was made."
        )
    published = False
    if args.publish:
        api.patch(f"/agent-graphs/{graph_id}/publish")
        published = True
    return {"updated": True, "verified": True, "nodeId": args.node_id,
            "graphId": graph_id, "published": published}


def cmd_update_node_params(api, args):
    body = {}
    if args.input_params_file:
        body["inputParams"] = _read_json_file(args.input_params_file, "Input-params file")
    if args.output_params_file:
        body["outputParams"] = _read_json_file(args.output_params_file, "Output-params file")
    if not body:
        raise BeamError("Provide --input-params-file and/or --output-params-file.")
    api.patch(f"/agent-graphs/{args.agent_id}/nodes/{args.node_id}/input-output-params",
              body=body)
    graph_id = _maybe_publish(api, args)
    return {"updated": True, "nodeId": args.node_id, "published": bool(args.publish),
            "graphId": graph_id}


def cmd_update_edge(api, args):
    body = {"isAttachmentDataPulledIn": True}
    if args.condition is not None:
        body["condition"] = args.condition
    if args.condition_groups_file:
        body["conditionGroups"] = _read_json_file(
            args.condition_groups_file, "Condition-groups file")
    api.put(f"/agent-graphs/update-edge/{args.edge_id}", body)
    return {"updated": True, "edgeId": args.edge_id}


def cmd_update_metadata(api, args):
    data = api.get(f"/agent-graphs/{args.agent_id}")
    graph = data.get("graph") or {}
    agent = graph.get("agent") or {}
    # Only send the metadata fields being changed; nodes are required by the
    # update DTO. agentName must carry the real existing name (the GET nests it
    # at graph.agent.name) or a rename to it would blank the agent.
    payload = {"nodes": graph.get("nodes", []) or []}
    payload["agentName"] = args.name or agent.get("name")
    if args.description is not None:
        payload["agentDescription"] = args.description
    if args.prompts_file or args.personality is not None or args.restrictions is not None:
        settings = {}
        if args.prompts_file:
            settings["prompts"] = _read_json_file(args.prompts_file, "Prompts file")
        if args.personality is not None:
            settings["agentPersonality"] = args.personality
        if args.restrictions is not None:
            settings["agentRestrictions"] = args.restrictions
        payload["settings"] = settings
    result = api.put(f"/agent-graphs/{args.agent_id}", payload)
    graph_id = result.get("draftGraphId")
    published = False
    if args.publish and graph_id:
        api.patch(f"/agent-graphs/{graph_id}/publish")
        published = True
    return {"updated": True, "agentId": args.agent_id, "agentName": payload["agentName"],
            "graphId": graph_id, "published": published}


def cmd_add_node(api, args):
    ns = _read_json_file(args.node_file, "Node file")
    integration = (_read_json_file(args.integration_file, "Integration file")
                   if args.integration_file else None)
    existing = api.get(f"/agent-graphs/{args.agent_id}")
    existing_nodes = (existing.get("graph") or {}).get("nodes", []) or []

    new_node_id, new_tc_id = _g(), _g()
    new_ops = {_param_name(op): _g() for op in ns.get("output_params", []) or []}
    node_type = ns.get("node_type") or "executionNode"

    # Place the new node relative to its source (or target) so it does not
    # land on top of an existing node in the UI.
    new_x, new_y = ns.get("x", 250), ns.get("y", 150)
    if "x" not in ns or "y" not in ns:
        anchor = next((n for n in existing_nodes if n["id"] == args.source_node_id), None)
        if anchor:
            new_x = anchor.get("xCoordinate", 250)
            new_y = anchor.get("yCoordinate", 150) + _LAYOUT_Y_GAP
        elif args.target_node_id:
            anchor = next((n for n in existing_nodes if n["id"] == args.target_node_id), None)
            if anchor:
                new_x = anchor.get("xCoordinate", 250)
                new_y = anchor.get("yCoordinate", 150) - _LAYOUT_Y_GAP

    new_node = {
        "id": new_node_id, "objective": ns["objective"],
        "evaluationCriteria": ns.get("evaluation_criteria", []) or [],
        "isEntryNode": False, "isExitNode": False, "nodeType": node_type,
        "parentNodeId": ns.get("parentNodeId"),
        "xCoordinate": new_x, "yCoordinate": new_y,
        "isEvaluationEnabled": bool(ns.get("evaluation_criteria")),
        "isAttachmentDataPulledIn": True, "onError": ns.get("on_error", "STOP"),
        "enableAutoRetryWhenFailure": ns.get("enable_retry", False),
        "autoRetryCountWhenFailure": ns.get("retry_count", 1),
        "autoRetryWaitTimeWhenFailureInMs": ns.get("retry_wait_ms", 1000),
        "autoRetryWhenAccuracyLessThan": 80, "autoRetryLimitWhenAccuracyIsLow": 1,
        "enableAutoRetryWhenAccuracyIsLow": False, "autoRetryDescription": None,
        "enableAutoRetryDescription": False, "isEdited": False,
        "childEdges": [], "parentEdges": [],
    }
    if node_type == "conditionNode":
        new_node["nodeConfigurations"] = ns.get("node_configurations") or {
            "conditionType": "llm_based", "llmModel": "GPT40", "fallbackModels": None}
    elif node_type == "waitingNode":
        new_node["nodeConfigurations"] = ns.get("node_configurations") or {
            "waitType": "time_based", "timeToWaitValue": 1,
            "timeToWaitUnit": "hours", "timeoutType": "no_timeout"}
    elif node_type == "loopingNode":
        new_node["nodeConfigurations"] = ns.get("node_configurations") or {"iterationCount": 1}
    if node_type in ("executionNode", "waitingNode"):
        fn = _tool_function_name(ns.get("tool_name") or ns.get("name"))
        new_node["toolConfiguration"] = {
            "id": new_tc_id, "toolFunctionName": fn,
            "toolName": ns.get("tool_name") or ns.get("name"), "iconSrc": None,
            "description": ns.get("tool_description", ""), "prompt": ns.get("prompt", ""),
            "preferredModel": ns.get("model", DEFAULT_NODE_MODEL),
            "fallbackModels": _coerce_fallback_models(ns.get("fallback_models")), "accuracyScore": None,
            "requiresConsent": False, "isMemoryTool": False,
            "memoryLookupInstruction": "", "isBackgroundTool": False,
            "isBatchExecutionEnabled": False, "isCodeExecutionEnabled": False,
            "isAvailableToWorkspace": False, "dynamicPropsId": None,
            "integrationProviderId": None,
            "inputParams": [
                {"position": ip.get("position", i), "paramName": _param_name(ip),
                 "paramDescription": ip.get("description", ""),
                 "fillType": ip.get("fill_type", "ai_fill"),
                 "required": ip.get("required", True),
                 "dataType": ip.get("type", "string"),
                 "isArray": ip.get("is_array", False),
                 "outputExample": ip.get("output_example"),
                 "reloadProps": False, "remoteOptions": False, "question": None,
                 "options": None, "paramTip": None,
                 "staticValue": ip.get("static_value") if ip.get("fill_type") == "static" else None,
                 "linkParamOutputId": None}
                for i, ip in enumerate(ns.get("input_params", []) or [])
            ],
            "outputParams": [
                {"id": new_ops[_param_name(op)], "position": op.get("position", i),
                 "paramName": _param_name(op), "paramDescription": op.get("description", ""),
                 "dataType": op.get("type", "string"), "isArray": op.get("is_array", False),
                 "outputExample": op.get("output_example"),
                 "agentToolConfigurationId": new_tc_id, "parentId": None,
                 "paramPath": None, "typeOptions": None}
                for op in ns.get("output_params", []) or []
            ],
        }

    if args.source_node_id:
        edge = {"sourceAgentGraphNodeId": args.source_node_id,
                "targetAgentGraphNodeId": new_node_id, "condition": "",
                "isAttachmentDataPulledIn": True}
        new_node["parentEdges"].append(edge)
        for n in existing_nodes:
            if n["id"] == args.source_node_id:
                n.setdefault("childEdges", []).append(edge)
                break
    if args.target_node_id:
        edge = {"sourceAgentGraphNodeId": new_node_id,
                "targetAgentGraphNodeId": args.target_node_id, "condition": "",
                "isAttachmentDataPulledIn": True}
        new_node["childEdges"].append(edge)
        for n in existing_nodes:
            if n["id"] == args.target_node_id:
                n.setdefault("parentEdges", []).append(edge)
                break

    existing_nodes.append(new_node)
    # PUT only the nodes; agentName/description/settings are optional on the
    # update DTO, so omitting them keeps the agent's existing metadata (the GET
    # response nests agentName under graph.agent.name, so sending the top-level
    # value would send null and blank the agent).
    result = api.put(f"/agent-graphs/{args.agent_id}", {"nodes": existing_nodes})
    graph_id = result.get("draftGraphId")
    steps = [{"step": "add_node", "status": "ok", "detail": f"Added node '{ns['objective']}'."}]

    if integration and graph_id:
        nodes_data = api.get(f"/agent-graphs/{args.agent_id}/nodes/lite")
        actual_id = next((n["id"] for n in nodes_data.get("nodes", []) or []
                          if n.get("objective") == ns["objective"]), None)
        if actual_id:
            clean = [_clean_integration_param(ip)
                     for ip in integration.get("input_params", []) or []]
            api.patch_with_body("/agent-graphs/update-node", {
                "agentId": args.agent_id, "graphId": graph_id,
                "node": {"id": actual_id, "objective": ns["objective"],
                         "isAttachmentDataPulledIn": True, "evaluationCriteria": [],
                         "toolConfiguration": {
                             "toolFunctionName": integration["tool_function_name"],
                             "toolName": integration["tool_name"],
                             "shortDescription": integration.get("description", ""),
                             "description": integration.get("description", ""),
                             "iconSrc": integration.get("icon_src"),
                             "preferredModel": integration.get("preferred_model"),
                             "requiresConsent": integration.get("requires_consent", False),
                             "isMemoryTool": False, "isBackgroundTool": False,
                             "isBatchExecutionEnabled": False, "integrationProviderId": None,
                             "inputParams": clean,
                             "outputParams": integration.get("output_params", []) or []}}})
            steps.append({"step": "attach_integration", "status": "ok",
                          "detail": f"Attached {integration['tool_function_name']}."})

    all_ok, _ = do_verify(api, args.agent_id)
    steps.append({"step": "verify", "status": "ok" if all_ok else "warning"})
    published = False
    if args.publish and graph_id:
        api.patch(f"/agent-graphs/{graph_id}/publish")
        published = True
    return {"added": True, "agentId": args.agent_id, "graphId": graph_id,
            "newNodeId": new_node_id, "verificationPassed": all_ok,
            "published": published, "steps": steps}


def cmd_remove_node(api, args):
    existing = api.get(f"/agent-graphs/{args.agent_id}")
    existing_nodes = (existing.get("graph") or {}).get("nodes", []) or []
    removed = next((n for n in existing_nodes if n["id"] == args.node_id), None)
    if not removed:
        raise BeamError(f"Node {args.node_id} not found in this agent.")
    parent_ids = [e["sourceAgentGraphNodeId"] for e in removed.get("parentEdges", []) or []]
    child_ids = [e["targetAgentGraphNodeId"] for e in removed.get("childEdges", []) or []]

    nodes = [n for n in existing_nodes if n["id"] != args.node_id]
    for n in nodes:
        n["childEdges"] = [e for e in n.get("childEdges", []) or []
                           if e["targetAgentGraphNodeId"] != args.node_id]
        n["parentEdges"] = [e for e in n.get("parentEdges", []) or []
                            if e["sourceAgentGraphNodeId"] != args.node_id]

    def link(src, tgt):
        edge = {"sourceAgentGraphNodeId": src, "targetAgentGraphNodeId": tgt,
                "condition": "", "isAttachmentDataPulledIn": True}
        for n in nodes:
            if n["id"] == src:
                n.setdefault("childEdges", []).append(edge)
            if n["id"] == tgt:
                n.setdefault("parentEdges", []).append(edge)

    if args.rewire_to:
        for pid in parent_ids:
            link(pid, args.rewire_to)
    else:
        for pid in parent_ids:
            for cid in child_ids:
                link(pid, cid)

    # PUT only the nodes - keeps the agent's existing metadata (see cmd_add_node).
    result = api.put(f"/agent-graphs/{args.agent_id}", {"nodes": nodes})
    graph_id = result.get("draftGraphId")
    published = False
    if args.publish and graph_id:
        api.patch(f"/agent-graphs/{graph_id}/publish")
        published = True
    return {"removed": True, "agentId": args.agent_id, "graphId": graph_id,
            "removedNodeId": args.node_id, "published": published}


# ===========================================================================
# Commands - triggers / webhooks (Bearer-JWT auth)
# ===========================================================================

def cmd_trigger_actions(api, args):
    data = api.t_get("/agent-trigger/integration/actions",
                     params={"systemIntegrationIdentifier": args.integration})
    actions = data if isinstance(data, list) else data.get("actions", [data])
    return {"actions": actions}


def cmd_create_trigger(api, args):
    spec = _read_json_file(args.trigger_file, "Trigger file")
    for field in ("agentId", "agentGraphNodeId", "title", "configuration"):
        if field not in spec:
            raise BeamError(f"Trigger file is missing required field '{field}'.")
    body = {
        "title": spec["title"],
        "agentId": spec["agentId"],
        "agentGraphNodeId": spec["agentGraphNodeId"],
        "integrationProviderId": spec.get("integrationProviderId"),
        "configuration": spec["configuration"],
        "timezone": spec.get("timezone", "UTC"),
        "onlyOnce": spec.get("onlyOnce", False),
    }
    for opt in ("prompt", "userDefinedFrequency", "userDefinedFrequencyValue",
                "userDefinedFrequencyDateTime"):
        if spec.get(opt) is not None:
            body[opt] = spec[opt]
    data = api.t_post("/agent-trigger", body)
    return {"created": True, "triggerId": data.get("id"), "trigger": data}


def cmd_get_triggers(api, args):
    data = api.t_get(f"/agent-trigger/{args.agent_id}",
                     params={"agentGraphNodeId": args.entry_node_id})
    triggers = data if isinstance(data, list) else data.get("triggers", [data])
    return {"triggers": triggers}


def cmd_update_trigger(api, args):
    spec = _read_json_file(args.trigger_file, "Trigger file")
    body = {"agentId": spec.get("agentId")}
    for field in ("title", "prompt", "configuration", "timezone",
                  "userDefinedFrequency", "userDefinedFrequencyValue",
                  "userDefinedFrequencyDateTime", "isActive", "onlyOnce"):
        if spec.get(field) is not None:
            body[field] = spec[field]
    data = api.t_patch(f"/agent-trigger/{args.trigger_id}", body)
    return {"updated": True, "trigger": data}


def cmd_delete_trigger(api, args):
    api.t_delete(f"/agent-trigger/{args.trigger_id}")
    return {"deleted": True, "triggerId": args.trigger_id}


def cmd_toggle_trigger(api, args):
    data = api.t_patch(f"/agent-trigger/{args.trigger_id}/toggle-deactivation", {})
    return {"toggled": True, "trigger": data}


def cmd_create_webhook(api, args):
    # The webhook create endpoint requires a boolean `triggered`; omitting it
    # is rejected with 400 "triggered must be a boolean value".
    body = {"triggered": True}
    if args.entry_node_id:
        body["agentGraphNodeId"] = args.entry_node_id
    data = api.t_post(f"/{args.agent_id}/webhook", body)
    return {"created": True, "webhook": data,
            "webhookUrl": f"{api.base}/{args.agent_id}/webhook"}


def cmd_get_webhook(api, args):
    data = api.t_get(f"/{args.agent_id}/webhook")
    return {"webhook": data, "webhookUrl": f"{api.base}/{args.agent_id}/webhook"}


def cmd_delete_webhook(api, args):
    api.t_delete(f"/{args.agent_id}/webhook")
    return {"deleted": True, "agentId": args.agent_id}


# ===========================================================================
# Small shared helpers for commands
# ===========================================================================

def _maybe_publish(api, args):
    """Publish the agent's current draft graph if --publish was given."""
    if not getattr(args, "publish", False):
        return None
    nodes_data = api.get(f"/agent-graphs/{args.agent_id}/nodes/lite")
    graph_id = nodes_data.get("graphId")
    if graph_id:
        api.patch(f"/agent-graphs/{graph_id}/publish")
    return graph_id


def _api_patch_with_body(self, path, body):
    return _http("PATCH", self.base + path,
                 _api_headers(self.api_key, self.workspace_id), body=body)


Api.patch_with_body = _api_patch_with_body


# ===========================================================================
# CLI
# ===========================================================================

def build_parser():
    p = argparse.ArgumentParser(
        prog="beam.py",
        description="Beam Agent Builder CLI - build and deploy Beam AI agents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Credentials resolve from env vars, then ~/.config/beam/credentials "
               "(written by `beam login`); BEAM_API_URL defaults to the public API. "
               "There is no .env file. Every command prints JSON to stdout; errors "
               "carry a 'code' and usually a 'next'. Do not merge stderr into stdout "
               "with 2>&1 before parsing.",
    )
    sub = p.add_subparsers(dest="command", metavar="<command>")

    s = sub.add_parser("validate", help="Check that credentials reach the Beam API.")

    s = sub.add_parser("search-tools", help="Search integration tools by keyword.")
    s.add_argument("keyword")
    s.add_argument("--wait-only", action="store_true",
                   help="Only tools whose replies a condition_based wait node can await.")
    s.add_argument("--managed-only", action="store_true",
                   help="Drop prompt-only tools (custom_gpt_tool / gpt_tool); keep "
                        "every real beam_tool, including Beam built-ins like web "
                        "search. Use this for the common case.")

    s = sub.add_parser("search-agents", help="Search existing agents by name.")
    s.add_argument("keyword")

    s = sub.add_parser("get-nodes", help="List an agent's nodes (id + objective).")
    s.add_argument("agent_id")

    s = sub.add_parser("get-node", help="Get one or more nodes (params, edges, UUIDs).")
    s.add_argument("agent_id")
    s.add_argument("node_ids", nargs="+", metavar="node_id")
    s.add_argument("--full", action="store_true", help="Return raw node JSON.")

    s = sub.add_parser("get-graph", help="Get an agent's full graph.")
    s.add_argument("agent_id")
    s.add_argument("--full", action="store_true", help="Return raw graph JSON.")

    s = sub.add_parser("verify-links", help="Check every linked param is intact.")
    s.add_argument("agent_id")

    s = sub.add_parser("deploy",
                       help="Full deploy: create/update + attach + relink + verify + publish.")
    s.add_argument("spec_file")
    s.add_argument("--agent-id", help="Update this existing agent instead of creating.")
    s.add_argument("--publish", action="store_true",
                   help="Publish after deploy. Omit to leave a draft (default).")
    s.add_argument("--dry-run", action="store_true", help="Print the payload, no API call.")
    s.add_argument("--summary", action="store_true",
                   help="With --dry-run, print counts and node names instead of the "
                        "full payload (which runs to thousands of tokens).")

    s = sub.add_parser("create", help="Create/update an agent (no integration attach).")
    s.add_argument("spec_file")
    s.add_argument("--agent-id")
    s.add_argument("--dry-run", action="store_true")

    s = sub.add_parser("publish", help="Publish a draft graph (makes the agent live).")
    s.add_argument("graph_id")

    s = sub.add_parser("attach-tool", help="Attach an integration tool to a node.")
    s.add_argument("agent_id")
    s.add_argument("graph_id")
    s.add_argument("node_id")
    s.add_argument("toolconfig_file")
    s.add_argument("--objective", default="")

    s = sub.add_parser("update-node", help="Update a node from a full node-payload file.")
    s.add_argument("agent_id")
    s.add_argument("graph_id")
    s.add_argument("node_file")

    s = sub.add_parser("update-node-prompt", help="Update only a node's prompt.")
    s.add_argument("agent_id")
    s.add_argument("node_id")
    s.add_argument("prompt_file", help="Text/markdown file containing the new prompt.")
    s.add_argument("--publish", action="store_true")

    s = sub.add_parser("update-node-params", help="Update only a node's input/output params.")
    s.add_argument("agent_id")
    s.add_argument("node_id")
    s.add_argument("--input-params-file", help="JSON array of input params.")
    s.add_argument("--output-params-file", help="JSON array of output params.")
    s.add_argument("--publish", action="store_true")

    s = sub.add_parser("update-edge", help="Update an edge's condition.")
    s.add_argument("edge_id")
    s.add_argument("--condition", help="New llm_based condition text ('' = unconditional).")
    s.add_argument("--condition-groups-file", help="JSON array for rule_based edges.")

    s = sub.add_parser("update-metadata", help="Update agent name/description/personality.")
    s.add_argument("agent_id")
    s.add_argument("--name")
    s.add_argument("--description")
    s.add_argument("--personality")
    s.add_argument("--restrictions")
    s.add_argument("--prompts-file", help="JSON array of example prompts.")
    s.add_argument("--publish", action="store_true")

    s = sub.add_parser("add-node", help="Add one node to an existing agent.")
    s.add_argument("agent_id")
    s.add_argument("node_file", help="JSON file with a single node spec.")
    s.add_argument("--source-node-id", help="Connect an edge FROM this node.")
    s.add_argument("--target-node-id", help="Connect an edge TO this node.")
    s.add_argument("--integration-file", help="Integration JSON to attach after adding.")
    s.add_argument("--publish", action="store_true")

    s = sub.add_parser("remove-node", help="Remove a node and rewire its edges.")
    s.add_argument("agent_id")
    s.add_argument("node_id")
    s.add_argument("--rewire-to", help="Point the removed node's parents at this node.")
    s.add_argument("--publish", action="store_true")

    s = sub.add_parser("trigger-actions", help="List trigger actions for an integration.")
    s.add_argument("integration", help="e.g. google-mail, slack, github, timer")

    s = sub.add_parser("create-trigger", help="Create a trigger from a JSON file.")
    s.add_argument("trigger_file")

    s = sub.add_parser("get-triggers", help="List an agent's triggers.")
    s.add_argument("agent_id")
    s.add_argument("entry_node_id")

    s = sub.add_parser("update-trigger", help="Update a trigger from a JSON file.")
    s.add_argument("trigger_id")
    s.add_argument("trigger_file")

    s = sub.add_parser("delete-trigger", help="Delete a trigger.")
    s.add_argument("trigger_id")

    s = sub.add_parser("toggle-trigger", help="Activate / deactivate a trigger.")
    s.add_argument("trigger_id")

    s = sub.add_parser("create-webhook", help="Create a webhook endpoint for an agent.")
    s.add_argument("agent_id")
    s.add_argument("--entry-node-id")

    s = sub.add_parser("get-webhook", help="Get an agent's webhook URL.")
    s.add_argument("agent_id")

    s = sub.add_parser("delete-webhook", help="Delete an agent's webhook.")
    s.add_argument("agent_id")

    s = sub.add_parser(
        "test-node",
        help="Run a single node with a task context string (smoke test before full deploy).",
    )
    s.add_argument("agent_id", help="Agent ID")
    s.add_argument("node_id", help="Node ID to test")
    s.add_argument("task_context", help="Realistic task input string for this node")

    return p


def cmd_test_node(api, args):
    """POST /agent-graphs/test-node — run a single node with a task context string."""
    payload = {
        "agentId": args.agent_id,
        "nodeId": args.node_id,
        "taskContext": args.task_context,
    }
    result = api.post("/agent-graphs/test-node", payload)
    return {"result": result}


COMMANDS = {
    "validate": cmd_validate,
    "search-tools": cmd_search_tools,
    "search-agents": cmd_search_agents,
    "get-nodes": cmd_get_nodes,
    "get-node": cmd_get_node,
    "get-graph": cmd_get_graph,
    "verify-links": cmd_verify_links,
    "deploy": cmd_deploy,
    "create": cmd_create,
    "publish": cmd_publish,
    "attach-tool": cmd_attach_tool,
    "update-node": cmd_update_node,
    "update-node-prompt": cmd_update_node_prompt,
    "update-node-params": cmd_update_node_params,
    "update-edge": cmd_update_edge,
    "update-metadata": cmd_update_metadata,
    "add-node": cmd_add_node,
    "remove-node": cmd_remove_node,
    "trigger-actions": cmd_trigger_actions,
    "create-trigger": cmd_create_trigger,
    "get-triggers": cmd_get_triggers,
    "update-trigger": cmd_update_trigger,
    "delete-trigger": cmd_delete_trigger,
    "toggle-trigger": cmd_toggle_trigger,
    "create-webhook": cmd_create_webhook,
    "get-webhook": cmd_get_webhook,
    "delete-webhook": cmd_delete_webhook,
    "test-node": cmd_test_node,
}


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help(sys.stderr)
        return 2

    handler = COMMANDS[args.command]
    try:
        api = Api(*resolve_creds())
        result = handler(api, args)
        print(json.dumps({"ok": True, "command": args.command, **result}, indent=2))
        return 0
    except BeamError as exc:
        payload = {"ok": False, "command": args.command,
                   "code": getattr(exc, "code", "internal_error"), "error": str(exc)}
        if getattr(exc, "next_step", None):
            payload["next"] = exc.next_step
        print(json.dumps(payload, indent=2))
        # stderr stays human; note that stdout carries the machine-readable copy,
        # so callers must not merge the streams with 2>&1 before parsing JSON.
        print(f"[beam.py] ERROR: {exc}", file=sys.stderr)
        if payload.get("next"):
            print(f"[beam.py] NEXT: {payload['next']}", file=sys.stderr)
        return EXIT_CODES.get(payload["code"], 1)
    except KeyboardInterrupt:
        print(json.dumps({"ok": False, "command": args.command, "error": "interrupted"}))
        return 130
    except Exception as exc:  # noqa: BLE001 - surface unexpected errors as JSON too
        print(json.dumps({"ok": False, "command": args.command,
                          "error": f"Unexpected {type(exc).__name__}: {exc}"}, indent=2))
        print(f"[beam.py] UNEXPECTED ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
