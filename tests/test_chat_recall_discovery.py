"""Discovery-only helper tests: direct ASGI, no listener or real content."""
import ast
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from chat_recall_discovery import create_app, main


class DiscoveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.origin = 'https://example-42.trycloudflare.com'
        self.app = create_app(self.origin, 8765)

    async def request(self, path, method='GET', headers=None, query=b'', raw_path=None, body=b''):
        output, reads = [], []
        scope = {'type': 'http', 'method': method, 'path': path,
                 'raw_path': path.encode() if raw_path is None else raw_path,
                 'query_string': query, 'headers': headers if headers is not None else
                 [(b'host', b'example-42.trycloudflare.com')]}
        async def receive():
            reads.append(True)
            return {'type': 'http.request', 'body': body, 'more_body': False}
        async def send(message):
            output.append(message)
        await self.app(scope, receive, send)
        start = next(x for x in output if x['type'] == 'http.response.start')
        data = b''.join(x.get('body', b'') for x in output if x['type'] == 'http.response.body')
        self.assertEqual(reads, [])
        headers = dict(start['headers'])
        self.assertEqual(headers[b'cache-control'], b'no-store')
        self.assertEqual(headers[b'referrer-policy'], b'no-referrer')
        self.assertEqual(headers[b'x-content-type-options'], b'nosniff')
        self.assertIn(b"frame-ancestors 'none'", headers[b'content-security-policy'])
        return start['status'], headers, data

    async def test_exact_discovery_metadata(self):
        status, _, raw = await self.request('/.well-known/oauth-protected-resource/mcp')
        self.assertEqual(status, 200)
        value = json.loads(raw)
        self.assertEqual(value['resource'], self.origin + '/mcp')
        self.assertEqual(value['authorization_servers'], [self.origin])
        self.assertEqual(value['scopes_supported'], ['memory:read'])
        self.assertIn('discovery-only', str(value).lower())
        status, _, raw = await self.request('/.well-known/oauth-authorization-server')
        self.assertEqual(status, 200)
        value = json.loads(raw)
        self.assertEqual(value['issuer'], self.origin)
        self.assertEqual(value['authorization_endpoint'], self.origin + '/authorize')
        self.assertEqual(value['token_endpoint'], self.origin + '/token')
        self.assertEqual(value['grant_types_supported'], ['authorization_code'])
        self.assertEqual(value['response_types_supported'], ['code'])
        self.assertEqual(value['token_endpoint_auth_methods_supported'], ['none'])
        self.assertEqual(value['code_challenge_methods_supported'], ['S256'])
        self.assertNotIn('registration_endpoint', value)
        self.assertNotIn('authorization_response_iss_parameter_supported', value)

    async def test_mcp_always_unauthorized_including_head_and_fake_bearer(self):
        for method in ('GET', 'POST', 'DELETE', 'HEAD', 'OPTIONS'):
            with self.subTest(method=method):
                status, headers, data = await self.request('/mcp', method, [
                    (b'host', b'example-42.trycloudflare.com'),
                    (b'authorization', b'Bearer PRIVATE_TOKEN_CANARY')])
                self.assertEqual(status, 401)
                self.assertIn((self.origin + '/.well-known/oauth-protected-resource/mcp').encode(),
                              headers[b'www-authenticate'])
                self.assertNotIn(b'PRIVATE_TOKEN_CANARY', data)
                if method == 'HEAD':
                    self.assertEqual(data, b'')

    async def test_other_methods_and_routes_refuse_without_reflection(self):
        for path, method in [('/authorize', 'GET'), ('/token', 'POST'), ('/consent', 'POST'),
                             ('/unknown', 'POST'), ('/.well-known/oauth-authorization-server', 'POST'),
                             ('/.well-known/oauth-authorization-server', 'HEAD')]:
            with self.subTest(path=path, method=method):
                status, headers, data = await self.request(path, method, query=b'PRIVATE_QUERY_CANARY')
                self.assertGreaterEqual(status, 400)
                self.assertNotIn(b'location', headers)
                self.assertNotIn(b'set-cookie', headers)
                self.assertNotIn(b'PRIVATE_QUERY_CANARY', data)
                if method == 'HEAD':
                    self.assertEqual(data, b'')

    async def test_mcp_messages_and_large_bodies_are_never_read(self):
        for method in ('initialize', 'tools/list', 'tools/call'):
            payload = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method,
                                  'params': {'arguments': {'query': 'PRIVATE_BODY_CANARY'}}}).encode()
            status, headers, data = await self.request('/mcp', 'POST', [
                (b'host', b'example-42.trycloudflare.com'), (b'authorization', b'Bearer PRIVATE_TOKEN_CANARY'),
                (b'content-type', b'application/json')], body=payload)
            self.assertEqual(status, 401)
            self.assertNotIn(b'PRIVATE_BODY_CANARY', data)
            self.assertNotIn(b'PRIVATE_TOKEN_CANARY', data)
            self.assertNotIn(b'location', headers)
        for path in ('/mcp', '/authorize', '/token', '/consent'):
            status, _, data = await self.request(path, 'POST', body=b'PRIVATE_BODY_CANARY' * 10000)
            self.assertGreaterEqual(status, 400)
            self.assertNotIn(b'PRIVATE_BODY_CANARY', data)

    async def test_host_origin_and_size_boundaries(self):
        good = b'example-42.trycloudflare.com'
        for headers in ([(b'host', b'PRIVATE_HOST_CANARY')], [(b'host', good), (b'host', good)],
                        [(b'host', good), (b'origin', b'https://other.example')],
                        [(b'host', good), (b'origin', self.origin.encode()), (b'origin', self.origin.encode())],
                        [(b'host', good)] + [(b'x', b'y')] * 64,
                        [(b'host', good), (b'x', b'z' * 16384)]):
            with self.subTest(count=len(headers)):
                status, _, data = await self.request('/mcp', headers=headers)
                self.assertEqual(status, 400)
                self.assertNotIn(b'PRIVATE_HOST_CANARY', data)
        for path in ('/.well-known/oauth-protected-resource/mcp', '/.well-known/oauth-authorization-server'):
            for headers in ([(b'host', b'PRIVATE_HOST_CANARY')],
                            [(b'host', good), (b'origin', b'https://PRIVATE_ORIGIN_CANARY')]):
                with self.subTest(path=path, headers=headers):
                    status, response_headers, data = await self.request(path, headers=headers)
                    self.assertEqual(status, 400)
                    self.assertNotIn(b'location', response_headers)
                    self.assertNotIn(b'PRIVATE_HOST_CANARY', data)
                    self.assertNotIn(b'PRIVATE_ORIGIN_CANARY', data)
        for path, query in [('/' + 'x' * 2048, b''), ('/mcp', b'x' * 4097)]:
            status, _, _ = await self.request(path, query=query)
            self.assertGreaterEqual(status, 400)
        status, _, _ = await self.request('/mcp', query=b'x' * 4096)
        self.assertEqual(status, 401)
        status, _, _ = await self.request('/mcp', headers=[(b'host', b'127.0.0.1:8765')])
        self.assertEqual(status, 401)
        status, _, _ = await self.request('/mcp', headers=[(b'host', b'localhost:8765'), (b'origin', self.origin.encode())])
        self.assertEqual(status, 401)
        status, _, _ = await self.request('/mcp', raw_path=b'/%6dcp')
        self.assertEqual(status, 400)

    def test_configuration_and_cli_are_strict(self):
        for origin in ('http://example.trycloudflare.com', 'https://example.trycloudflare.com/',
                       'https://a.b.trycloudflare.com', 'https://-bad.trycloudflare.com',
                       'https://example.trycloudflare.com:443', 'https://*.trycloudflare.com'):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                create_app(origin, 8765)
        for port in (True, 0, 65536, '8765'):
            with self.subTest(port=port), self.assertRaises(ValueError):
                create_app(self.origin, port)
        for outcome in ('normal', 'config', 'run', 'exit', 'interrupt'):
            with self.subTest(outcome=outcome), patch('uvicorn.Config') as config, patch('uvicorn.Server') as server:
                if outcome == 'config':
                    config.side_effect = RuntimeError('PRIVATE_ERROR_CANARY')
                if outcome == 'run':
                    server.return_value.run.side_effect = RuntimeError('PRIVATE_ERROR_CANARY')
                if outcome == 'exit':
                    server.return_value.run.side_effect = SystemExit('PRIVATE_ERROR_CANARY')
                if outcome == 'interrupt':
                    server.return_value.run.side_effect = KeyboardInterrupt()
                output = io.StringIO()
                with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                    result = main(['--origin', self.origin, '--port', '8765'])
                self.assertEqual(result, 0 if outcome == 'normal' else 1)
                self.assertNotIn('PRIVATE_ERROR_CANARY', output.getvalue())
                self.assertEqual(config.call_args.kwargs['host'], '127.0.0.1')
                self.assertFalse(config.call_args.kwargs['access_log'])
                self.assertFalse(config.call_args.kwargs['proxy_headers'])

    def test_no_data_loader_imports(self):
        source = (Path(__file__).resolve().parents[1] / 'scripts/chat_recall_discovery.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        modules = [node.module or '' for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        modules += [name.name for node in ast.walk(tree) if isinstance(node, ast.Import) for name in node.names]
        self.assertFalse(any(any(word in name for word in ('managed_memory', 'publish_', 'selected_memory'))
                             for name in modules))


if __name__ == '__main__':
    unittest.main()
