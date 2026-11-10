"""Fictional launcher/capture lifecycle test: no tunnel, remote network, or UI.

The gate and helper below are test doubles, not a production supervisor. The
launcher expires normally and performs its own cleanup; no process is killed.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import chat_ready_capture as capture
import test_run_chat_synthetic as launcher_fixture

CHECKS = ('issuer_match', 'resource_match', 'authorization_server_match', 's256',
          'token_auth_none', 'challenge_present', 'challenge_match')

def fake_gate(result):
    """A test-only model of the agreed pre-UI conditions; false on uncertainty."""
    if not isinstance(result, dict) or result.get('schema') != 'chat-discovery-check-v1':
        return False
    requests = result.get('requests')
    checks = result.get('checks')
    if not isinstance(requests, list) or len(requests) != 3 or not isinstance(checks, dict) or set(checks) != set(CHECKS):
        return False
    expected = [('authorization_metadata', 200, None), ('protected_resource_metadata', 200, None), ('mcp', 401, 'http')]
    return (all(isinstance(r, dict) and (r.get('path'), r.get('status'), r.get('error')) == e
                for r, e in zip(requests, expected)) and all(checks[k] is True for k in CHECKS))

def passed():
    return {'schema': 'chat-discovery-check-v1', 'requests': [
        {'path': 'authorization_metadata', 'status': 200, 'error': None},
        {'path': 'protected_resource_metadata', 'status': 200, 'error': None},
        {'path': 'mcp', 'status': 401, 'error': 'http'}], 'checks': {k: True for k in CHECKS}}

class CaptureLifecycleTests(unittest.TestCase):
    def test_fake_checker_gate_refuses_missing_failed_and_unknown(self):
        self.assertTrue(fake_gate(passed()))
        for key in CHECKS:
            for value in (False, None):
                result = passed(); result['checks'][key] = value
                self.assertFalse(fake_gate(result))
        for i in range(3):
            result = passed(); result['requests'][i]['status'] = None
            self.assertFalse(fake_gate(result))
        for result in (None, {}, {'schema':'chat-discovery-check-v1'}, 'timeout'):
            self.assertFalse(fake_gate(result))

    @unittest.skipUnless(sys.platform == 'win32', 'Windows fictional CLI and socket required')
    def test_fictional_launcher_ready_gate_and_normal_cleanup(self):
        fixture_factory = launcher_fixture.BoundaryTests(methodName='test_actual_cli_fictional_oauth_and_socket_read')
        fixture, profile, path, _, source = fixture_factory.synthetic_profile()
        self.addCleanup(fixture_factory.doCleanups)
        profile['lifetime_seconds'] = 6
        profile['startup_timeout_seconds'] = 5
        raw = json.dumps(profile).encode()
        path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        adapter = fixture.base / 'capture-test-adapter'
        adapter.mkdir()
        (adapter / 'sitecustomize.py').write_text(
            'import subprocess,sys,uvicorn,mcp.server.mcpserver\n'
            '_real = subprocess.Popen\n'
            'def fake(argv,*args,**kwargs):\n'
            f'    if not isinstance(argv,list) or not argv or argv[0] != {profile["helper"]["path"]!r}: return _real(argv,*args,**kwargs)\n'
            '    code = "import time; print(\\"https://fake.trycloudflare.com\\",flush=True); time.sleep(20)"\n'
            '    return _real([sys.executable,"-u","-c",code],**kwargs)\n'
            'subprocess.Popen = fake\n', encoding='utf-8')
        env = os.environ.copy(); env['PYTHONPATH'] = str(adapter)
        with capture.reserve(adapter, 'ready.jsonl') as (writer, reader):
            process = subprocess.Popen([sys.executable, '-B', str(source), str(path), digest],
                                       env=env, stdout=writer, stderr=subprocess.DEVNULL)
            try:
                ready = capture.wait_ready(reader, process, 10)
                self.assertEqual(ready['mcp_url'], 'https://fake.trycloudflare.com/mcp')
                self.assertIsNone(process.poll())
                self.assertTrue(fake_gate(passed()))
                failed = passed(); failed['checks']['challenge_match'] = False
                self.assertFalse(fake_gate(failed))
            finally:
                # The fictional launcher owns cleanup. Let its bounded lifetime end.
                process.wait(timeout=20)
            self.assertEqual(process.returncode, 0)
            receipt = json.loads(Path(profile['receipt_path']).read_text(encoding='utf-8'))
            self.assertEqual(receipt['cleanup'], 'complete')
            self.assertEqual(receipt['diagnostic']['reason'], 'lifetime_elapsed')

if __name__ == '__main__': unittest.main()
