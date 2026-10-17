import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / 'beam/bin/beam'

class ManagedRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = Path(self.temp.name)
        self.env = {**os.environ, 'BEAM_MANAGED_CONTEXT': '1', 'BEAM_API_KEY': 'host-key',
                    'BEAM_API_URL': 'https://instance.example', 'BEAM_WORKSPACE_ID': 'host-workspace',
                    'BEAM_SESSION_ID': 'prism-thread', 'BEAM_INSTANCE_ID': 'host-instance',
                    'BEAM_CONFIG_DIR': str(self.config)}
    def run_cli(self, *args, env=None):
        return subprocess.run(['sh', str(CLI), *args], env=env or self.env, capture_output=True, text=True)
    def test_checkout_is_locked_without_writing_local_state(self):
        result = self.run_cli('checkout')
        self.assertEqual(result.returncode, 0, result.stderr)
        checkout = json.loads(result.stdout)
        self.assertTrue(checkout['locked'])
        self.assertEqual(checkout['workspaceId'], 'host-workspace')
        self.assertEqual(list(self.config.iterdir()), [])
    def test_connection_and_target_management_is_disabled(self):
        for args in [('login',), ('logout',), ('instance', 'add'), ('workspace', 'use', 'other'), ('checkout', 'other')]:
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('managed_context_locked', result.stderr)
        self.assertEqual(list(self.config.iterdir()), [])
    def test_managed_mode_cannot_fall_back_to_saved_credentials(self):
        env = dict(self.env)
        del env['BEAM_API_KEY']
        result = self.run_cli('checkout', env=env)
        self.assertEqual(result.returncode, 3)
        self.assertIn('managed_context_missing', result.stderr)
    def test_manifest_has_complete_closed_executable_contract(self):
        result = subprocess.run(['python3', str(ROOT / 'beam/bin/operation_manifest.py')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        operations = json.loads(result.stdout)['operations']
        self.assertEqual(len(operations), 124)
        self.assertEqual(len({op['id'] for op in operations}), 124)
        for op in operations:
            self.assertFalse(op['execution']['inputSchema']['additionalProperties'])
            self.assertTrue(op['execution']['commands'])
            self.assertIn(op['safety'], ['read', 'external-effect', 'destructive-write', 'reversible-write', 'additive-write'])
            self.assertTrue(op['confirmation'])

if __name__ == '__main__': unittest.main()
