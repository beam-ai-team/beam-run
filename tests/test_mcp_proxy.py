import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "beam_mcp_proxy", ROOT / "beam" / "bin" / "mcp_proxy.py"
)
proxy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(proxy)


class McpPolicyTests(unittest.TestCase):
    def test_flow_internal_tools_are_hidden_from_discovery(self):
        reply = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "tools": [
                    {"name": "listAgents"},
                    {"name": "getAgentGraph"},
                    {"name": "mcp__beam__testGraphNode"},
                    {"name": "listenTask"},
                    {"name": "startTask"},
                ]
            },
        }

        filtered = proxy.filter_tools_list_reply(reply)

        self.assertEqual(
            [tool["name"] for tool in filtered["result"]["tools"]],
            [
                "listAgents",
                "listenTask",
                "listPreferredModels",
                "listActiveTools",
                "listAgentViews",
                "getAgentView",
                "listAgentViewRecords",
                "listLinkedAgentViewRecords",
            ],
        )

    def test_flow_internal_calls_are_rejected_with_agent_builder_guidance(self):
        reply = proxy.flow_internal_tool_reply(
            {"id": 7, "params": {"name": "updateGraphNode"}}
        )

        self.assertTrue(reply["result"]["isError"])
        self.assertEqual(reply["id"], 7)
        self.assertIn("Agent Builder", reply["result"]["content"][0]["text"])

    def test_operational_tools_remain_available(self):
        self.assertFalse(proxy.is_flow_internal_tool("listenTask"))
        self.assertFalse(proxy.is_flow_internal_tool("createAgentTask"))
        self.assertTrue(proxy.is_flow_internal_tool("mcp__beam__getToolOutputSchema"))

    def test_local_views_tool_uses_read_only_rest_route(self):
        calls = []
        original = proxy.rest_get
        proxy.rest_get = lambda path, workspace_id, params=None: calls.append(
            (path, workspace_id, params)
        ) or {"records": []}
        try:
            reply = proxy.local_operation_request(
                {
                    "id": 9,
                    "params": {
                        "name": "listAgentViewRecords",
                        "arguments": {
                            "viewId": "view/a",
                            "workspaceId": "workspace-1",
                            "pageNum": 2,
                            "pageSize": 50,
                        },
                    },
                }
            )
        finally:
            proxy.rest_get = original

        self.assertFalse(reply["result"].get("isError", False))
        self.assertEqual(
            calls,
            [
                (
                    "/agent-views/view%2Fa/records",
                    "workspace-1",
                    {"pageNum": 2, "pageSize": 50, "fields": None, "sort": None, "where": None},
                )
            ],
        )

    def test_local_operations_reject_missing_workspace_before_calling_api(self):
        reply = proxy.local_operation_request(
            {"id": 10, "params": {"name": "listAgentViews", "arguments": {}}}
        )
        self.assertTrue(reply["result"]["isError"])
        self.assertIn("workspaceId", reply["result"]["content"][0]["text"])

    def test_preferred_models_uses_documented_workspace_route(self):
        calls = []
        original = proxy.rest_get
        proxy.rest_get = lambda path, workspace_id, params=None: calls.append(
            (path, workspace_id, params)
        ) or []
        try:
            reply = proxy.local_operation_request(
                {
                    "id": 11,
                    "params": {
                        "name": "listPreferredModels",
                        "arguments": {"workspaceId": "workspace-1"},
                    },
                }
            )
        finally:
            proxy.rest_get = original

        self.assertEqual(reply["result"]["structuredContent"], {"data": []})
        self.assertEqual(calls, [("/custom-tool/preferred-models", "workspace-1", None)])

    def test_active_tools_defaults_to_a_safe_page_size(self):
        calls = []
        original = proxy.rest_get
        proxy.rest_get = lambda path, workspace_id, params=None: calls.append(
            (path, workspace_id, params)
        ) or {"tools": [], "count": 0}
        try:
            proxy.local_operation_request(
                {
                    "id": 12,
                    "params": {
                        "name": "listActiveTools",
                        "arguments": {"workspaceId": "workspace-1"},
                    },
                }
            )
        finally:
            proxy.rest_get = original

        self.assertEqual(
            calls,
            [
                (
                    "/tool/active-tools",
                    "workspace-1",
                    {
                        "searchKeyword": None,
                        "type": None,
                        "categoryId": None,
                        "agentId": None,
                        "creatorType": None,
                        "includedFunctionNames": None,
                        "excludedFunctionNames": None,
                        "excludeAgentTools": None,
                        "pageNum": 1,
                        "pageSize": 25,
                    },
                )
            ],
        )

    def test_registration_uses_the_policy_enforcing_stdio_server(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            (home_path / ".cursor").mkdir()
            env = os.environ.copy()
            env.update(
                {
                    "HOME": home,
                    "BEAM_API_KEY": "test-key",
                    "PATH": os.pathsep.join(
                        [str(pathlib.Path(sys.executable).parent), "/usr/bin", "/bin"]
                    ),
                }
            )
            result = subprocess.run(
                [str(ROOT / "beam" / "bin" / "beam"), "register"],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )

            config = json.loads((home_path / ".cursor" / "mcp.json").read_text())
            registered = config["mcpServers"]["beam"]
            self.assertEqual(registered["args"], ["mcp"])
            self.assertNotIn("url", registered)
            self.assertTrue(registered["command"].endswith("/beam/bin/beam"))
            self.assertIn("cursor", result.stdout)


if __name__ == "__main__":
    unittest.main()
