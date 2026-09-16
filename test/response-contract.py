#!/usr/bin/env python3
"""Exercise the user-facing setup text without a live Beam account."""

import importlib.util
import pathlib
import tempfile
import urllib.error

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("mcp_proxy", ROOT / "beam/bin/mcp_proxy.py")
beam = importlib.util.module_from_spec(spec)
spec.loader.exec_module(beam)


def assert_copy(text, expected):
    assert expected in text, text
    for internal in ("Ask the user", "Never ask", "policy card", "skill requires", "do not scan"):
        assert internal not in text, text


with tempfile.TemporaryDirectory(prefix="beam-response-") as tmp:
    root = pathlib.Path(tmp)
    beam.CONFIG_DIR = tmp
    beam.SESSION_FILE = str(root / "sessions" / "test")
    beam.API_KEY = ""

    def profile(instance_id, name, key, previous=""):
        path = root / "instances" / instance_id
        path.parent.mkdir(exist_ok=True)
        path.write_text(
            f"BEAM_INSTANCE_ID={instance_id}\nBEAM_INSTANCE_NAME={name}\n"
            f"BEAM_API_KEY={key}\nBEAM_API_URL=https://api.{instance_id}.example\n"
            f"BEAM_WORKSPACE_ID={previous}\n"
            f"BEAM_WORKSPACE_NAME={'Alpha' if previous else ''}\n",
            encoding="utf-8",
        )

    assert_copy(beam.context_text(beam.load_context()), "Paste a Beam workspace URL")
    assert_copy(beam.context_text(beam.load_context()), "Enter the API key in the hidden prompt")
    assert_copy(beam.context_text(beam.load_context()), "Select or create a workspace")
    print("ok  first connection: URL → hidden key → workspace")

    profile("app", "Beam App", "app-key")
    assert_copy(beam.context_text(beam.load_context()), "Which workspace would you like to use?")
    print("ok  one saved instance: workspace choice, no App default assumption")

    profile("app", "Beam App", "app-key", "w-a")
    assert_copy(beam.context_text(beam.load_context()), "Use Alpha again, choose another workspace, or create a new one?")
    print("ok  previous workspace: explicit confirmation and alternatives")

    profile("enterprise", "Beam Enterprise", "enterprise-key")
    assert_copy(beam.context_text(beam.load_context()), "Which instance would you like to use?")
    assert_copy(beam.context_text(beam.load_context()), "+ Add another")
    assert "required" not in beam.CHECKOUT_TOOL["inputSchema"]
    print("ok  multiple instances: instance choice before workspace")

    selected, choice = beam.choose_checkout({})
    assert selected is None and "Which instance would you like to use?" in choice
    assert not (root / "sessions" / "test").exists()
    print("ok  fresh multi-instance session: no instance is assumed or locked")

    beam.request_json = lambda url, key: {"workspaces": [
        {"id": "w-a", "name": "Alpha"}, {"id": "w-b", "name": "Beta"}
    ]}
    selected, choice = beam.choose_checkout({"instance": "Beam App"})
    assert selected is None
    assert_copy(choice, "Use Alpha again, choose another workspace, or create a new one?")
    beam.request_json = lambda url, key: {"workspaces": [{"id": "w-a", "name": "Alpha"}]}
    selected, choice = beam.choose_checkout({"instance": "Beam App"})
    assert selected is None
    assert_copy(choice, "Use Alpha again")
    selected, choice = beam.choose_checkout({"instance": "Beam Enterprise"})
    assert choice is None and selected["locked"]
    (root / "sessions" / "test").unlink()
    print("ok  checkout: no silent reuse and no workspace dump")

    beam.request_json = lambda url, key: {"workspaces": [
        {"id": "w-b", "name": "Beta"}, {"id": "w-c", "name": "Gamma"}
    ]}
    selected, choice = beam.choose_checkout({"instance": "Beam App"})
    assert selected is None
    assert_copy(choice, "Which workspace would you like to use?")
    assert "Alpha" not in choice
    selected, choice = beam.choose_checkout({"instance": "Beam App", "workspace": "Missing"})
    assert selected is None
    assert_copy(choice, "No unique workspace matches 'Missing'")
    selected, choice = beam.choose_checkout({"instance": "Unknown"})
    assert selected is None
    assert_copy(choice, "No unique saved instance matches 'Unknown'")
    print("ok  stale previous workspace and unknown selections: no accidental checkout")

    beam.request_json = lambda url, key: {"workspaces": [
        {"id": "w-a", "name": "Alpha"}, {"id": "w-b", "name": "Beta"}
    ]}

    selected, choice = beam.choose_checkout({"instance": "Beam App", "workspace": "Alpha"})
    assert choice is None and selected["locked"]
    assert_copy(beam.context_text(beam.load_context()), "🔒 Locked for this session")
    selected, choice = beam.choose_checkout({"instance": "Beam Enterprise", "workspace": "Alpha"})
    assert selected is None
    assert_copy(choice, "Start a new session")
    selected, choice = beam.choose_checkout({"instance": "Beam App", "workspace": "Beta"})
    assert selected is None
    assert_copy(choice, "Start a new session")
    print("ok  checked out: visible lock; cross-instance switch blocked")

    (root / "sessions" / "test").unlink()
    beam.request_json = lambda url, key: (_ for _ in ()).throw(
        urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)
    )
    selected, choice = beam.choose_checkout({"instance": "Beam App", "workspace": "Alpha"})
    assert selected is None
    assert_copy(choice, "Run `beam login --replace`")
    assert not (root / "sessions" / "test").exists()
    print("ok  rejected saved key: specific repair, no session change")

print("Response contract checks PASSED.")
