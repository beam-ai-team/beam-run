import importlib.util
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

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
                    'BEAM_CONFIG_DIR': str(self.config), 'HOME': str(self.config)}
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
        for args in [('login',), ('login', '--wait', 'app'), ('login', '--paste', 'app'),
                     ('login', '--callback', 'http://127.0.0.1:53682/callback?code=synthetic'),
                     ('login', '--replace', 'app'), ('logout',), ('instance', 'add'),
                     ('workspace', 'use', 'other'), ('checkout', 'other')]:
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

    def test_saved_connect_profiles_and_pending_login_cannot_override_host(self):
        profiles = self.config / 'instances'
        profiles.mkdir()
        (profiles / 'app').write_text('BEAM_API_KEY=local-key\nBEAM_WORKSPACE_ID=local-workspace\nBEAM_CONNECT=1\n')
        pending = self.config / 'pending'
        pending.mkdir()
        (pending / 'app').write_text('{"code":"local-code","state":"local-state"}')
        before = {str(p.relative_to(self.config)): p.read_bytes() for p in self.config.rglob('*') if p.is_file()}
        result = self.run_cli('checkout')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['workspaceId'], 'host-workspace')
        result = self.run_cli('login', '--wait', 'app')
        self.assertIn('managed_context_locked', result.stderr)
        after = {str(p.relative_to(self.config)): p.read_bytes() for p in self.config.rglob('*') if p.is_file()}
        self.assertEqual(after, before)

    def test_successful_bearer_read_replaces_an_initial_permission_status(self):
        curl = self.config / 'curl'
        curl.write_text('#!/usr/bin/env python3\nimport json,sys\nfrom pathlib import Path\na=sys.argv[1:]\n'
                        'headers=Path(a[a.index("-K")+1]).read_text() if "-K" in a else "\\n".join(a)\n'
                        'success=a[-1].endswith("/auth/access-token") or "Authorization: Bearer synthetic-bearer" in headers\n'
                        'body={"idToken":"synthetic-bearer"} if a[-1].endswith("/auth/access-token") else {"id":"agent-a"}\n'
                        'Path(a[a.index("-o")+1]).write_text(json.dumps(body))\nprint("200" if success else "403",end="")\n')
        curl.chmod(0o755)
        status = self.config / 'http-status'
        env = {**self.env, 'PATH': str(self.config) + os.pathsep + self.env['PATH'], 'BEAM_MANAGED_HTTP_STATUS_FILE': str(status)}
        result = self.run_cli('agents', 'get', 'agent-a', env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['id'], 'agent-a')
        self.assertEqual(status.read_text(), '200')

    def test_python_api_success_replaces_a_previous_auth_status(self):
        spec = importlib.util.spec_from_file_location('beam_managed_builder', ROOT / 'beam/internal/agent-builder/scripts/beam.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        status = self.config / 'http-status'
        status.write_text('401')
        response = io.BytesIO(b'{"id":"agent-a"}')
        response.status = 200
        with patch.dict(os.environ, {**self.env, 'BEAM_MANAGED_HTTP_STATUS_FILE': str(status)}), patch.object(module.urllib.request, 'urlopen', return_value=response):
            self.assertEqual(module._http('GET', 'https://instance.example/agent/agent-a', {})['id'], 'agent-a')
        self.assertEqual(status.read_text(), '200')
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

    def test_manifest_rejects_incomplete_or_unsafe_mappings(self):
        spec = importlib.util.spec_from_file_location('operation_manifest', ROOT / 'beam/bin/operation_manifest.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original = module.manifest()['operations']
        for defect in ('safety', 'confirmation', 'serializer', 'unmapped', 'verification', 'dynamic-command'):
            with self.subTest(defect=defect):
                operations = copy.deepcopy(original)
                operation = operations[0]
                if defect == 'safety': operation['safety'] = 'unknown'
                elif defect == 'confirmation': operation['confirmation'] = 'optional'
                elif defect == 'unmapped': operation['execution']['inputSchema']['properties']['unused'] = {'type': 'string'}
                elif defect == 'verification': operation['postRead'] = 'missing.operation'
                elif defect == 'dynamic-command': operation['execution']['commands'][0][0] = {'field': 'injected', 'kind': 'value'}
                else: operation['execution']['commands'][0].append({'field': 'missing', 'kind': 'shell'})
                with self.assertRaises(ValueError): module.validate_operations(operations)

if __name__ == '__main__': unittest.main()
