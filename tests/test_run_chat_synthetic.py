"""Disposable synthetic-only launcher tests; no real helper or remote access."""
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
import contextlib
import io
import types
import time
import uvicorn
import asyncio
import socket
import _thread
import threading
import base64
import http.client
import os
import queue
import re
from urllib.parse import urlencode, urlsplit, parse_qs
from unittest.mock import patch
import test_managed_memory as fixtures

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import run_chat_synthetic as launcher


class BoundaryTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'win32', 'Windows socket required')
    def test_post_snapshot_stream_changes_do_not_change_receipt(self):
        import run_chat_discovery as shared
        for mode in ('eof', 'read_error', 'late_invalid'):
            with self.subTest(mode=mode):
                fixture, profile, path, _, source = self.synthetic_profile()
                profile['lifetime_seconds'] = profile['startup_timeout_seconds'] = 1
                raw = json.dumps(profile).encode()
                path.write_bytes(raw)
                digest = hashlib.sha256(raw).hexdigest()
                released, pump_updated, final_byte = threading.Event(), threading.Event(), threading.Event()
                class TracingLock:
                    def __init__(self): self.lock = threading.Lock()
                    def __enter__(self): self.lock.acquire(); return self
                    def __exit__(self, *args):
                        if released.is_set() and final_byte.is_set() and threading.current_thread().name == 'synthetic-pump':
                            pump_updated.set()
                        self.lock.release()
                def make_thread(*args, **kwargs):
                    if getattr(kwargs.get('target'), '__name__', '') == 'drain':
                        kwargs['name'] = 'synthetic-pump'
                    return threading.Thread(*args, **kwargs)
                synthetic_threads = types.SimpleNamespace(Thread=make_thread, Lock=TracingLock, Event=threading.Event)
                class Stream:
                    pending = io.BytesIO(b'https://fake.trycloudflare.com:443/PRIVATE_QUERY_CANARY\n')
                    def read(self, size):
                        if not released.wait(5): raise RuntimeError('test timed out')
                        if mode == 'late_invalid':
                            chunk = self.pending.read(size)
                            if chunk in (b'\n', b''): final_byte.set()
                            return chunk
                        final_byte.set()
                        if mode == 'read_error': raise OSError('PRIVATE_STREAM_CANARY')
                        return b''
                class Child:
                    pid = 880
                    alive = True
                    stdout = Stream()
                    pump_completed = False
                    def poll(self): return None if self.alive else 9
                    def terminate(self): self.alive = False; released.set()
                    def wait(self, timeout):
                        self.pump_completed = pump_updated.wait(3)
                        return 9
                    def kill(self): self.alive = False; released.set()
                child = Child()
                guards = []
                original_guard = shared.OutputGuard
                def make_guard():
                    guard = original_guard()
                    guards.append(guard)
                    return guard
                transport = types.SimpleNamespace(create_app=lambda *a, **kw: self.fail('unexpected app'))
                output, errors = io.StringIO(), io.StringIO()
                with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime', return_value=(shared, transport)), patch.object(launcher, 'threading', synthetic_threads), patch.object(shared, 'OutputGuard', side_effect=make_guard), patch.object(shared, '_creation_filetime', return_value=123), patch.object(launcher.subprocess, 'Popen', return_value=child), contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                    self.assertEqual(launcher.main([str(path), digest]), 1)
                self.assertTrue(child.pump_completed)
                self.assertEqual(guards[0].failure_mask, 4 if mode == 'late_invalid' else 0)
                self.assertEqual(guards[0].failed, mode in ('read_error', 'late_invalid'))
                receipt = json.loads(Path(profile['receipt_path']).read_text())
                diag = receipt['diagnostic']
                self.assertEqual(diag['reason'], 'startup_timeout')
                self.assertFalse(diag['stream_eof'])
                self.assertFalse(diag['stream_read_error'])
                self.assertFalse(diag['guard_failed'])
                self.assertFalse(diag['recognized_origin'])
                self.assertEqual(diag['guard_failure_mask'], 0)
                self.assertEqual(diag['pre_cleanup_child'], {'state': 'running', 'exit_code': None})
                self.assertEqual(diag['post_cleanup_child'], {'state': 'exited', 'exit_code': 9})
                self.assertNotIn('PRIVATE_STREAM_CANARY', json.dumps(receipt) + output.getvalue() + errors.getvalue())
                self.assertNotIn('PRIVATE_QUERY_CANARY', json.dumps(receipt) + output.getvalue() + errors.getvalue())

    @unittest.skipUnless(sys.platform == 'win32', 'Windows socket required')
    def test_interrupted_snapshot_remains_unknown_and_cleanup_runs(self):
        import run_chat_discovery as shared
        for failure, reason in ((KeyboardInterrupt(), 'interrupted'), (SystemExit(), 'system_exit')):
            with self.subTest(reason=reason):
                fixture, profile, path, _, source = self.synthetic_profile()
                profile['lifetime_seconds'] = profile['startup_timeout_seconds'] = 1
                raw = json.dumps(profile).encode()
                path.write_bytes(raw)
                digest = hashlib.sha256(raw).hexdigest()
                cleaned = []
                class Child:
                    pid = 881
                    alive = True
                    stdout = io.BytesIO(b'https://fake.trycloudflare.com\n')
                    def poll(self): return None if self.alive else 0
                    def terminate(self): self.alive = False
                    def wait(self, timeout): return 0
                    def kill(self): self.alive = False
                class Server:
                    started = False
                    should_exit = False
                    def __init__(self, config): pass
                    def run(self, sockets):
                        self.started = True
                        while not self.should_exit: time.sleep(.01)
                child = Child()
                app = types.SimpleNamespace(state=types.SimpleNamespace(owner_cleanup=lambda: cleaned.append(True)))
                transport = types.SimpleNamespace(create_app=lambda *a, **kw: app)
                with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime', return_value=(shared, transport)), patch.object(launcher, '_snapshot_observations', side_effect=failure), patch.object(shared, '_creation_filetime', return_value=123), patch.object(launcher.subprocess, 'Popen', return_value=child), patch.object(uvicorn, 'Server', Server), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(launcher.main([str(path), digest]), 1)
                self.assertFalse(child.alive)
                self.assertTrue(cleaned)
                receipt = json.loads(Path(profile['receipt_path']).read_text())
                self.assertEqual(receipt['diagnostic']['reason'], reason)
                self.assertEqual(receipt['cleanup'], 'complete')
                for field in ('guard_failed', 'recognized_origin', 'stream_eof', 'stream_read_error', 'guard_failure_mask'):
                    self.assertIsNone(receipt['diagnostic'][field])
    def test_child_observation_is_bounded_and_never_echoes_errors(self):
        class Child:
            def __init__(self, value): self.value = value
            def poll(self):
                if isinstance(self.value, BaseException): raise self.value
                return self.value
        for value, state, code in [(None, 'running', None), (0, 'exited', 0),
                                   (-15, 'exited', -15), (2**32 - 1, 'exited', 2**32 - 1),
                                   (2**50, 'exited', None), (True, 'unknown', None),
                                   (ValueError('PRIVATE_EXIT_CANARY'), 'unknown', None)]:
            with self.subTest(value=type(value).__name__):
                observation = launcher._child_observation(Child(value))
                self.assertEqual(observation, {'state': state, 'exit_code': code})
                self.assertNotIn('PRIVATE_EXIT_CANARY', str(observation))
        self.assertEqual(launcher._child_observation(None), {'state': 'not_started', 'exit_code': None})

    @unittest.skipUnless(sys.platform == 'win32', 'Windows socket required')
    def test_spawn_failure_diagnostic_is_unknown_and_redacted(self):
        import run_chat_discovery as shared
        fixture, profile, path, digest, source = self.synthetic_profile()
        transport = types.SimpleNamespace(create_app=lambda *a, **kw: self.fail('unexpected app'))
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime', return_value=(shared, transport)), patch.object(launcher.subprocess, 'Popen', side_effect=OSError('PRIVATE_SPAWN_PATH_CANARY')), contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(launcher.main([str(path), digest]), 1)
        text = Path(profile['receipt_path']).read_text()
        diagnostic = json.loads(text)['diagnostic']
        self.assertEqual(diagnostic['phase'], 'helper_spawn')
        self.assertEqual(diagnostic['reason'], 'stage_error')
        self.assertEqual(diagnostic['pre_cleanup_child'], {'state': 'not_started', 'exit_code': None})
        self.assertEqual(diagnostic['post_cleanup_child'], {'state': 'not_started', 'exit_code': None})
        for name in ('guard_failed', 'recognized_origin', 'stream_eof', 'stream_read_error', 'guard_failure_mask', 'owner_cleanup_failed'):
            self.assertIsNone(diagnostic[name])
        self.assertNotIn('PRIVATE_SPAWN_PATH_CANARY', text + output.getvalue() + errors.getvalue())
    @unittest.skipUnless(sys.platform == 'win32', 'Windows socket required')
    def test_startup_diagnostics_distinguish_child_guard_read_error_and_eof(self):
        import run_chat_discovery as shared
        for mode in ('child_exit', 'guard', 'read_error', 'eof_without_newline'):
            with self.subTest(mode=mode):
                fixture, profile, path, _, source = self.synthetic_profile()
                profile['lifetime_seconds'] = profile['startup_timeout_seconds'] = 1
                raw = json.dumps(profile).encode()
                path.write_bytes(raw)
                digest = hashlib.sha256(raw).hexdigest()
                class ErrorStream:
                    def read(self, size): raise OSError('PRIVATE_PATH_SECRET_CANARY')
                class Child:
                    pid = 780
                    alive = mode != 'child_exit'
                    stdout = (ErrorStream() if mode == 'read_error' else io.BytesIO(
                        b'https://bad.trycloudflare.com:443/PRIVATE_QUERY_CANARY\n' if mode == 'guard' else
                        b'https://fake.trycloudflare.com' if mode == 'eof_without_newline' else b''))
                    def poll(self): return None if self.alive else (17 if mode == 'child_exit' else 9)
                    def terminate(self): self.alive = False
                    def wait(self, timeout): return self.poll()
                    def kill(self): self.alive = False
                child = Child()
                factory_calls = []
                transport = types.SimpleNamespace(create_app=lambda *a, **kw: factory_calls.append(True))
                out, err = io.StringIO(), io.StringIO()
                with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime', return_value=(shared, transport)), patch.object(shared, '_creation_filetime', return_value=123), patch.object(launcher.subprocess, 'Popen', return_value=child), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    self.assertEqual(launcher.main([str(path), digest]), 1)
                self.assertEqual(factory_calls, [])
                receipt_text = Path(profile['receipt_path']).read_text()
                diag = json.loads(receipt_text)['diagnostic']
                self.assertLessEqual(len(json.dumps(diag).encode()), 1024)
                self.assertEqual(diag['phase'], 'output_startup')
                self.assertEqual(diag['reason'], {'child_exit': 'child_exited', 'guard': 'guard_rejected',
                                                  'read_error': 'stream_read_error',
                                                  'eof_without_newline': 'startup_timeout'}[mode])
                self.assertIsInstance(diag['elapsed_ms'], int)
                self.assertLessEqual(diag['elapsed_ms'], 86400000)
                self.assertEqual(diag['pre_cleanup_child']['state'], 'exited' if mode == 'child_exit' else 'running')
                self.assertEqual(diag['pre_cleanup_child']['exit_code'], 17 if mode == 'child_exit' else None)
                self.assertEqual(diag['post_cleanup_child']['state'], 'exited')
                self.assertEqual(diag['post_cleanup_child']['exit_code'], 17 if mode == 'child_exit' else 9)
                if mode == 'eof_without_newline':
                    self.assertTrue(diag['stream_eof'])
                    self.assertFalse(diag['recognized_origin'])
                if mode == 'read_error': self.assertTrue(diag['stream_read_error'])
                if mode == 'guard': self.assertTrue(diag['guard_failed'])
                if mode == 'read_error': self.assertEqual(diag['guard_failure_mask'], 0)
                if mode == 'guard': self.assertEqual(diag['guard_failure_mask'], 4)
                if mode == 'eof_without_newline': self.assertEqual(diag['guard_failure_mask'], 0)
                for canary in ('PRIVATE_PATH_SECRET_CANARY', 'PRIVATE_QUERY_CANARY'):
                    self.assertNotIn(canary, receipt_text + out.getvalue() + err.getvalue())
                self.assertNotIn('trycloudflare.com', json.dumps(diag))
                self.assertNotIn('s' * 43, receipt_text + out.getvalue() + err.getvalue())

    def test_elapsed_milliseconds_are_bounded_or_unknown(self):
        for current, expected in [(-1, 0), (1.25, 1250), (1000000, 86400000), (float('nan'), None)]:
            with self.subTest(current=current), patch.object(launcher, 'time', types.SimpleNamespace(monotonic=lambda: current)):
                self.assertEqual(launcher._elapsed_ms(0), expected)
        self.assertIsNone(launcher._elapsed_ms(None))
        def interrupted(): raise KeyboardInterrupt()
        with patch.object(launcher, 'time', types.SimpleNamespace(monotonic=interrupted)), self.assertRaises(KeyboardInterrupt):
            launcher._elapsed_ms(0)

    @unittest.skipUnless(sys.platform == 'win32', 'Windows socket required')
    def test_interrupt_during_child_observation_still_cleans_up(self):
        import run_chat_discovery as shared
        fixture, profile, path, _, source = self.synthetic_profile()
        profile['lifetime_seconds'] = profile['startup_timeout_seconds'] = 1
        raw = json.dumps(profile).encode()
        path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        cleaned = []
        class Child:
            pid = 781
            alive = True
            stdout = io.BytesIO(b'https://fake.trycloudflare.com\n')
            def poll(self): return None if self.alive else 0
            def terminate(self): self.alive = False
            def wait(self, timeout): return 0
            def kill(self): self.alive = False
        class Server:
            started = False
            should_exit = False
            def __init__(self, config): pass
            def run(self, sockets):
                self.started = True
                while not self.should_exit: time.sleep(.01)
        child = Child()
        app = types.SimpleNamespace(state=types.SimpleNamespace(owner_cleanup=lambda: cleaned.append(True)))
        transport = types.SimpleNamespace(create_app=lambda *a, **kw: app)
        original = launcher._child_observation
        count = []
        def observe(value):
            count.append(True)
            if len(count) == 1: raise KeyboardInterrupt()
            return original(value)
        with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime', return_value=(shared, transport)), patch.object(launcher, '_child_observation', side_effect=observe), patch.object(shared, '_creation_filetime', return_value=123), patch.object(launcher.subprocess, 'Popen', return_value=child), patch.object(uvicorn, 'Server', Server), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launcher.main([str(path), digest]), 1)
        self.assertFalse(child.alive)
        self.assertTrue(cleaned)
        receipt = json.loads(Path(profile['receipt_path']).read_text())
        self.assertEqual(receipt['status'], 'error')
        self.assertEqual(receipt['diagnostic']['reason'], 'interrupted')
        self.assertEqual(receipt['diagnostic']['pre_cleanup_child'], {'state': 'unknown', 'exit_code': None})
    @unittest.skipUnless(sys.platform == 'win32', 'Windows socket required')
    def test_real_owner_cleanup_before_and_after_lifespan(self):
        import run_chat_discovery as shared
        import chat_recall_http as transport_module
        for mode in ('pre_lifespan_failure', 'normal_lifespan'):
            with self.subTest(mode=mode):
                fixture, profile, path, _, source = self.synthetic_profile()
                profile['lifetime_seconds'] = profile['startup_timeout_seconds'] = 2
                raw = json.dumps(profile).encode()
                path.write_bytes(raw)
                digest = hashlib.sha256(raw).hexdigest()
                captured = []
                class Child:
                    pid = 566
                    alive = True
                    stdout = io.BytesIO(b'https://fake.trycloudflare.com\n')
                    def poll(self): return None if self.alive else 0
                    def terminate(self): self.alive = False
                    def wait(self, timeout): return 0
                    def kill(self): self.alive = False
                class Server:
                    started = False
                    should_exit = False
                    def __init__(self, app): self.app = app
                    def run(self, sockets):
                        async def run_lifespan():
                            async with self.app.router.lifespan_context(self.app):
                                self.started = True
                                while not self.should_exit: await asyncio.sleep(.01)
                        asyncio.run(run_lifespan())
                def factory(*args, **kwargs):
                    app = transport_module.create_app(*args, **kwargs)
                    owner = next(m.kwargs['owner'] for m in app.user_middleware if 'owner' in m.kwargs)
                    owner._tokens['synthetic-token'] = (time.time() + 60, object())
                    owner._tickets['synthetic-ticket'] = object()
                    captured.append(owner)
                    return app
                def make_config(app, **kwargs):
                    if mode == 'pre_lifespan_failure': raise RuntimeError('synthetic startup failure')
                    return app
                child = Child()
                with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime', return_value=(shared, types.SimpleNamespace(create_app=factory))), patch.object(shared, '_creation_filetime', return_value=123), patch.object(launcher.subprocess, 'Popen', return_value=child), patch.object(uvicorn, 'Config', side_effect=make_config), patch.object(uvicorn, 'Server', Server), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(launcher.main([str(path), digest]), 1 if mode == 'pre_lifespan_failure' else 0)
                self.assertEqual(len(captured), 1)
                self.assertTrue(captured[0]._closed)
                self.assertEqual(captured[0]._tokens, {})
                self.assertEqual(captured[0]._tickets, {})
                self.assertFalse(child.alive)
    @unittest.skipUnless(sys.platform == 'win32', 'Windows CLI required')
    def test_cli_refuses_preloaded_foreign_local_module_before_intent(self):
        fixture, profile, path, digest, source = self.synthetic_profile()
        adapter = fixture.base / 'foreign-adapter'
        adapter.mkdir()
        (adapter / 'sitecustomize.py').write_text(
            'import sys,types\n'
            'm=types.ModuleType("chat_recall_http")\n'
            'm.__file__="C:/foreign/chat_recall_http.py"\n'
            'sys.modules["chat_recall_http"]=m\n', encoding='utf-8')
        env = os.environ.copy()
        env['PYTHONPATH'] = str(adapter)
        result = launcher.subprocess.run([sys.executable, '-B', str(source), str(path), digest],
                                         env=env, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, b'')
        self.assertFalse(Path(profile['intent_path']).exists())
        self.assertFalse(Path(profile['receipt_path']).exists())
    @unittest.skipUnless(sys.platform == 'win32', 'Windows CLI and socket required')
    def test_actual_cli_fictional_oauth_and_socket_read(self):
        fixture, profile, path, _, source = self.synthetic_profile()
        profile['lifetime_seconds'] = 8
        profile['startup_timeout_seconds'] = 5
        raw = json.dumps(profile).encode()
        path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        fixed_paths = set(profile['closure']) | {str(path), profile['helper']['path'], profile['config']['path'],
                                                profile['owner_code']['path']} | {str(Path(profile['runtime_dir']) / name) for name in profile['runtime']}
        before = {name: Path(name).read_bytes() for name in fixed_paths}
        adapter = fixture.base / 'test-adapter'
        adapter.mkdir()
        port_path = adapter / 'listener-port.txt'
        (adapter / 'sitecustomize.py').write_text(
            'import subprocess, sys, socket, pathlib, uvicorn, mcp.server.mcpserver\n'
            '_real_popen = subprocess.Popen\n'
            'def synthetic_helper(argv, *args, **kwargs):\n'
            f'    if not isinstance(argv, list) or not argv or argv[0] != {profile["helper"]["path"]!r}: return _real_popen(argv, *args, **kwargs)\n'
            '    code = "import time; print(\\"https://fake.trycloudflare.com\\", flush=True); time.sleep(12)"\n'
            '    return _real_popen([sys.executable, "-u", "-c", code], **kwargs)\n'
            'subprocess.Popen = synthetic_helper\n'
            '_real_bind = socket.socket.bind\n'
            'def record_bind(self, address):\n'
            '    result = _real_bind(self, address)\n'
            f'    if address == ("127.0.0.1", 0) and self.getsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE): pathlib.Path({str(port_path)!r}).write_text(str(self.getsockname()[1]))\n'
            '    return result\n'
            'socket.socket.bind = record_bind\n', encoding='utf-8')
        env = os.environ.copy()
        env['PYTHONPATH'] = str(adapter)
        process = launcher.subprocess.Popen([sys.executable, '-B', str(source), str(path), digest],
                                           env=env, stdout=launcher.subprocess.PIPE, stderr=launcher.subprocess.PIPE)
        lines = queue.Queue()
        threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True).start()
        try:
            ready = lines.get(timeout=12)
            receipt_path = Path(profile['receipt_path'])
            detail = receipt_path.read_text() if receipt_path.exists() else 'no receipt'
            self.assertTrue(ready, 'no ready output from synthetic CLI: ' + detail)
            self.assertIsNone(process.poll())
            self.assertEqual(json.loads(ready), {'status': 'synthetic-only', 'origin': 'https://fake.trycloudflare.com',
                                                 'mcp_url': 'https://fake.trycloudflare.com/mcp'})
            port = int(port_path.read_text())
            def request(method, route, body=None, headers=None):
                conn = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
                try:
                    conn.request(method, route, body=body, headers={'Host': 'fake.trycloudflare.com', **(headers or {})})
                    response = conn.getresponse()
                    return response.status, dict((k.lower(), v) for k, v in response.getheaders()), response.read()
                finally:
                    conn.close()
            mcp_call = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}
            headers = {'content-type': 'application/json', 'accept': 'application/json, text/event-stream',
                       'mcp-protocol-version': '2025-03-26'}
            status, _, body = request('POST', '/mcp', json.dumps(mcp_call).encode(), headers)
            self.assertEqual(status, 401)
            self.assertNotIn(b'DENIED_CANARY', body)
            unauthorized_call = {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
                                 'params': {'name': 'read_managed_memory', 'arguments': {'note_id': 'decision'}}}
            status, _, body = request('POST', '/mcp', json.dumps(unauthorized_call).encode(), headers)
            self.assertEqual(status, 401)
            self.assertNotIn(b'amber-kite', body)
            verifier = 'v' * 43
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
            origin = 'https://fake.trycloudflare.com'
            params = {'client_id': 'synthetic-client', 'redirect_uri': profile['callback'], 'response_type': 'code',
                      'scope': 'memory:read', 'state': 'synthetic-state', 'code_challenge': challenge,
                      'code_challenge_method': 'S256', 'resource': origin + '/mcp'}
            status, response_headers, _ = request('GET', '/authorize?' + urlencode(params))
            self.assertEqual(status, 302)
            consent = urlsplit(response_headers['location'])
            status, _, page = request('GET', '/consent?' + consent.query)
            self.assertEqual(status, 200)
            ticket = re.search(rb'name="ticket" value="([^"]+)"', page).group(1).decode()
            csrf = re.search(rb'name="csrf" value="([^"]+)"', page).group(1).decode()
            form = urlencode({'ticket': ticket, 'csrf': csrf, 'owner_code': 's' * 43})
            status, response_headers, _ = request('POST', '/consent', form,
                {'origin': origin, 'content-type': 'application/x-www-form-urlencoded', 'cookie': 'brain_csrf=' + csrf})
            self.assertEqual(status, 303)
            code = parse_qs(urlsplit(response_headers['location']).query)['code'][0]
            token_form = urlencode({'grant_type': 'authorization_code', 'client_id': 'synthetic-client',
                'redirect_uri': profile['callback'], 'code': code, 'code_verifier': verifier, 'resource': origin + '/mcp'})
            status, _, body = request('POST', '/token', token_form, {'content-type': 'application/x-www-form-urlencoded'})
            self.assertEqual(status, 200)
            access_token = json.loads(body)['access_token']
            headers['authorization'] = 'Bearer ' + access_token
            def tool(name, arguments):
                payload = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': name, 'arguments': arguments}}
                status, _, result = request('POST', '/mcp', json.dumps(payload).encode(), headers)
                self.assertEqual(status, 200)
                return result
            search = tool('search_managed_memory', {'query': 'amber'})
            self.assertIn(b'decision', search)
            self.assertIn(fixture.entry()['sha256'].encode(), search)
            reading = tool('read_managed_memory', {'note_id': 'decision', 'start_line': 1, 'line_count': 5})
            self.assertIn(fixture.entry()['sha256'].encode(), reading)
            parsed = json.loads(reading)['result']
            content = parsed.get('structuredContent') or json.loads(parsed['content'][0]['text'])
            self.assertEqual(content['note_id'], 'decision')
            expected = fixture.note.read_text(encoding='utf-8').splitlines()[:5]
            self.assertEqual(content['lines'], [{'line': i + 1, 'text': line} for i, line in enumerate(expected)])
            denied = tool('read_managed_memory', {'note_id': 'denied', 'start_line': 1, 'line_count': 5})
            self.assertNotIn(b'DENIED_CANARY', denied)
            self.assertIn(b'MANAGED_RECALL_REFUSED', denied)
            self.assertEqual(before, {name: Path(name).read_bytes() for name in fixed_paths})
            remaining, stderr = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, stderr.decode(errors='replace'))
            self.assertEqual(remaining, b'')
            self.assertNotIn(('s' * 43).encode(), ready + remaining + stderr)
            self.assertNotIn(access_token.encode(), ready + remaining + stderr)
            self.assertEqual(before, {name: Path(name).read_bytes() for name in fixed_paths})
        finally:
            if process.poll() is None:
                try: process.communicate(timeout=15)
                except launcher.subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate(timeout=5)
    @unittest.skipUnless(sys.platform == 'win32', 'Windows fictional CLI required')
    def test_stop_marker_requests_owned_cleanup_after_ready(self):
        fixture, profile, path, _, source = self.synthetic_profile()
        profile['lifetime_seconds'] = 15
        profile['startup_timeout_seconds'] = 6
        raw = json.dumps(profile).encode(); path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        adapter = fixture.base / 'stop-test-adapter'; adapter.mkdir()
        helper_code = 'import time;print("https://fake.trycloudflare.com",flush=True);time.sleep(30)'
        (adapter/'sitecustomize.py').write_text(
            'import subprocess,sys,uvicorn,mcp.server.mcpserver\n'
            '_real=subprocess.Popen\n'
            'def fake(argv,*args,**kwargs):\n'
            f'    if not isinstance(argv,list) or not argv or argv[0] != {profile["helper"]["path"]!r}: return _real(argv,*args,**kwargs)\n'
            f'    return _real([sys.executable,"-u","-c",{helper_code!r}],**kwargs)\n'
            'subprocess.Popen=fake\n',encoding='utf-8')
        env=os.environ.copy(); env['PYTHONPATH']=str(adapter)
        process=subprocess.Popen([sys.executable,'-B',str(source),str(path),digest],env=env,
                                 stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        received=queue.Queue()
        threading.Thread(target=lambda: received.put(process.stdout.readline()),daemon=True).start()
        try:
            ready=received.get(timeout=12)
            self.assertEqual(json.loads(ready)['status'],'synthetic-only')
            stop=Path(profile['intent_path']+'.stop.json')
            with stop.open('xb') as request: request.write(b'stop\n')
            self.assertEqual(process.wait(timeout=10),1)
            receipt=json.loads(Path(profile['receipt_path']).read_text())
            self.assertEqual(receipt['cleanup'],'complete')
            self.assertEqual(receipt['diagnostic']['reason'],'stop_requested')
            self.assertEqual(receipt['diagnostic']['post_cleanup_child']['state'],'exited')
        finally:
            if process.poll() is None:
                try: process.wait(timeout=20)
                except subprocess.TimeoutExpired: self.fail('synthetic launcher did not finish')
            process.stdout.close()
    def test_existing_stop_marker_refused_before_intent(self):
        fixture, profile, path, digest, source = self.synthetic_profile()
        Path(profile['intent_path']+'.stop.json').write_bytes(b'preserve')
        with patch.object(launcher,'__file__',str(source)):
            self.assertEqual(launcher.main([str(path),digest]),1)
        self.assertEqual(Path(profile['intent_path']+'.stop.json').read_bytes(),b'preserve')
        self.assertFalse(Path(profile['intent_path']).exists())
    def test_profile_scope_and_limit_refusals_precede_runtime(self):
        variants = [('state', 'pending'), ('scope', 'metadata-only'), ('additional_spend_usd', True),
                    ('lifetime_seconds', 901), ('startup_timeout_seconds', 61),
                    ('recipients', ['Cloudflare', 'OpenAI']), ('callback', 'https://client.example'),
                    ('callback', 'https://client.example/callback?query=forbidden'),
                    ('callback', 'https://client.example:wrong/callback'), ('unknown', 'refuse')]
        for name, value in variants:
            with self.subTest(name=name, value=value):
                fixture, profile, path, _, source = self.synthetic_profile()
                profile[name] = value
                raw = json.dumps(profile).encode()
                path.write_bytes(raw)
                with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime') as runtime:
                    self.assertEqual(launcher.main([str(path), hashlib.sha256(raw).hexdigest()]), 1)
                    runtime.assert_not_called()

    def test_runtime_helper_and_secret_drift_precede_runtime_load(self):
        for kind in ('runtime', 'helper', 'owner_code'):
            with self.subTest(kind=kind):
                fixture, profile, path, digest, source = self.synthetic_profile()
                target = (Path(profile['runtime_dir']) / 'chat_recall_http.py' if kind == 'runtime'
                          else Path(profile[kind]['path']))
                target.write_bytes(b'DRIFT_CANARY')
                with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime') as runtime:
                    self.assertEqual(launcher.main([str(path), digest]), 1)
                    runtime.assert_not_called()

    def test_record_collisions_refuse_and_preserve_bytes(self):
        for name in ('intent_path', 'receipt_path', 'hold'):
            with self.subTest(name=name):
                fixture, profile, path, digest, source = self.synthetic_profile()
                record = Path(profile['intent_path'] + '.hold.json') if name == 'hold' else Path(profile[name])
                record.write_bytes(b'PRESERVE_CANARY')
                with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime') as runtime:
                    self.assertEqual(launcher.main([str(path), digest]), 1)
                    runtime.assert_not_called()
                self.assertEqual(record.read_bytes(), b'PRESERVE_CANARY')
    @unittest.skipUnless(sys.platform == 'win32', 'Windows socket required')
    def test_blocked_owner_cleanup_reports_hold_until_close_returns(self):
        import run_chat_discovery as shared
        fixture, profile, path, _, source = self.synthetic_profile()
        profile['lifetime_seconds'] = profile['startup_timeout_seconds'] = 1
        raw = json.dumps(profile).encode()
        path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        hold = Path(profile['intent_path'] + '.hold.json')
        observed = []
        class Child:
            pid = 565
            alive = True
            stdout = io.BytesIO(b'https://fake.trycloudflare.com\n')
            def poll(self): return None if self.alive else 0
            def terminate(self): self.alive = False
            def wait(self, timeout): return 0
            def kill(self): self.alive = False
        class Server:
            started = False
            should_exit = False
            def __init__(self, config): pass
            def run(self, sockets):
                self.started = True
                while not self.should_exit: time.sleep(.01)
        def close_owner():
            deadline = time.monotonic() + 5
            record = None
            while record is None and time.monotonic() < deadline:
                try: record = json.loads(hold.read_text())
                except (OSError, ValueError): time.sleep(.01)
            if record is not None:
                record['receipt_exists'] = Path(profile['receipt_path']).exists()
                with socket.socket() as competitor:
                    try:
                        competitor.bind(('127.0.0.1', record['port']))
                        record['blocked'] = False
                    except OSError:
                        record['blocked'] = True
                observed.append(record)
        app = types.SimpleNamespace(state=types.SimpleNamespace(owner_cleanup=close_owner))
        transport = types.SimpleNamespace(create_app=lambda *a, **kw: app)
        with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime', return_value=(shared, transport)), patch.object(shared, '_creation_filetime', return_value=123), patch.object(launcher.subprocess, 'Popen', return_value=Child()), patch.object(uvicorn, 'Server', Server), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(launcher.main([str(path), digest]), 0)
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0]['reason'], 'owner')
        self.assertTrue(observed[0]['blocked'])
        self.assertFalse(observed[0]['receipt_exists'])
    @unittest.skipUnless(sys.platform == 'win32', 'Windows socket required')
    def test_owner_cleanup_retry_retains_listener_until_close_succeeds(self):
        import run_chat_discovery as shared
        fixture, profile, path, _, source = self.synthetic_profile()
        profile['lifetime_seconds'] = profile['startup_timeout_seconds'] = 1
        raw = json.dumps(profile).encode()
        path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        observed, output = [], io.StringIO()
        class Child:
            pid = 564
            alive = True
            stdout = io.BytesIO(b'https://fake.trycloudflare.com\n')
            def poll(self): return None if self.alive else 0
            def terminate(self): self.alive = False
            def wait(self, timeout): return 0
            def kill(self): self.alive = False
        class Server:
            started = False
            should_exit = False
            def __init__(self, config): pass
            def run(self, sockets):
                self.started = True
                while not self.should_exit: time.sleep(.01)
        def close_owner():
            if not observed:
                observed.append('failed')
                raise RuntimeError('synthetic close failure')
            hold = json.loads(Path(profile['intent_path'] + '.hold.json').read_text())
            with socket.socket() as competitor:
                try:
                    competitor.bind(('127.0.0.1', hold['port']))
                    observed.append('unprotected')
                except OSError:
                    observed.append('protected')
        app = types.SimpleNamespace(state=types.SimpleNamespace(owner_cleanup=close_owner))
        transport = types.SimpleNamespace(create_app=lambda *a, **kw: app)
        with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime', return_value=(shared, transport)), patch.object(shared, '_creation_filetime', return_value=123), patch.object(launcher.subprocess, 'Popen', return_value=Child()), patch.object(uvicorn, 'Server', Server), contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(launcher.main([str(path), digest]), 1)
        self.assertEqual(observed, ['failed', 'protected'])
        self.assertEqual(json.loads(Path(profile['intent_path'] + '.hold.json').read_text())['reason'], 'owner')
        receipt = json.loads(Path(profile['receipt_path']).read_text())
        self.assertEqual(receipt['status'], 'error')
        self.assertTrue(receipt['diagnostic']['owner_cleanup_failed'])
    @unittest.skipUnless(sys.platform == 'win32', 'Windows socket required')
    def test_server_hold_keeps_listener_and_reports_identity(self):
        import run_chat_discovery as shared
        fixture, profile, path, _, source = self.synthetic_profile()
        profile['lifetime_seconds'] = profile['startup_timeout_seconds'] = 1
        raw = json.dumps(profile).encode()
        path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        hold = Path(profile['intent_path'] + '.hold.json')
        observations = []
        cleaned = []
        class Child:
            pid = 563
            alive = True
            stdout = io.BytesIO(b'https://fake.trycloudflare.com\n')
            def poll(self): return None if self.alive else 0
            def terminate(self): self.alive = False
            def wait(self, timeout): return 0
            def kill(self): self.alive = False
        class Server:
            started = False
            should_exit = False
            def __init__(self, config): pass
            def run(self, sockets):
                self.started = True
                deadline = time.monotonic() + 5
                record = None
                while record is None and time.monotonic() < deadline:
                    try: record = json.loads(hold.read_text())
                    except (OSError, ValueError): time.sleep(.01)
                if record is not None:
                    record['owner_closed'] = bool(cleaned)
                    record['receipt_exists'] = Path(profile['receipt_path']).exists()
                    with socket.socket() as competitor:
                        try:
                            competitor.bind(('127.0.0.1', record['port']))
                            record['blocked'] = False
                        except OSError:
                            record['blocked'] = True
                    observations.append(record)
        app = types.SimpleNamespace(state=types.SimpleNamespace(owner_cleanup=lambda: cleaned.append(True)))
        transport = types.SimpleNamespace(create_app=lambda *a, **kw: app)
        with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime', return_value=(shared, transport)), patch.object(shared, '_creation_filetime', return_value=123), patch.object(launcher.subprocess, 'Popen', return_value=Child()), patch.object(uvicorn, 'Server', Server), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(launcher.main([str(path), digest]), 0)
        self.assertTrue(cleaned)
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0]['reason'], 'server')
        self.assertGreater(observations[0]['server_native_id'], 0)
        self.assertTrue(observations[0]['blocked'])
        self.assertTrue(observations[0]['owner_closed'])
        self.assertFalse(observations[0]['receipt_exists'])
    @unittest.skipUnless(sys.platform == 'win32', 'Windows socket required')
    def test_late_server_start_without_ready_is_error(self):
        import run_chat_discovery as shared
        fixture, profile, path, digest, source = self.synthetic_profile()
        started = threading.Event()
        cleaned = []
        class Child:
            pid = 562
            alive = True
            stdout = io.BytesIO(b'https://fake.trycloudflare.com\n')
            def poll(self): return None if self.alive else 0
            def terminate(self): self.alive = False
            def wait(self, timeout): return 0
            def kill(self): self.alive = False
        class Server:
            started = False
            should_exit = False
            def __init__(self, config): pass
            def run(self, sockets):
                self.started = True
                started.set()
                while not self.should_exit: time.sleep(.01)
        def thread_factory(*args, **kwargs):
            thread = threading.Thread(*args, **kwargs)
            if kwargs.get('target').__name__ == 'serve':
                start = thread.start
                def synchronized_start():
                    start()
                    if not started.wait(3): raise RuntimeError('synthetic server did not start')
                thread.start = synchronized_start
            return thread
        clock = types.SimpleNamespace(monotonic=lambda: 10 if started.is_set() else 0, sleep=time.sleep)
        threads = types.SimpleNamespace(Thread=thread_factory, Lock=threading.Lock, Event=threading.Event)
        child, output = Child(), io.StringIO()
        app = types.SimpleNamespace(state=types.SimpleNamespace(owner_cleanup=lambda: cleaned.append(True)))
        transport = types.SimpleNamespace(create_app=lambda *a, **kw: app)
        with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime', return_value=(shared, transport)), patch.object(launcher, 'time', clock), patch.object(launcher, 'threading', threads), patch.object(shared, '_creation_filetime', return_value=123), patch.object(launcher.subprocess, 'Popen', return_value=child), patch.object(uvicorn, 'Server', Server), contextlib.redirect_stdout(output):
            self.assertEqual(launcher.main([str(path), digest]), 1)
        self.assertTrue(started.is_set())
        self.assertFalse(child.alive)
        self.assertTrue(cleaned)
        self.assertEqual(output.getvalue(), '')
        receipt = json.loads(Path(profile['receipt_path']).read_text())
        self.assertEqual(receipt['status'], 'error')
        self.assertEqual(receipt['diagnostic']['reason'], 'ready_not_emitted')
    @unittest.skipUnless(sys.platform == 'win32', 'Windows socket required')
    def test_lifetime_includes_slow_helper_start(self):
        import run_chat_discovery as shared
        fixture, profile, path, _, source = self.synthetic_profile()
        profile['lifetime_seconds'] = profile['startup_timeout_seconds'] = 1
        raw = json.dumps(profile).encode()
        path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        clock = {'now': 0}
        class Child:
            pid = 560
            alive = True
            stdout = io.BytesIO(b'https://fake.trycloudflare.com\n')
            def poll(self): return None if self.alive else 0
            def terminate(self): self.alive = False
            def wait(self, timeout): return 0
            def kill(self): self.alive = False
        child = Child()
        def popen(*args, **kwargs):
            clock['now'] = 2
            return child
        def tick(delay):
            clock['now'] += .1
            time.sleep(.001)
        synthetic_clock = types.SimpleNamespace(monotonic=lambda: clock['now'], sleep=tick)
        created = []
        def create_app(*args, **kwargs):
            created.append(True)
            raise ValueError('synthetic factory')
        transport = types.SimpleNamespace(create_app=create_app)
        output = io.StringIO()
        with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime', return_value=(shared, transport)), patch.object(launcher, 'time', synthetic_clock), patch.object(shared, '_creation_filetime', return_value=123), patch.object(launcher.subprocess, 'Popen', side_effect=popen), contextlib.redirect_stdout(output):
            self.assertEqual(launcher.main([str(path), digest]), 1)
        self.assertFalse(child.alive)
        self.assertEqual(created, [])
        self.assertEqual(output.getvalue(), '')
        receipt = json.loads(Path(profile['receipt_path']).read_text())
        self.assertEqual(receipt['status'], 'error')
        self.assertEqual(receipt['diagnostic']['reason'], 'startup_timeout')

    @unittest.skipUnless(sys.platform == 'win32', 'Windows socket required')
    def test_startup_deadline_includes_slow_app_construction(self):
        import run_chat_discovery as shared
        fixture, profile, path, digest, source = self.synthetic_profile()
        clock = {'now': 0}
        cleaned = []
        class Child:
            pid = 561
            alive = True
            stdout = io.BytesIO(b'https://fake.trycloudflare.com\n')
            def poll(self): return None if self.alive else 0
            def terminate(self): self.alive = False
            def wait(self, timeout): return 0
            def kill(self): self.alive = False
        def tick(delay):
            clock['now'] += .001
            time.sleep(.001)
        synthetic_clock = types.SimpleNamespace(monotonic=lambda: clock['now'], sleep=tick)
        app = types.SimpleNamespace(state=types.SimpleNamespace(owner_cleanup=lambda: cleaned.append(True)))
        def create_app(*args, **kwargs):
            clock['now'] = 10
            return app
        child, output = Child(), io.StringIO()
        with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime', return_value=(shared, types.SimpleNamespace(create_app=create_app))), patch.object(launcher, 'time', synthetic_clock), patch.object(shared, '_creation_filetime', return_value=123), patch.object(launcher.subprocess, 'Popen', return_value=child), patch.object(uvicorn, 'Server') as server, contextlib.redirect_stdout(output):
            self.assertEqual(launcher.main([str(path), digest]), 1)
            server.assert_not_called()
        self.assertTrue(cleaned)
        self.assertFalse(child.alive)
        self.assertEqual(output.getvalue(), '')
    @unittest.skipUnless(sys.platform == 'win32', 'Windows socket required')
    def test_final_receipt_collision_preserves_existing_bytes(self):
        import run_chat_discovery as shared
        fixture, profile, path, _, source = self.synthetic_profile()
        profile['lifetime_seconds'] = 1
        raw = json.dumps(profile).encode()
        path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        receipt = Path(profile['receipt_path'])
        class Child:
            pid = 558
            alive = True
            stdout = io.BytesIO(b'https://fake.trycloudflare.com\n')
            def poll(self): return None if self.alive else 0
            def terminate(self):
                self.alive = False
                receipt.write_bytes(b'PRESERVE_EXISTING_BYTES')
            def wait(self, timeout): return 0
            def kill(self): self.alive = False
        class Server:
            started = False
            should_exit = False
            def __init__(self, config): pass
            def run(self, sockets):
                self.started = True
                while not self.should_exit: time.sleep(.01)
        cleaned = []
        app = types.SimpleNamespace(state=types.SimpleNamespace(owner_cleanup=lambda: cleaned.append(True)))
        transport = types.SimpleNamespace(create_app=lambda *a, **kw: app)
        with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime', return_value=(shared, transport)), patch.object(shared, '_creation_filetime', return_value=123), patch.object(launcher.subprocess, 'Popen', return_value=Child()), patch.object(uvicorn, 'Server', Server), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launcher.main([str(path), digest]), 1)
        self.assertTrue(cleaned)
        self.assertEqual(receipt.read_bytes(), b'PRESERVE_EXISTING_BYTES')

    @unittest.skipUnless(sys.platform == 'win32', 'Windows socket required')
    def test_oversized_helper_output_stops_without_ready_or_app(self):
        import run_chat_discovery as shared
        for data in (b'x' * 4097, b'x\n' * 32769):
            with self.subTest(size=len(data)):
                fixture, profile, path, digest, source = self.synthetic_profile()
                class Child:
                    pid = 559
                    alive = True
                    stdout = io.BytesIO(data)
                    def poll(self): return None if self.alive else 0
                    def terminate(self): self.alive = False
                    def wait(self, timeout): return 0
                    def kill(self): self.alive = False
                child = Child()
                transport = types.SimpleNamespace(create_app=lambda *a, **kw: self.fail('unexpected app'))
                output = io.StringIO()
                with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime', return_value=(shared, transport)), patch.object(shared, '_creation_filetime', return_value=123), patch.object(launcher.subprocess, 'Popen', return_value=child), contextlib.redirect_stdout(output):
                    self.assertEqual(launcher.main([str(path), digest]), 1)
                self.assertFalse(child.alive)
                self.assertEqual(output.getvalue(), '')
                receipt = json.loads(Path(profile['receipt_path']).read_text())
                self.assertEqual(receipt['status'], 'error')
                if len(data) == 4097:
                    self.assertEqual(receipt['diagnostic']['reason'], 'guard_rejected')
                    self.assertTrue(receipt['diagnostic']['guard_failed'])
    @unittest.skipUnless(sys.platform == 'win32', 'Windows socket required')
    def test_changed_helper_origin_stops_and_cleans_owner(self):
        import run_chat_discovery as shared
        fixture, profile, path, digest, source = self.synthetic_profile()
        server_started = threading.Event()
        cleaned = []
        class Stream:
            first = io.BytesIO(b'https://first.trycloudflare.com\n')
            second = io.BytesIO(b'https://second.trycloudflare.com\n')
            def read(self, size):
                value = self.first.read(size)
                if value: return value
                server_started.wait(2)
                return self.second.read(size)
        class Child:
            pid = 557
            alive = True
            stdout = Stream()
            def poll(self): return None if self.alive else 0
            def terminate(self): self.alive = False
            def wait(self, timeout): return 0
            def kill(self): self.alive = False
        class Server:
            started = False
            should_exit = False
            def __init__(self, config): pass
            def run(self, sockets):
                self.started = True
                server_started.set()
                while not self.should_exit: time.sleep(.01)
        child = Child()
        app = types.SimpleNamespace(state=types.SimpleNamespace(owner_cleanup=lambda: cleaned.append(True)))
        transport = types.SimpleNamespace(create_app=lambda *a, **kw: app)
        output = io.StringIO()
        with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime', return_value=(shared, transport)), patch.object(shared, '_creation_filetime', return_value=123), patch.object(launcher.subprocess, 'Popen', return_value=child), patch.object(uvicorn, 'Server', Server), contextlib.redirect_stdout(output):
            self.assertEqual(launcher.main([str(path), digest]), 1)
        self.assertTrue(server_started.is_set())
        self.assertFalse(child.alive)
        self.assertTrue(cleaned)
        self.assertLessEqual(len(output.getvalue().splitlines()), 1)
        self.assertNotIn('second.trycloudflare.com', output.getvalue())
        receipt = json.loads(Path(profile['receipt_path']).read_text())
        self.assertEqual(receipt['status'], 'error')
        self.assertEqual(receipt['diagnostic']['reason'], 'guard_rejected')
        self.assertNotIn('trycloudflare.com', json.dumps(receipt['diagnostic']))
    @unittest.skipUnless(sys.platform == 'win32', 'Windows socket required')
    def test_owner_interrupt_cleans_owner_and_child(self):
        import run_chat_discovery as shared
        fixture, profile, path, digest, source = self.synthetic_profile()
        cleaned = []
        class Child:
            pid = 555
            alive = True
            stdout = io.BytesIO(b'https://fake.trycloudflare.com\n')
            def poll(self): return None if self.alive else 0
            def terminate(self): self.alive = False
            def wait(self, timeout): return 0
            def kill(self): self.alive = False
        class Server:
            started = False
            should_exit = False
            def __init__(self, config): pass
            def run(self, sockets):
                self.started = True
                _thread.interrupt_main()
                while not self.should_exit: time.sleep(.01)
        child = Child()
        app = types.SimpleNamespace(state=types.SimpleNamespace(owner_cleanup=lambda: cleaned.append(True)))
        transport = types.SimpleNamespace(create_app=lambda *a, **kw: app)
        with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime', return_value=(shared, transport)), patch.object(shared, '_creation_filetime', return_value=123), patch.object(launcher.subprocess, 'Popen', return_value=child), patch.object(uvicorn, 'Server', Server), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launcher.main([str(path), digest]), 1)
        self.assertFalse(child.alive)
        self.assertTrue(cleaned)
        receipt = json.loads(Path(profile['receipt_path']).read_text())
        self.assertEqual(receipt['status'], 'error')
        self.assertEqual(receipt['diagnostic']['reason'], 'interrupted')

    @unittest.skipUnless(sys.platform == 'win32', 'Windows socket required')
    def test_server_failure_before_ready_cleans_owner_and_child(self):
        import run_chat_discovery as shared
        fixture, profile, path, digest, source = self.synthetic_profile()
        cleaned = []
        class Child:
            pid = 556
            alive = True
            stdout = io.BytesIO(b'https://fake.trycloudflare.com\n')
            def poll(self): return None if self.alive else 0
            def terminate(self): self.alive = False
            def wait(self, timeout): return 0
            def kill(self): self.alive = False
        class Server:
            started = False
            should_exit = False
            def __init__(self, config): pass
            def run(self, sockets): raise RuntimeError('PRIVATE_EXCEPTION_CANARY')
        child, output = Child(), io.StringIO()
        app = types.SimpleNamespace(state=types.SimpleNamespace(owner_cleanup=lambda: cleaned.append(True)))
        transport = types.SimpleNamespace(create_app=lambda *a, **kw: app)
        with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime', return_value=(shared, transport)), patch.object(shared, '_creation_filetime', return_value=123), patch.object(launcher.subprocess, 'Popen', return_value=child), patch.object(uvicorn, 'Server', Server), contextlib.redirect_stdout(output):
            self.assertEqual(launcher.main([str(path), digest]), 1)
        self.assertEqual(output.getvalue(), '')
        self.assertFalse(child.alive)
        self.assertTrue(cleaned)
        self.assertEqual(json.loads(Path(profile['receipt_path']).read_text())['status'], 'error')
    @unittest.skipUnless(sys.platform == 'win32', 'Windows socket required')
    def test_child_hold_reports_identity_before_reap_and_port_release(self):
        import run_chat_discovery as shared
        fixture, profile, path, _, source = self.synthetic_profile()
        profile['lifetime_seconds'] = profile['startup_timeout_seconds'] = 1
        raw = json.dumps(profile).encode()
        path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        hold = Path(profile['intent_path'] + '.hold.json')
        observed = []
        class Child:
            pid = 444
            stdout = io.BytesIO(b'')
            calls = 0
            def poll(self): return None
            def terminate(self): pass
            def kill(self): pass
            def wait(self, timeout):
                self.calls += 1
                if self.calls < 3: raise launcher.subprocess.TimeoutExpired('fake', timeout)
                record = json.loads(hold.read_text())
                record['receipt_exists'] = Path(profile['receipt_path']).exists()
                with socket.socket() as competitor:
                    try:
                        competitor.bind(('127.0.0.1', record['port']))
                        record['blocked'] = False
                    except OSError:
                        record['blocked'] = True
                observed.append(record)
                return 0
        transport = types.SimpleNamespace(create_app=lambda *a, **kw: self.fail('unexpected factory'))
        with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime', return_value=(shared, transport)), patch.object(shared, '_creation_filetime', return_value=456), patch.object(launcher.subprocess, 'Popen', return_value=Child()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(launcher.main([str(path), digest]), 1)
        self.assertEqual(observed[0]['child_pid'], 444)
        self.assertEqual(observed[0]['child_creation_filetime'], 456)
        self.assertTrue(observed[0]['blocked'])
        self.assertFalse(observed[0]['receipt_exists'])
        self.assertLessEqual(hold.stat().st_size, 2048)
    @unittest.skipUnless(sys.platform == 'win32', 'Windows socket required')
    def test_post_factory_startup_failure_cleans_owner_and_redacts(self):
        import run_chat_discovery as shared
        fixture, profile, path, digest, source = self.synthetic_profile()
        cleaned = []
        class Child:
            pid = 222
            alive = True
            stdout = io.BytesIO(b'https://fake.trycloudflare.com\n')
            def poll(self): return None if self.alive else 0
            def terminate(self): self.alive = False
            def wait(self, timeout): return 0
            def kill(self): self.alive = False
        child = Child()
        app = types.SimpleNamespace(state=types.SimpleNamespace(owner_cleanup=lambda: cleaned.append(True)))
        transport = types.SimpleNamespace(create_app=lambda *a, **kw: app)
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime', return_value=(shared, transport)), patch.object(shared, '_creation_filetime', return_value=123), patch.object(launcher.subprocess, 'Popen', return_value=child), patch.object(uvicorn, 'Config', side_effect=ValueError('PRIVATE_EXCEPTION_CANARY')), contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(launcher.main([str(path), digest]), 1)
        self.assertFalse(child.alive)
        self.assertTrue(cleaned)
        self.assertNotIn('PRIVATE_EXCEPTION_CANARY', output.getvalue() + errors.getvalue())
        self.assertNotIn('s' * 43, output.getvalue() + errors.getvalue())
        receipt = Path(profile['receipt_path']).read_text()
        self.assertNotIn('s' * 43, receipt)
        self.assertEqual(json.loads(receipt)['status'], 'error')

    @unittest.skipUnless(sys.platform == 'win32', 'Windows socket required')
    def test_early_owned_child_exit_never_creates_app_or_ready(self):
        import run_chat_discovery as shared
        fixture, profile, path, digest, source = self.synthetic_profile()
        class Child:
            pid = 333
            stdout = io.BytesIO(b'https://fake.trycloudflare.com\n')
            def poll(self): return 1
            def terminate(self): pass
            def wait(self, timeout): return 1
            def kill(self): pass
        transport = types.SimpleNamespace(create_app=lambda *a, **kw: self.fail('app must not start'))
        output = io.StringIO()
        with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime', return_value=(shared, transport)), patch.object(shared, '_creation_filetime', return_value=123), patch.object(launcher.subprocess, 'Popen', return_value=Child()), contextlib.redirect_stdout(output):
            self.assertEqual(launcher.main([str(path), digest]), 1)
        self.assertEqual(output.getvalue(), '')
        self.assertEqual(json.loads(Path(profile['receipt_path']).read_text())['status'], 'error')
    @unittest.skipUnless(sys.platform == 'win32', 'Windows socket required')
    def test_fake_lifecycle_cleans_owner_and_records_synthetic_ready(self):
        import run_chat_discovery as shared
        fixture, profile, path, digest, source = self.synthetic_profile()
        profile['lifetime_seconds'] = 1
        raw = json.dumps(profile).encode()
        path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        cleaned = []
        class Child:
            pid = 111
            alive = True
            stdout = io.BytesIO(b'https://fake.trycloudflare.com\n')
            def poll(self): return None if self.alive else 0
            def terminate(self): self.alive = False
            def wait(self, timeout): return 0
            def kill(self): self.alive = False
        child = Child()
        app = types.SimpleNamespace(state=types.SimpleNamespace(owner_cleanup=lambda: cleaned.append(True)))
        transport = types.SimpleNamespace(create_app=lambda *a, **kw: app)
        class Server:
            started = False
            should_exit = False
            def __init__(self, config): pass
            def run(self, sockets):
                self.started = True
                while not self.should_exit: time.sleep(.01)
        output = io.StringIO()
        with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime', return_value=(shared, transport)), patch.object(shared, '_creation_filetime', return_value=123), patch.object(launcher.subprocess, 'Popen', return_value=child), patch.object(uvicorn, 'Server', Server), contextlib.redirect_stdout(output):
            self.assertEqual(launcher.main([str(path), digest]), 0)
        self.assertFalse(child.alive)
        self.assertTrue(cleaned)
        ready = json.loads(output.getvalue())
        self.assertEqual(ready, {'status': 'synthetic-only', 'origin': 'https://fake.trycloudflare.com',
                                 'mcp_url': 'https://fake.trycloudflare.com/mcp'})
        receipt = json.loads(Path(profile['receipt_path']).read_text())
        self.assertEqual(receipt['cleanup'], 'complete')
        self.assertEqual(receipt['diagnostic']['phase'], 'serving')
        self.assertEqual(receipt['diagnostic']['reason'], 'lifetime_elapsed')
        self.assertTrue(receipt['diagnostic']['recognized_origin'])
        self.assertFalse(receipt['diagnostic']['guard_failed'])
    def synthetic_profile(self):
        fixture = fixtures.ManagedMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.grant.update(client='chatgpt-openai', prefixes=[], note_ids=['decision'])
        denied = fixture.root / 'denied.md'
        denied.write_bytes(b'---\nprivacy: "synthetic"\n---\n\n# Denied\nDENIED_CANARY\n')
        entry = {'id': 'denied', 'path': 'denied.md', 'sha256': hashlib.sha256(denied.read_bytes()).hexdigest(),
                 'size': denied.stat().st_size, 'privacy': 'synthetic', 'external_processing': False,
                 'source_references': ['synthetic://denied']}
        fixture.manifest['notes'].append(entry)
        fixture.publish()
        fixture.pin()
        root = fixture.base
        runtime = root / 'runtime'
        runtime.mkdir()
        scripts = Path(launcher.__file__).parent
        def pin(path):
            data = path.read_bytes()
            return {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        runtime_pins = {}
        for name in launcher.RUNTIME_NAMES:
            target = runtime / name
            target.write_bytes((scripts / name).read_bytes())
            runtime_pins[name] = pin(target)
        helper, config, secret = root / 'fake.exe', root / 'empty.yaml', root / 'owner-code'
        helper.write_bytes(b'fictional')
        config.write_bytes(b'{}\n')
        secret.write_bytes(b's' * 43)
        temp = root / 'temp'
        temp.mkdir()
        def pathpin(path): return {'path': str(path), **pin(path)}
        paths = [fixture.grant_path, fixture.private / '.private-staging.json', fixture.policy_path,
                 fixture.pointer, fixture.managed / 'generation.json', fixture.note, denied]
        profile = {'schema': 'brain-chat-synthetic-launch-v1', 'state': 'approved', 'scope': 'synthetic-only',
                   'owner_reference': 'synthetic', 'additional_spend_usd': 0, 'lifetime_seconds': 3,
                   'startup_timeout_seconds': 2, 'recipients': ['Cloudflare', 'OpenAI', 'Sentry'],
                   'private_root': str(root), 'runtime_dir': str(runtime), 'runtime': runtime_pins,
                   'helper': pathpin(helper), 'config': pathpin(config), 'owner_code': pathpin(secret),
                   'grant': str(fixture.grant_path), 'closure': {str(path): pin(path) for path in paths},
                   'client_id': 'synthetic-client', 'callback': 'https://client.example/callback',
                   'intent_path': str(root / 'intent.json'), 'receipt_path': str(root / 'receipt.json'),
                   'temp_dir': str(temp)}
        path = root / 'profile.json'
        raw = json.dumps(profile).encode()
        path.write_bytes(raw)
        return fixture, profile, path, hashlib.sha256(raw).hexdigest(), runtime / 'run_chat_synthetic.py'

    def test_exact_closure_rejects_consistently_repinned_generation(self):
        fixture, profile, path, digest, source = self.synthetic_profile()
        with patch.object(launcher, '__file__', str(source)):
            loaded = launcher.load_profile(str(path), digest)
            launcher.validate_closure(loaded)
            fixture.manifest['generation'] = 2
            fixture.publish('next.json')
            with self.assertRaises(ValueError):
                launcher.validate_closure(loaded)

    def test_outside_nested_pointer_refused_without_open(self):
        fixture, profile, path, _, source = self.synthetic_profile()
        with tempfile.TemporaryDirectory() as outside:
            outside_path = Path(outside) / 'policy.json'
            outside_path.write_bytes(b'PRIVATE_CANARY')
            fixture.grant['policy_path'] = str(outside_path)
            fixture.pin()
            raw_grant = fixture.grant_path.read_bytes()
            profile['closure'][str(fixture.grant_path)] = {'size': len(raw_grant), 'sha256': hashlib.sha256(raw_grant).hexdigest()}
            raw = json.dumps(profile).encode()
            path.write_bytes(raw)
            original = Path.open
            def trap(candidate, *args, **kwargs):
                if candidate == outside_path: self.fail('outside content opened')
                return original(candidate, *args, **kwargs)
            with patch.object(launcher, '__file__', str(source)), patch.object(Path, 'open', trap):
                with self.assertRaises(ValueError):
                    launcher.load_profile(str(path), hashlib.sha256(raw).hexdigest())

    def test_post_start_nested_redirect_refused_without_open(self):
        fixture, profile, path, digest, source = self.synthetic_profile()
        with tempfile.TemporaryDirectory() as outside, patch.object(launcher, '__file__', str(source)):
            launcher.load_profile(str(path), digest)
            target = Path(outside) / 'external-policy'
            target.write_bytes(b'OUTSIDE_CANARY')
            fixture.grant['policy_path'] = str(target)
            fixture.pin()
            original = Path.open
            def trap(candidate, *args, **kwargs):
                if candidate == target: self.fail('outside content opened')
                return original(candidate, *args, **kwargs)
            with patch.object(Path, 'open', trap), self.assertRaises(ValueError):
                launcher.validate_closure(profile)

    def test_unreferenced_in_root_file_not_opened(self):
        fixture, profile, path, _, source = self.synthetic_profile()
        extra = fixture.base / 'unrelated.txt'
        extra.write_bytes(b'PRIVATE_CANARY')
        profile['closure'][str(extra)] = {'size': extra.stat().st_size, 'sha256': hashlib.sha256(extra.read_bytes()).hexdigest()}
        raw = json.dumps(profile).encode()
        path.write_bytes(raw)
        original = Path.open
        def trap(candidate, *args, **kwargs):
            if candidate == extra: self.fail('unreferenced content opened')
            return original(candidate, *args, **kwargs)
        with patch.object(launcher, '__file__', str(source)), patch.object(Path, 'open', trap), self.assertRaises(ValueError):
            launcher.load_profile(str(path), hashlib.sha256(raw).hexdigest())

    def test_canonical_shaped_grant_refused_before_runtime(self):
        fixture, profile, path, _, source = self.synthetic_profile()
        fixture.grant['source_kind'] = 'canonical'
        fixture.pin()
        raw_grant = fixture.grant_path.read_bytes()
        profile['closure'][str(fixture.grant_path)] = {'size': len(raw_grant), 'sha256': hashlib.sha256(raw_grant).hexdigest()}
        raw = json.dumps(profile).encode()
        path.write_bytes(raw)
        with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime') as load:
            self.assertEqual(launcher.main([str(path), hashlib.sha256(raw).hexdigest()]), 1)
            load.assert_not_called()

    def test_pending_grant_and_disabled_policy_refuse_before_runtime(self):
        for kind in ('grant', 'policy'):
            with self.subTest(kind=kind):
                fixture, profile, path, _, source = self.synthetic_profile()
                if kind == 'grant':
                    fixture.grant['owner_authorization']['state'] = 'pending'
                else:
                    fixture.policy['enabled'] = False
                    fixture.write(fixture.policy_path, fixture.policy)
                    policy_hash = hashlib.sha256(fixture.policy_path.read_bytes()).hexdigest()
                    fixture.grant['policy_sha256'] = policy_hash
                    fixture.manifest['policy_sha256'] = policy_hash
                    fixture.publish()
                fixture.pin()
                for item in (fixture.grant_path, fixture.policy_path, fixture.pointer, fixture.managed / 'generation.json'):
                    content = item.read_bytes()
                    profile['closure'][str(item)] = {'size': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
                raw = json.dumps(profile).encode()
                path.write_bytes(raw)
                with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime') as runtime:
                    self.assertEqual(launcher.main([str(path), hashlib.sha256(raw).hexdigest()]), 1)
                    runtime.assert_not_called()

    def test_invalid_secret_refused_without_output_or_runtime(self):
        fixture, profile, path, _, source = self.synthetic_profile()
        secret = Path(profile['owner_code']['path'])
        raw_secret = b'PRIVATE_SECRET_CANARY!'
        secret.write_bytes(raw_secret)
        profile['owner_code'].update(size=len(raw_secret), sha256=hashlib.sha256(raw_secret).hexdigest())
        raw = json.dumps(profile).encode()
        path.write_bytes(raw)
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(launcher, '__file__', str(source)), patch.object(launcher, '_load_runtime') as load, contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(launcher.main([str(path), hashlib.sha256(raw).hexdigest()]), 1)
            load.assert_not_called()
        self.assertNotIn('PRIVATE_SECRET_CANARY', output.getvalue() + errors.getvalue())

    def test_outside_helper_secret_and_runtime_never_opened(self):
        for kind in ('helper', 'owner_code', 'runtime'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as outside:
                fixture, profile, path, _, source = self.synthetic_profile()
                outer = Path(outside)
                if kind == 'runtime':
                    profile['runtime_dir'] = str(outer)
                    for name in launcher.RUNTIME_NAMES:
                        (outer / name).write_bytes((Path(profile['private_root']) / 'runtime' / name).read_bytes())
                else:
                    target = outer / kind
                    target.write_bytes(Path(profile[kind]['path']).read_bytes())
                    profile[kind]['path'] = str(target)
                raw = json.dumps(profile).encode()
                path.write_bytes(raw)
                original = Path.open
                def trap(candidate, *args, **kwargs):
                    if candidate.is_relative_to(outer): self.fail('outside content opened')
                    return original(candidate, *args, **kwargs)
                with patch.object(launcher, '__file__', str(source)), patch.object(Path, 'open', trap), self.assertRaises(ValueError):
                    launcher.load_profile(str(path), hashlib.sha256(raw).hexdigest())

    def test_reparse_fixture_refused_before_content_open(self):
        fixture, profile, path, digest, source = self.synthetic_profile()
        original_lstat = Path.lstat
        original_open = Path.open
        def synthetic_reparse(candidate):
            info = original_lstat(candidate)
            if candidate == fixture.note:
                return types.SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400, st_nlink=info.st_nlink)
            return info
        def trap(candidate, *args, **kwargs):
            if candidate == fixture.note: self.fail('redirected content opened')
            return original_open(candidate, *args, **kwargs)
        with patch.object(launcher, '__file__', str(source)), patch.object(Path, 'lstat', synthetic_reparse), patch.object(Path, 'open', trap), self.assertRaises(ValueError):
            launcher.load_profile(str(path), digest)

    def test_noncanonical_nested_manifest_name_refused(self):
        for value in ('../outside.json', '.Obsidian/outside.json', 'generation.json ', 'folder//file.json'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    launcher._relative(value)

    def test_oversized_fixture_refused_before_note_open(self):
        fixture, profile, path, _, source = self.synthetic_profile()
        fixture.note.write_bytes(b'x' * 128001)
        fixture.manifest['notes'][0] = fixture.entry()
        fixture.publish()
        for item in (fixture.note, fixture.pointer, fixture.managed / 'generation.json'):
            data = item.read_bytes()
            profile['closure'][str(item)] = {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        raw = json.dumps(profile).encode()
        path.write_bytes(raw)
        original = Path.open
        def trap(candidate, *args, **kwargs):
            if candidate == fixture.note: self.fail('oversized note opened')
            return original(candidate, *args, **kwargs)
        with patch.object(launcher, '__file__', str(source)), patch.object(Path, 'open', trap), self.assertRaises(ValueError):
            launcher.load_profile(str(path), hashlib.sha256(raw).hexdigest())

    def test_guard_blocks_result_after_reader_changes_pointer(self):
        import chat_recall_http as transport
        fixture, profile, path, digest, source = self.synthetic_profile()
        servers = []
        original_server = transport._RedactedServer
        def capture_server(*args, **kwargs):
            server = original_server(*args, **kwargs)
            servers.append(server)
            return server
        def drift_reader(*args):
            fixture.manifest['generation'] = 2
            fixture.publish('later.json')
            return {'result': 'PRIVATE_RESULT_CANARY'}
        async def exercise():
            with patch.object(launcher, '__file__', str(source)), patch.object(transport, '_RedactedServer', side_effect=capture_server), patch.object(transport, 'search_managed', side_effect=drift_reader):
                launcher.load_profile(str(path), digest)
                app = transport.create_app(str(fixture.grant_path), profile['closure'][str(fixture.grant_path)]['sha256'],
                    'chatgpt-openai', 'https://fake.trycloudflare.com', 'synthetic-client',
                    'https://client.example/callback', 's' * 43, operation_guard=lambda: launcher.validate_closure(profile))
                try:
                    with self.assertRaises(transport.ToolError) as caught:
                        await servers[0].call_tool('search_managed_memory', {'query': 'amber'})
                    self.assertEqual(str(caught.exception), 'MANAGED_RECALL_REFUSED')
                    self.assertNotIn('PRIVATE_RESULT_CANARY', str(caught.exception))
                finally:
                    app.state.owner_cleanup()
        asyncio.run(exercise())

    def test_guard_refuses_drift_before_reader_is_called(self):
        import chat_recall_http as transport
        fixture, profile, path, digest, source = self.synthetic_profile()
        servers = []
        original_server = transport._RedactedServer
        def capture_server(*args, **kwargs):
            server = original_server(*args, **kwargs)
            servers.append(server)
            return server
        async def exercise():
            with patch.object(launcher, '__file__', str(source)), patch.object(transport, '_RedactedServer', side_effect=capture_server), patch.object(transport, 'search_managed') as reader:
                launcher.load_profile(str(path), digest)
                app = transport.create_app(str(fixture.grant_path), profile['closure'][str(fixture.grant_path)]['sha256'],
                    'chatgpt-openai', 'https://fake.trycloudflare.com', 'synthetic-client',
                    'https://client.example/callback', 's' * 43, operation_guard=lambda: launcher.validate_closure(profile))
                try:
                    fixture.manifest['generation'] = 2
                    fixture.publish('later.json')
                    with self.assertRaises(transport.ToolError) as caught:
                        await servers[0].call_tool('search_managed_memory', {'query': 'amber'})
                    self.assertEqual(str(caught.exception), 'MANAGED_RECALL_REFUSED')
                    reader.assert_not_called()
                finally:
                    app.state.owner_cleanup()
        asyncio.run(exercise())
    def test_pending_profile_refuses_before_listener_or_child(self):
        with tempfile.TemporaryDirectory() as root:
            raw = b'{"state":"pending"}'
            path = Path(root) / 'profile.json'
            path.write_bytes(raw)
            with patch.object(launcher, 'open_exclusive_listener') as listener, patch.object(launcher.subprocess, 'Popen') as child:
                self.assertEqual(launcher.main([str(path), hashlib.sha256(raw).hexdigest()]), 1)
                listener.assert_not_called()
                child.assert_not_called()

    def test_duplicate_profile_keys_refused(self):
        with tempfile.TemporaryDirectory() as root:
            raw = b'{"state":"approved","state":"approved"}'
            path = Path(root) / 'profile.json'
            path.write_bytes(raw)
            with self.assertRaises(ValueError):
                launcher.load_profile(str(path), hashlib.sha256(raw).hexdigest())


if __name__ == '__main__':
    unittest.main()
