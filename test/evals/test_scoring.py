#!/usr/bin/env python3
"""Regression checks for eval matching and generated action dependencies."""
import runpy
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
scorer = runpy.run_path(str(ROOT / "test/evals/score_playbook_evals.py"))
generator = runpy.run_path(str(ROOT / "beam/scripts/check_playbooks.py"))


class EvalChecks(unittest.TestCase):
    def test_alternative_start_keeps_route_validation(self):
        case = {"playbooks": [["change-an-agents-flow", "connect-or-fix-an-integration"]]}
        for first in case["playbooks"][0]:
            self.assertEqual(scorer["score"](case, {"playbooks": [first]}, True), [])
        self.assertTrue(scorer["score"](case, {"playbooks": ["get-oriented"]}, True))

    def test_multistep_order_is_still_required(self):
        case = {"playbooks": ["find-out-what-happened", ["change-an-agents-flow", "build-a-new-agent"], "test-a-draft"]}
        for middle in case["playbooks"][1]:
            self.assertEqual(scorer["score"](case, {"playbooks": [case["playbooks"][0], middle, "test-a-draft"]}, True), [])
        self.assertTrue(scorer["score"](case, {"playbooks": [case["playbooks"][0], "test-a-draft", "change-an-agents-flow"]}, True))

    def test_publish_must_stop_on_its_own_action(self):
        case = {"playbooks": [], "required": [["graph.publish"]], "must_stop_before": ["graph.publish"]}
        steps = [{"action": "none", "stop_before": True}, {"action": "graph.publish", "stop_before": False}]
        self.assertTrue(scorer["score"](case, {"steps": steps}, False))
        steps[-1]["stop_before"] = True
        self.assertEqual(scorer["score"](case, {"steps": steps}, False), [])

    def test_generated_tables_include_transitive_reads(self):
        ops = generator["load_operations"]()
        ops["graph.get"]["postRead"] = "graph.nodes"
        actions = generator["table_actions"]({"graph.publish", "task.submit-input"}, ops)
        self.assertTrue({"agent.list", "agent.get", "user.current", "graph.validate", "graph.get", "graph.nodes", "task.get"} <= actions)
        for action in actions:
            for key in ("preRead", "postRead"):
                if ops[action].get(key):
                    self.assertIn(ops[action][key], actions)
        self.assertTrue(all(ops[a]["safety"] == "read" for a in actions - {"graph.publish", "task.submit-input"}))


if __name__ == "__main__":
    unittest.main()
