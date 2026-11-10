"""Synthetic ASGI-only tests for the proposed Chat recall transport."""
import asyncio
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest
from urllib.parse import parse_qs, urlencode, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from chat_recall_http import BoundedBody, create_app, main
from chat_recall_oauth import OwnerOAuth
from mcp.server.auth.provider import AuthorizationParams, TokenError
import test_managed_memory as fixtures


class BodyBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, chunks, headers=(), maximum=8):
        calls, output = [], []
        async def app(scope, receive, send):
            calls.append(True)
            message = await receive()
            calls.append(message.get('body', b''))
            await send({'type': 'http.response.start', 'status': 200, 'headers': []})
            await send({'type': 'http.response.body', 'body': b'ok'})
        events = iter([{'type': 'http.request', 'body': chunk, 'more_body': i < len(chunks) - 1}
                       for i, chunk in enumerate(chunks)])
        async def receive():
            return next(events)
        async def send(message):
            output.append(message)
        await BoundedBody(app, maximum)({'type': 'http', 'method': 'POST', 'headers': list(headers)}, receive, send)
        return calls, output

    async def test_chunked_body_limit_is_enforced_without_content_length(self):
        calls, output = await self.request([b'12345', b'6789'])
        self.assertEqual(calls, [])
        self.assertEqual(output[0]['status'], 413)

    async def test_misleading_content_length_does_not_bypass_limit(self):
        calls, output = await self.request([b'12345', b'6789'], [(b'content-length', b'1')])
        self.assertEqual(calls, [])
        self.assertEqual(output[0]['status'], 413)

    async def test_small_chunked_body_reaches_handler(self):
        calls, output = await self.request([b'12', b'34'])
        self.assertEqual(calls, [True, b'1234'])
        self.assertEqual(output[0]['status'], 200)

    async def test_disconnect_before_complete_body_never_calls_handler(self):
        called, output = [], []
        events = iter([{'type': 'http.request', 'body': b'partial', 'more_body': True},
                       {'type': 'http.disconnect'}])
        async def app(scope, receive, send):
            called.append(True)
        async def receive():
            return next(events)
        async def send(value):
            output.append(value)
        await BoundedBody(app)({'type': 'http'}, receive, send)
        self.assertEqual(called, [])
        self.assertEqual(output, [])


class OAuthStateTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.owner = OwnerOAuth('https://bridge.example', 'synthetic-client',
                                'https://client.example/callback', 's' * 43)
        self.params = AuthorizationParams(state='state', scopes=['memory:read'], code_challenge='a' * 43,
                                           redirect_uri='https://client.example/callback',
                                           redirect_uri_provided_explicitly=True,
                                           resource='https://bridge.example/mcp')

    async def test_consent_ticket_and_code_are_single_use(self):
        client = await self.owner.get_client('synthetic-client')
        url = await self.owner.authorize(client, self.params)
        ticket = url.rsplit('=', 1)[-1]
        csrf = self.owner.consent_csrf(ticket)
        issued = self.owner.consent(ticket, csrf, csrf, 's' * 43)
        self.assertIsNotNone(issued)
        code, _ = issued
        self.assertIsNone(self.owner.consent(ticket, csrf, csrf, 's' * 43))
        record = await self.owner.load_authorization_code(client, code)
        results = await asyncio.gather(self.owner.exchange_authorization_code(client, record),
                                       self.owner.exchange_authorization_code(client, record), return_exceptions=True)
        self.assertEqual(sum(isinstance(x, TokenError) for x in results), 1)

    async def test_wrong_secret_and_csrf_never_issue_code(self):
        client = await self.owner.get_client('synthetic-client')
        ticket = (await self.owner.authorize(client, self.params)).rsplit('=', 1)[-1]
        csrf = self.owner.consent_csrf(ticket)
        self.assertIsNone(self.owner.consent(ticket, csrf, csrf, 'bad'))
        self.assertIsNone(self.owner.consent(ticket, csrf, 'bad', 's' * 43))

    async def test_concurrent_consent_only_one_issues(self):
        client = await self.owner.get_client('synthetic-client')
        ticket = (await self.owner.authorize(client, self.params)).rsplit('=', 1)[-1]
        csrf = self.owner.consent_csrf(ticket)
        results = await asyncio.gather(*(asyncio.to_thread(self.owner.consent, ticket, csrf, csrf, 's' * 43)
                                         for _ in range(2)))
        self.assertEqual(sum(value is not None for value in results), 1)

    async def test_expired_ticket_and_token_refuse(self):
        from unittest.mock import patch
        client = await self.owner.get_client('synthetic-client')
        with patch('chat_recall_oauth.time.time', return_value=1000):
            ticket = (await self.owner.authorize(client, self.params)).rsplit('=', 1)[-1]
            csrf = self.owner.consent_csrf(ticket)
        with patch('chat_recall_oauth.time.time', return_value=1121):
            self.assertIsNone(self.owner.consent(ticket, csrf, csrf, 's' * 43))

    async def test_shutdown_clears_issued_token_and_disables_new_auth(self):
        client = await self.owner.get_client('synthetic-client')
        ticket = (await self.owner.authorize(client, self.params)).rsplit('=', 1)[-1]
        csrf = self.owner.consent_csrf(ticket)
        code, _ = self.owner.consent(ticket, csrf, csrf, 's' * 43)
        record = await self.owner.load_authorization_code(client, code)
        token = await self.owner.exchange_authorization_code(client, record)
        self.owner.close()
        self.assertIsNone(await self.owner.load_access_token(token.access_token))
        self.assertIsNone(await self.owner.get_client('synthetic-client'))


class EndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_factory_setup_failure_closes_allocated_owner(self):
        from unittest.mock import patch
        fixture = fixtures.ManagedMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        for failure in (RuntimeError('PRIVATE_SETUP_CANARY'), KeyboardInterrupt(), SystemExit()):
            with self.subTest(failure=type(failure).__name__):
                owner = OwnerOAuth('https://bridge.example', 'synthetic-client',
                                   'https://client.example/callback', 's' * 43)
                client = await owner.get_client('synthetic-client')
                params = AuthorizationParams(state='state', scopes=['memory:read'], code_challenge='a' * 43,
                    redirect_uri='https://client.example/callback', redirect_uri_provided_explicitly=True,
                    resource='https://bridge.example/mcp')
                ticket = (await owner.authorize(client, params)).split('ticket=')[1]
                csrf = owner.consent_csrf(ticket)
                code, _ = owner.consent(ticket, csrf, csrf, 's' * 43)
                token = await owner.exchange_authorization_code(client, await owner.load_authorization_code(client, code))
                extra_ticket = (await owner.authorize(client, params)).split('ticket=')[1]
                with patch('chat_recall_http.OwnerOAuth', return_value=owner), patch('chat_recall_http.AuthSettings', side_effect=failure):
                    expected = ValueError if isinstance(failure, Exception) else type(failure)
                    with self.assertRaises(expected):
                        create_app(fixture.args[0], fixture.args[1], fixture.args[2], 'https://bridge.example',
                                   'synthetic-client', 'https://client.example/callback', 's' * 43)
                self.assertTrue(owner._closed)
                self.assertIsNone(await owner.load_access_token(token.access_token))
                self.assertIsNone(owner.consent_csrf(extra_ticket))
                owner.close()
                self.assertEqual(owner._tokens, {})

    async def test_guard_brackets_each_reader_and_redacts_refusal(self):
        from unittest.mock import patch
        import chat_recall_http as transport
        fixture = fixtures.ManagedMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        baseline_servers = []
        server_type = transport._RedactedServer
        def make_baseline(*a, **kw):
            server = server_type(*a, **kw)
            baseline_servers.append(server)
            return server
        with patch('chat_recall_http._RedactedServer', side_effect=make_baseline):
            baseline_app = create_app(fixture.args[0], fixture.args[1], fixture.args[2], 'https://bridge.example',
                                      'synthetic-client', 'https://client.example/callback', 's' * 43)
        baseline = [tool.model_dump() for tool in await baseline_servers[0].list_tools()]
        baseline_app.state.owner_cleanup()
        for name, args, reader_name in [('search_managed_memory', {'query': 'amber'}, 'search_managed'),
                                         ('read_managed_memory', {'note_id': 'decision'}, 'read_managed'),
                                         ('search', {'query': 'amber'}, 'search_managed'),
                                         ('fetch', {'id': 'decision'}, 'read_managed')]:
            for fail_at in (0, 1, 2):
                with self.subTest(tool=name, fail_at=fail_at):
                    calls, servers = [], []
                    def guard():
                        calls.append('guard')
                        if len([x for x in calls if x == 'guard']) == fail_at:
                            raise ValueError('PRIVATE_GUARD_CANARY')
                    def reader(*unused):
                        calls.append('reader')
                        return {'text': 'PRIVATE_RESULT_CANARY'}
                    server_type = transport._RedactedServer
                    def make_server(*a, **kw):
                        server = server_type(*a, **kw)
                        servers.append(server)
                        return server
                    with patch('chat_recall_http._RedactedServer', side_effect=make_server), patch('chat_recall_http.' + reader_name, side_effect=reader):
                        app = create_app(fixture.args[0], fixture.args[1], fixture.args[2], 'https://bridge.example',
                                         'synthetic-client', 'https://client.example/callback', 's' * 43,
                                         operation_guard=guard)
                        self.assertEqual([tool.model_dump() for tool in await servers[0].list_tools()], baseline)
                        if fail_at:
                            with self.assertRaises(transport.ToolError) as caught:
                                await servers[0].call_tool(name, args)
                            result = caught.exception
                        else:
                            result = await servers[0].call_tool(name, args)
                        app.state.owner_cleanup()
                    self.assertEqual(calls, ['guard'] if fail_at == 1 else ['guard', 'reader', 'guard'])
                    rendered = str(result)
                    if fail_at:
                        self.assertIn('MANAGED_RECALL_REFUSED', rendered)
                        self.assertNotIn('PRIVATE_GUARD_CANARY', rendered)
                        self.assertNotIn('PRIVATE_RESULT_CANARY', rendered)
                    else:
                        self.assertIn('PRIVATE_RESULT_CANARY', rendered)

    async def test_guard_false_and_async_result_refuse_before_reader(self):
        from unittest.mock import patch
        import chat_recall_http as transport
        fixture = fixtures.ManagedMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        async def async_guard(): return True
        for guard in (lambda: False, async_guard):
            servers = []
            original = transport._RedactedServer
            def create_server(*args, **kwargs):
                server = original(*args, **kwargs)
                servers.append(server)
                return server
            with patch('chat_recall_http._RedactedServer', side_effect=create_server), patch('chat_recall_http.search_managed') as reader:
                app = create_app(fixture.args[0], fixture.args[1], fixture.args[2], 'https://bridge.example',
                                 'synthetic-client', 'https://client.example/callback', 's' * 43,
                                 operation_guard=guard)
                with self.assertRaises(transport.ToolError) as caught:
                    await servers[0].call_tool('search_managed_memory', {'query': 'amber'})
                self.assertEqual(str(caught.exception), 'MANAGED_RECALL_REFUSED')
                reader.assert_not_called()
                app.state.owner_cleanup()
    async def request(self, app, path, method='GET', body=b'', headers=(), query=b'', host=b'bridge.example', chunks=None):
        output, used = [], 0
        chunks = chunks if chunks is not None else [body]
        scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1',
                 'scheme': 'https', 'method': method, 'path': path, 'raw_path': path.encode(),
                 'query_string': query, 'root_path': '', 'server': ('bridge.example', 443),
                 'client': ('127.0.0.1', 10000), 'headers': [(b'host', host), *headers]}
        async def receive():
            nonlocal used
            if used < len(chunks):
                chunk = chunks[used]
                used += 1
                return {'type': 'http.request', 'body': chunk, 'more_body': used < len(chunks)}
            await asyncio.Event().wait()
        async def send(message):
            output.append(message)
        await app(scope, receive, send)
        start = next(m for m in output if m['type'] == 'http.response.start')
        data = b''.join(m.get('body', b'') for m in output if m['type'] == 'http.response.body')
        return start['status'], dict(start['headers']), data

    async def test_discovery_and_unauthenticated_mcp(self):
        fixture = fixtures.ManagedMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        app = create_app(fixture.args[0], fixture.args[1], fixture.args[2], 'https://bridge.example',
                         'synthetic-client', 'https://client.example/callback', 's' * 43)
        async with app.router.lifespan_context(app):
            status, _, data = await self.request(app, '/.well-known/oauth-authorization-server')
            self.assertEqual(status, 200)
            metadata = json.loads(data)
            self.assertEqual(metadata['grant_types_supported'], ['authorization_code'])
            self.assertEqual(metadata['token_endpoint_auth_methods_supported'], ['none'])
            self.assertEqual(metadata['code_challenge_methods_supported'], ['S256'])
            self.assertNotIn('registration_endpoint', metadata)
            status, _, data = await self.request(app, '/.well-known/oauth-protected-resource/mcp')
            self.assertEqual(status, 200)
            protected = json.loads(data)
            self.assertEqual(protected['resource'], 'https://bridge.example/mcp')
            self.assertEqual(protected['authorization_servers'], ['https://bridge.example'])
            self.assertEqual(protected['scopes_supported'], ['memory:read'])
            status, _, _ = await self.request(app, '/register', 'POST', b'{}')
            self.assertEqual(status, 404)
            status, _, _ = await self.request(app, '/mcp', 'POST', b'{"jsonrpc":"2.0","id":1,"method":"tools/list"}',
                                              [(b'content-type', b'application/json'),
                                               (b'accept', b'application/json, text/event-stream')])
            self.assertEqual(status, 401)

    async def test_full_oauth_and_synthetic_mcp_read(self):
        fixture = fixtures.ManagedMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.note.write_bytes(fixture.note.read_bytes() + (b'x' * 500 + b'\n') * 25)
        denied = fixture.root / 'other/denied.md'
        denied.parent.mkdir()
        denied.write_bytes(b'---\nprivacy: "synthetic"\n---\n# Denied\nDENIED_CONTENT_CANARY\n')
        denied_entry = {'id': 'denied', 'path': 'other/denied.md',
                        'sha256': hashlib.sha256(denied.read_bytes()).hexdigest(), 'size': denied.stat().st_size,
                        'privacy': 'synthetic', 'external_processing': False,
                        'source_references': ['DENIED_REFERENCE_CANARY']}
        fixture.manifest['notes'] = [fixture.entry(), denied_entry]
        fixture.publish()
        guard_state = {'calls': 0, 'fail_at': 0}
        def guard():
            guard_state['calls'] += 1
            if guard_state['calls'] == guard_state['fail_at']:
                raise ValueError('PRIVATE_GUARD_CANARY')
        app = create_app(fixture.args[0], fixture.args[1], fixture.args[2], 'https://bridge.example',
                         'synthetic-client', 'https://client.example/callback', 's' * 43, operation_guard=guard)
        verifier = 'v' * 43
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        query = urlencode({'client_id': 'synthetic-client', 'redirect_uri': 'https://client.example/callback',
                           'response_type': 'code', 'scope': 'memory:read', 'state': 'synthetic-state',
                           'code_challenge': challenge, 'code_challenge_method': 'S256',
                           'resource': 'https://bridge.example/mcp'}).encode()
        before = {p: p.read_bytes() for p in fixture.base.rglob('*') if p.is_file()}
        async with app.router.lifespan_context(app):
            status, headers, _ = await self.request(app, '/authorize', query=query)
            self.assertEqual(status, 302)
            consent_url = urlsplit(headers[b'location'].decode())
            self.assertNotIn('iss', parse_qs(consent_url.query))
            status, headers, page = await self.request(app, '/consent', query=consent_url.query.encode())
            self.assertEqual(status, 200)
            self.assertEqual(headers[b'referrer-policy'], b'no-referrer')
            self.assertEqual(headers[b'cache-control'], b'no-store')
            self.assertIn(b"frame-ancestors 'none'", headers[b'content-security-policy'])
            ticket = re.search(rb'name="ticket" value="([^"]+)"', page).group(1).decode()
            csrf = re.search(rb'name="csrf" value="([^"]+)"', page).group(1).decode()
            form = urlencode({'ticket': ticket, 'csrf': csrf, 'owner_code': 's' * 43}).encode()
            status, _, _ = await self.request(app, '/consent', 'POST', form,
                [(b'content-type', b'application/x-www-form-urlencoded'), (b'cookie', ('brain_csrf=' + csrf).encode())])
            self.assertEqual(status, 403)
            wrong_form = urlencode({'ticket': ticket, 'csrf': csrf, 'owner_code': 'PRIVATE_SECRET_CANARY'}).encode()
            status, _, denial = await self.request(app, '/consent', 'POST', wrong_form,
                [(b'origin', b'https://bridge.example'), (b'content-type', b'application/x-www-form-urlencoded'),
                 (b'cookie', ('brain_csrf=' + csrf).encode())])
            self.assertEqual(status, 403)
            self.assertNotIn(b'PRIVATE_SECRET_CANARY', denial)
            status, _, _ = await self.request(app, '/consent', 'POST', form,
                [(b'origin', b'https://bridge.example'), (b'content-type', b'application/x-www-form-urlencoded'),
                 (b'cookie', b'brain_csrf=wrong')])
            self.assertEqual(status, 403)
            consent_headers = [(b'origin', b'https://bridge.example'),
                               (b'content-type', b'application/x-www-form-urlencoded'),
                               (b'cookie', ('brain_csrf=' + csrf).encode())]
            consent_results = await asyncio.gather(*(self.request(app, '/consent', 'POST', form, consent_headers)
                                                     for _ in range(2)))
            self.assertEqual(sum(status == 303 for status, _, _ in consent_results), 1)
            headers = next(headers for status, headers, _ in consent_results if status == 303)
            callback_query = parse_qs(urlsplit(headers[b'location'].decode()).query)
            self.assertEqual(callback_query.get('iss'), ['https://bridge.example'])
            self.assertEqual(callback_query.get('state'), ['synthetic-state'])
            _, auth_headers2, _ = await self.request(app, '/authorize', query=query)
            _, _, page2 = await self.request(app, '/consent', query=urlsplit(auth_headers2[b'location'].decode()).query.encode())
            ticket2 = re.search(rb'name="ticket" value="([^"]+)"', page2).group(1).decode()
            csrf2 = re.search(rb'name="csrf" value="([^"]+)"', page2).group(1).decode()
            form2 = urlencode({'ticket': ticket2, 'csrf': csrf2, 'owner_code': '  ' + 's' * 43 + '\n'}).encode()
            no_cookie_headers = [(b'origin', b'https://bridge.example'), (b'content-type', b'application/x-www-form-urlencoded')]
            status2, headers2, _ = await self.request(app, '/consent', 'POST', form2, no_cookie_headers)
            self.assertEqual(status2, 303)
            self.assertIn(b'location', headers2)
            code = callback_query['code'][0]
            token_form = urlencode({'grant_type': 'authorization_code', 'client_id': 'synthetic-client',
                                    'redirect_uri': 'https://client.example/callback', 'code': code,
                                    'code_verifier': verifier, 'resource': 'https://bridge.example/mcp'}).encode()
            bad_token_form = token_form.replace(b'code_verifier=' + verifier.encode(), b'code_verifier=' + b'w' * 43)
            status, _, _ = await self.request(app, '/token', 'POST', bad_token_form,
                                              [(b'content-type', b'application/x-www-form-urlencoded')])
            self.assertNotEqual(status, 200)
            for bad_form in (token_form + b'&client_id=synthetic-client',
                             token_form.replace(b'synthetic-client', b'other-client'),
                             token_form.replace(b'bridge.example', b'other.example'),
                             token_form.replace(b'client.example', b'other.example')):
                status, _, _ = await self.request(app, '/token', 'POST', bad_form,
                                                  [(b'content-type', b'application/x-www-form-urlencoded')])
                self.assertEqual(status, 400)
            token_results = await asyncio.gather(*(self.request(app, '/token', 'POST', token_form,
                [(b'content-type', b'application/x-www-form-urlencoded')]) for _ in range(2)))
            self.assertEqual(sum(status == 200 for status, _, _ in token_results), 1)
            body = next(body for status, _, body in token_results if status == 200)
            token = json.loads(body)['access_token']
            mcp_headers = [(b'authorization', ('Bearer ' + token).encode()),
                           (b'content-type', b'application/json'),
                           (b'accept', b'application/json, text/event-stream'),
                           (b'mcp-protocol-version', b'2025-03-26')]
            status, _, _ = await asyncio.wait_for(self.request(app, '/mcp', 'GET', headers=mcp_headers), timeout=2)
            self.assertIn(status, (404, 405))
            # Search-first is caller guidance, not an additional per-token authorization cache.
            direct = {'jsonrpc': '2.0', 'id': 9, 'method': 'tools/call',
                      'params': {'name': 'read_managed_memory',
                                 'arguments': {'note_id': 'decision', 'start_line': 7, 'line_count': 1}}}
            status, _, data = await self.request(app, '/mcp', 'POST', json.dumps(direct).encode(), mcp_headers)
            self.assertEqual(status, 200)
            self.assertIn('amber-kite', data.decode())
            call = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                    'params': {'name': 'search_managed_memory', 'arguments': {'query': 'amber'}}}
            status, _, data = await self.request(app, '/mcp', 'POST', json.dumps(call).encode(), mcp_headers)
            self.assertEqual(status, 200)
            self.assertIn('decision', data.decode())
            self.assertIn('synthetic://fixture/source', data.decode())
            self.assertIn(fixture.entry()['sha256'], data.decode())
            for request in (call, direct):
                for position in (1, 2):
                    guard_state.update(calls=0, fail_at=position)
                    status, _, data = await self.request(app, '/mcp', 'POST', json.dumps(request).encode(), mcp_headers)
                    self.assertEqual(status, 200)
                    self.assertIn('MANAGED_RECALL_REFUSED', data.decode())
                    self.assertNotIn('PRIVATE_GUARD_CANARY', data.decode())
                    self.assertNotIn('amber-kite', data.decode())
            guard_state.update(calls=0, fail_at=0)
            denied_search = {'jsonrpc': '2.0', 'id': 8, 'method': 'tools/call',
                             'params': {'name': 'search_managed_memory', 'arguments': {'query': 'DENIED_CONTENT_CANARY'}}}
            status, _, data = await self.request(app, '/mcp', 'POST', json.dumps(denied_search).encode(), mcp_headers)
            self.assertEqual(status, 200)
            self.assertNotIn('DENIED_REFERENCE_CANARY', data.decode())
            result = json.loads(data)['result']
            payload = result.get('structuredContent') or json.loads(result['content'][0]['text'])
            self.assertEqual(payload['matches'], [])
            listed = {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'}
            status, _, data = await self.request(app, '/mcp', 'POST', json.dumps(listed).encode(), mcp_headers)
            self.assertEqual(status, 200)
            self.assertEqual({x['name'] for x in json.loads(data)['result']['tools']},
                             {'search_managed_memory', 'read_managed_memory', 'search', 'fetch'})
            connector_search = {'jsonrpc': '2.0', 'id': 20, 'method': 'tools/call',
                                'params': {'name': 'search', 'arguments': {'query': 'amber'}}}
            status, _, data = await self.request(app, '/mcp', 'POST', json.dumps(connector_search).encode(), mcp_headers)
            self.assertEqual(status, 200)
            search_res = json.loads(data)['result']
            search_payload = search_res.get('structuredContent') or json.loads(search_res['content'][0]['text'])
            self.assertEqual(len(search_payload['results']), 1)
            self.assertEqual(search_payload['results'][0]['id'], 'decision')
            self.assertIn('amber-kite', search_payload['results'][0]['text'])
            connector_fetch = {'jsonrpc': '2.0', 'id': 21, 'method': 'tools/call',
                               'params': {'name': 'fetch', 'arguments': {'id': 'decision', 'start_line': 7, 'line_count': 1}}}
            status, _, data = await self.request(app, '/mcp', 'POST', json.dumps(connector_fetch).encode(), mcp_headers)
            self.assertEqual(status, 200)
            fetch_res = json.loads(data)['result']
            fetch_payload = fetch_res.get('structuredContent') or json.loads(fetch_res['content'][0]['text'])
            self.assertEqual(fetch_payload['id'], 'decision')
            self.assertIn('amber-kite', fetch_payload['text'])
            read = {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call',
                    'params': {'name': 'read_managed_memory',
                               'arguments': {'note_id': 'decision', 'start_line': 7, 'line_count': 1}}}
            status, _, data = await self.request(app, '/mcp', 'POST', json.dumps(read).encode(), mcp_headers)
            self.assertEqual(status, 200)
            self.assertIn('amber-kite', data.decode())
            self.assertIn(fixture.entry()['sha256'], data.decode())
            read['id'] = 4
            read['params']['arguments'] = {'note_id': 'decision', 'start_line': 8, 'line_count': 40}
            status, _, data = await self.request(app, '/mcp', 'POST', json.dumps(read).encode(), mcp_headers)
            self.assertEqual(status, 200)
            self.assertIn('MANAGED_RECALL_REFUSED', data.decode())
            self.assertNotIn('DENIED_CONTENT_CANARY', data.decode())
            for name, arguments in [('search_managed_memory', {'query': 'amber', 'limit': 'PRIVATE_INPUT_CANARY'}),
                                    ('read_managed_memory', {'note_id': 'PRIVATE_INPUT_CANARY' * 10})]:
                malformed = {'jsonrpc': '2.0', 'id': 5, 'method': 'tools/call',
                             'params': {'name': name, 'arguments': arguments}}
                status, _, data = await self.request(app, '/mcp', 'POST', json.dumps(malformed).encode(), mcp_headers)
                self.assertEqual(status, 200)
                self.assertIn('MANAGED_RECALL_REFUSED', data.decode())
                self.assertNotIn('PRIVATE_INPUT_CANARY', data.decode())
            read['params']['arguments'] = {'note_id': 'unknown'}
            status, _, data = await self.request(app, '/mcp', 'POST', json.dumps(read).encode(), mcp_headers)
            self.assertEqual(status, 200)
            self.assertIn('MANAGED_RECALL_REFUSED', data.decode())
            owner = next(m.kwargs['owner'] for m in app.user_middleware if 'owner' in m.kwargs)
            expires, original_access = owner._tokens[token]
            for change in ({'resource': 'https://wrong.example/mcp'}, {'scopes': ['other']},
                           {'subject': 'different-owner'}, {'client_id': 'different-client'},
                           {'claims': {'iss': 'https://wrong.example'}}, {'expires_at': 1}):
                with self.subTest(token=change):
                    owner._tokens[token] = (expires, original_access.model_copy(update=change))
                    status, _, _ = await self.request(app, '/mcp', 'POST', json.dumps(call).encode(), mcp_headers)
                    self.assertEqual(status, 401)
            owner._tokens[token] = (expires, original_access)
            original_grant = fixture.grant_path.read_bytes()
            fixture.grant_path.write_bytes(original_grant + b' ')
            status, _, data = await self.request(app, '/mcp', 'POST', json.dumps(call).encode(), mcp_headers)
            self.assertEqual(status, 200)
            self.assertIn('MANAGED_RECALL_REFUSED', data.decode())
            fixture.grant_path.write_bytes(original_grant)
            status, _, _ = await self.request(app, '/token', 'POST', token_form,
                                              [(b'content-type', b'application/x-www-form-urlencoded')])
            self.assertNotEqual(status, 200)
        self.assertEqual(before, {p: p.read_bytes() for p in fixture.base.rglob('*') if p.is_file()})
        self.assertTrue(owner._closed)
        self.assertEqual(owner._tokens, {})

    async def test_bad_oauth_parameters_and_oversized_requests_are_redacted(self):
        fixture = fixtures.ManagedMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        app = create_app(fixture.args[0], fixture.args[1], fixture.args[2], 'https://bridge.example',
                         'synthetic-client', 'https://client.example/callback', 's' * 43)
        base = {'client_id': 'synthetic-client', 'redirect_uri': 'https://client.example/callback',
                'response_type': 'code', 'scope': 'memory:read', 'state': 'synthetic-state',
                'code_challenge': 'a' * 43, 'code_challenge_method': 'S256',
                'resource': 'https://bridge.example/mcp'}
        async with app.router.lifespan_context(app):
            for mutation in ({'code_challenge_method': 'plain'}, {'code_challenge_method': ''},
                             {'client_id': 'PRIVATE_INPUT_CANARY'}, {'resource': 'https://other.example/mcp'},
                             {'redirect_uri': 'https://other.example/callback'}):
                query = urlencode({**base, **mutation}).encode()
                status, invalid_headers, data = await self.request(app, '/authorize', query=query)
                self.assertEqual(status, 400)
                self.assertNotIn(b'location', invalid_headers)
                self.assertNotIn(b'PRIVATE_INPUT_CANARY', data)
            status, _, _ = await self.request(app, '/authorize', query=urlencode(base).encode() + b'&scope=memory%3Aread')
            self.assertEqual(status, 400)
            for path in ('/authorize', '/token', '/consent', '/mcp'):
                status, _, data = await self.request(app, path, 'POST',
                    headers=[(b'content-length', b'1')], chunks=[b'x' * 9000, b'PRIVATE_INPUT_CANARY' * 500])
                self.assertEqual(status, 413)
                self.assertNotIn(b'PRIVATE_INPUT_CANARY', data)
            missing_method = {k: v for k, v in base.items() if k != 'code_challenge_method'}
            status, _, _ = await self.request(app, '/authorize', query=urlencode(missing_method).encode())
            self.assertEqual(status, 400)
            status, _, data = await self.request(app, '/.well-known/oauth-authorization-server', host=b'PRIVATE_HOST_CANARY')
            self.assertEqual(status, 400)
            self.assertNotIn(b'PRIVATE_HOST_CANARY', data)
            status, _, data = await self.request(app, '/.well-known/oauth-authorization-server',
                                                  headers=[(b'origin', b'https://PRIVATE_ORIGIN_CANARY')])
            self.assertEqual(status, 400)
            self.assertNotIn(b'PRIVATE_ORIGIN_CANARY', data)
            status, headers, data = await self.request(app, '/authorize/', query=b'PRIVATE_QUERY_CANARY')
            self.assertEqual(status, 404)
            self.assertNotIn(b'location', headers)
            self.assertNotIn(b'PRIVATE_QUERY_CANARY', data)
            status, _, _ = await self.request(app, '/token', 'POST', b'client_id=x',
                                              query=b'client_id=synthetic-client')
            self.assertEqual(status, 400)
            status, _, _ = await self.request(app, '/consent', query=b'x=' + b'a' * 4096)
            self.assertEqual(status, 413)
            status, _, _ = await self.request(app, '/mcp', 'POST', b'{}',
                [(b'authorization', b'Bearer invalid'), (b'content-type', b'application/json')])
            self.assertEqual(status, 401)

    async def test_canonical_grant_is_rejected_before_reader_load(self):
        from unittest.mock import patch
        fixture = fixtures.ManagedMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.grant['source_kind'] = 'canonical'
        fixture.pin()
        with patch('chat_recall_http._load') as load:
            with self.assertRaises(ValueError):
                create_app(fixture.args[0], fixture.args[1], fixture.args[2], 'https://bridge.example',
                           'synthetic-client', 'https://client.example/callback', 's' * 43)
            load.assert_not_called()

    async def test_issuer_metadata_agrees_with_protected_resource(self):
        fixture = fixtures.ManagedMemoryTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        app = create_app(fixture.args[0], fixture.args[1], fixture.args[2], 'https://bridge.example',
                         'synthetic-client', 'https://client.example/callback', 's' * 43)
        async with app.router.lifespan_context(app):
            status, _, data = await self.request(app, '/.well-known/oauth-authorization-server')
            self.assertEqual(status, 200); metadata=json.loads(data)
            self.assertIs(metadata.get('authorization_response_iss_parameter_supported'), True)
            self.assertEqual(metadata['issuer'], 'https://bridge.example')
            status_oidc, _, data_oidc = await self.request(app, '/.well-known/openid-configuration')
            self.assertEqual(status_oidc, 200)
            self.assertEqual(json.loads(data_oidc), metadata)
            status_root, _, data_root = await self.request(app, '/')
            self.assertEqual(status_root, 200)
            self.assertEqual(json.loads(data_root)['status'], 'ok')
            status, _, data = await self.request(app, '/.well-known/oauth-protected-resource/mcp')
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(data)['authorization_servers'], [metadata['issuer']])

    async def test_stable_callback_exact_binding_and_no_mismatch_redirect(self):
        fixture=fixtures.ManagedMemoryTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        stable='https://chatgpt.com/connector_platform_oauth_redirect'
        app=create_app(fixture.args[0],fixture.args[1],fixture.args[2],'https://bridge.example',
                       'synthetic-client',stable,'s'*43)
        params={'client_id':'synthetic-client','redirect_uri':stable,'response_type':'code',
                'scope':'memory:read','state':'synthetic-state','code_challenge':'a'*43,
                'code_challenge_method':'S256','resource':'https://bridge.example/mcp'}
        async with app.router.lifespan_context(app):
            status,headers,_=await self.request(app,'/authorize',query=urlencode(params).encode())
            self.assertEqual(status,302)
            consent=urlsplit(headers[b'location'].decode())
            self.assertEqual((consent.scheme,consent.netloc,consent.path),('https','bridge.example','/consent'))
            self.assertNotIn('iss',parse_qs(consent.query))
            from unittest.mock import patch
            from mcp.server.auth.provider import AuthorizeError
            with patch.object(OwnerOAuth,'authorize',side_effect=AuthorizeError('temporarily_unavailable','fictional')):
                error_status,error_headers,_=await self.request(app,'/authorize',query=urlencode(params).encode())
            self.assertEqual(error_status,302)
            error_url=urlsplit(error_headers[b'location'].decode())
            self.assertEqual(error_url.scheme+'://'+error_url.netloc+error_url.path,stable)
            error_query=parse_qs(error_url.query)
            self.assertEqual(error_query.get('state'),['synthetic-state'])
            self.assertEqual(error_query.get('iss'),['https://bridge.example'])
            status,headers,_=await self.request(app,'/authorize',query=urlencode({**params,'redirect_uri':stable+'-wrong'}).encode())
            self.assertEqual(status,400); self.assertNotIn(b'location',headers)
    async def test_normalized_callback_is_refused(self):
        fixture=fixtures.ManagedMemoryTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        for callback in ('https://CLIENT.example/callback','https://client.example:443/callback'):
            with self.subTest(callback=callback), self.assertRaises(ValueError):
                create_app(fixture.args[0],fixture.args[1],fixture.args[2],'https://bridge.example',
                           'synthetic-client',callback,'s'*43)

    async def test_normalized_issuer_or_resource_is_refused(self):
        fixture=fixtures.ManagedMemoryTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        for origin in ('https://BRIDGE.example','https://bridge.example:443'):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                create_app(fixture.args[0],fixture.args[1],fixture.args[2],origin,
                           'synthetic-client','https://client.example/callback','s'*43)

    async def test_authorization_redirect_must_be_local_consent_or_safe_error(self):
        from unittest.mock import patch
        fixture=fixtures.ManagedMemoryTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        app=create_app(fixture.args[0], fixture.args[1], fixture.args[2], 'https://bridge.example',
                       'synthetic-client', 'https://client.example/callback', 's'*43)
        params={'client_id':'synthetic-client','redirect_uri':'https://client.example/callback',
                'response_type':'code','scope':'memory:read','state':'synthetic-state',
                'code_challenge':'a'*43,'code_challenge_method':'S256','resource':'https://bridge.example/mcp'}
        malicious=['https://evil.example/collect?code=canary',
                   'https://client.example/callback?error=x&state=synthetic-state&iss=https://evil.example',
                   'https://client.example/callback?error=x&state=synthetic-state&state=evil',
                   'https://client.example/callback?code=canary&state=synthetic-state',
                   'https://client.example/callback?error=x#evil&state=synthetic-state']
        async with app.router.lifespan_context(app):
            for target in malicious:
                with self.subTest(target=target), patch.object(OwnerOAuth,'authorize',return_value=target):
                    status,headers,_=await self.request(app,'/authorize',query=urlencode(params).encode())
                    self.assertEqual(status,500); self.assertNotIn(b'location',headers)
            status,headers,_=await self.request(app,'/authorize',query=urlencode({**params,'iss':'https://evil.example'}).encode())
            self.assertEqual(status,400); self.assertNotIn(b'location',headers)

    async def test_client_lookup_exception_is_local_redacted_and_not_logged(self):
        from unittest.mock import patch
        fixture=fixtures.ManagedMemoryTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        app=create_app(fixture.args[0],fixture.args[1],fixture.args[2],'https://bridge.example',
                       'synthetic-client','https://client.example/callback','s'*43)
        params={'client_id':'synthetic-client','redirect_uri':'https://client.example/callback',
                'response_type':'code','scope':'memory:read','state':'synthetic-state',
                'code_challenge':'a'*43,'code_challenge_method':'S256','resource':'https://bridge.example/mcp'}
        async with app.router.lifespan_context(app):
            with patch.object(OwnerOAuth,'get_client',side_effect=RuntimeError('PRIVATE_LOOKUP_CANARY')):
                with self.assertNoLogs('mcp.server.auth.handlers.authorize',level='ERROR'):
                    status,headers,body=await self.request(app,'/authorize',query=urlencode(params).encode())
            self.assertEqual(status,500); self.assertNotIn(b'location',headers)
            self.assertNotIn(b'PRIVATE_LOOKUP_CANARY',body)

    async def test_authorization_catchall_error_is_redacted_and_includes_issuer(self):
        from unittest.mock import patch
        from chat_recall_oauth import RedactedOAuth
        fixture=fixtures.ManagedMemoryTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        app=create_app(fixture.args[0], fixture.args[1], fixture.args[2], 'https://bridge.example',
                       'synthetic-client', 'https://client.example/callback', 's'*43)
        params={'client_id':'synthetic-client','redirect_uri':'https://client.example/callback',
                'response_type':'code','scope':'memory:read','state':'synthetic-state',
                'code_challenge':'a'*43,'code_challenge_method':'S256','resource':'https://bridge.example/mcp'}
        async with app.router.lifespan_context(app):
            with patch.object(RedactedOAuth,'authorize',side_effect=RuntimeError('PRIVATE_CATCHALL_CANARY')), \
                 patch.object(OwnerOAuth,'authorize',side_effect=RuntimeError('PRIVATE_CATCHALL_CANARY')):
                with self.assertNoLogs('mcp.server.auth.handlers.authorize',level='ERROR'):
                    status,headers,body=await self.request(app,'/authorize',query=urlencode(params).encode())
            self.assertNotIn(b'PRIVATE_CATCHALL_CANARY',body)
            self.assertNotIn(b'PRIVATE_CATCHALL_CANARY',headers.get(b'location',b''))
            self.assertEqual(status,302)
            query=parse_qs(urlsplit(headers[b'location'].decode()).query)
            self.assertEqual(query.get('error'),['server_error'])
            self.assertEqual(query.get('state'),['synthetic-state'])
            self.assertEqual(query.get('iss'),['https://bridge.example'])

    async def test_provider_failure_neither_logs_nor_echoes_sensitive_exception(self):
        from unittest.mock import patch
        fixture = fixtures.ManagedMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        app = create_app(fixture.args[0], fixture.args[1], fixture.args[2], 'https://bridge.example',
                         'synthetic-client', 'https://client.example/callback', 's' * 43)
        params = {'client_id': 'synthetic-client', 'redirect_uri': 'https://client.example/callback',
                  'response_type': 'code', 'scope': 'memory:read', 'state': 'synthetic-state',
                  'code_challenge': 'a' * 43, 'code_challenge_method': 'S256',
                  'resource': 'https://bridge.example/mcp'}
        async with app.router.lifespan_context(app):
            with patch.object(OwnerOAuth, 'authorize', side_effect=RuntimeError('PRIVATE_EXCEPTION_CANARY')):
                with self.assertNoLogs('mcp.server.auth.handlers.authorize', level='ERROR'):
                    status, headers, data = await self.request(app, '/authorize', query=urlencode(params).encode())
            self.assertNotIn(b'PRIVATE_EXCEPTION_CANARY', data)
            self.assertNotIn(b'PRIVATE_EXCEPTION_CANARY', headers.get(b'location', b''))
            self.assertEqual(status, 302)
            location=urlsplit(headers[b'location'].decode())
            self.assertEqual(location.scheme+'://'+location.netloc+location.path, 'https://client.example/callback')
            callback=parse_qs(location.query)
            self.assertEqual(callback.get('iss'), ['https://bridge.example'])
            self.assertEqual(callback.get('state'), ['synthetic-state'])
            self.assertIn('error', callback)


    async def test_ticket_capacity_and_expiry_through_authorize_endpoint(self):
        from unittest.mock import patch
        fixture = fixtures.ManagedMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        app = create_app(fixture.args[0], fixture.args[1], fixture.args[2], 'https://bridge.example',
                         'synthetic-client', 'https://client.example/callback', 's' * 43)
        params = {'client_id': 'synthetic-client', 'redirect_uri': 'https://client.example/callback',
                  'response_type': 'code', 'scope': 'memory:read', 'state': 'synthetic-state',
                  'code_challenge': 'a' * 43, 'code_challenge_method': 'S256',
                  'resource': 'https://bridge.example/mcp'}
        owner = next(m.kwargs['owner'] for m in app.user_middleware if 'owner' in m.kwargs)
        async with app.router.lifespan_context(app):
            with patch('chat_recall_oauth.time.time', return_value=1000):
                for _ in range(32):
                    status, headers, _ = await self.request(app, '/authorize', query=urlencode(params).encode())
                    self.assertEqual(status, 302)
                    self.assertTrue(headers[b'location'].startswith(b'https://bridge.example/consent?'))
                status, headers, _ = await self.request(app, '/authorize', query=urlencode(params).encode())
                self.assertEqual(status, 302)
                self.assertIn(b'error=temporarily_unavailable', headers[b'location'])
                self.assertEqual(parse_qs(urlsplit(headers[b'location'].decode()).query).get('iss'), ['https://bridge.example'])
                self.assertNotIn(b'code=', headers[b'location'])
            with patch('chat_recall_oauth.time.time', return_value=1121):
                status, headers, _ = await self.request(app, '/authorize', query=urlencode(params).encode())
                self.assertEqual(status, 302)
                self.assertTrue(headers[b'location'].startswith(b'https://bridge.example/consent?'))
        self.assertTrue(owner._closed)
        self.assertEqual(owner._tickets, {})
        self.assertEqual(owner._tokens, {})

    async def test_factory_errors_do_not_echo_local_path(self):
        with self.assertRaises(ValueError) as caught:
            create_app('PRIVATE_PATH_CANARY', '0' * 64, 'codex-openai', 'https://bridge.example',
                       'synthetic-client', 'https://client.example/callback', 's' * 43)
        self.assertNotIn('PRIVATE_PATH_CANARY', str(caught.exception))

    async def test_factory_rejects_wildcard_callback(self):
        fixture = fixtures.ManagedMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        with self.assertRaises(ValueError):
            create_app(fixture.args[0], fixture.args[1], fixture.args[2], 'https://bridge.example',
                       'synthetic-client', 'https://client.example/*', 's' * 43)

    async def test_disabled_synthetic_policy_fails_before_serving(self):
        fixture = fixtures.ManagedMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.policy['enabled'] = False
        fixture.write(fixture.policy_path, fixture.policy)
        fixture.grant['policy_sha256'] = hashlib.sha256(fixture.policy_path.read_bytes()).hexdigest()
        fixture.pin()
        with self.assertRaises(ValueError):
            create_app(fixture.args[0], fixture.args[1], fixture.args[2], 'https://bridge.example',
                       'synthetic-client', 'https://client.example/callback', 's' * 43)

    async def test_selected_personal_metadata_refuses_synthetic_grant(self):
        fixture = fixtures.ManagedMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        # Only the entry label changes: the file remains the fictional synthetic fixture.
        fixture.manifest['notes'][0]['privacy'] = 'personal'
        fixture.publish()
        before = {p: p.read_bytes() for p in fixture.base.rglob('*') if p.is_file()}
        with self.assertRaises(ValueError):
            create_app(fixture.args[0], fixture.args[1], fixture.args[2], 'https://bridge.example',
                       'synthetic-client', 'https://client.example/callback', 's' * 43)
        self.assertEqual(before, {p: p.read_bytes() for p in fixture.base.rglob('*') if p.is_file()})

    async def test_consent_rate_limit_and_expiry_at_endpoint(self):
        from unittest.mock import patch
        fixture = fixtures.ManagedMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        app = create_app(fixture.args[0], fixture.args[1], fixture.args[2], 'https://bridge.example',
                         'synthetic-client', 'https://client.example/callback', 's' * 43)
        params = {'client_id': 'synthetic-client', 'redirect_uri': 'https://client.example/callback',
                  'response_type': 'code', 'scope': 'memory:read', 'state': 'synthetic-state',
                  'code_challenge': 'a' * 43, 'code_challenge_method': 'S256',
                  'resource': 'https://bridge.example/mcp'}
        async with app.router.lifespan_context(app):
            with patch('chat_recall_oauth.time.time', return_value=1000):
                _, headers, _ = await self.request(app, '/authorize', query=urlencode(params).encode())
                query = urlsplit(headers[b'location'].decode()).query.encode()
                status, headers, page = await self.request(app, '/consent', query=query)
                self.assertEqual(status, 200)
                self.assertNotIn(b'location', headers)
                ticket = re.search(rb'name="ticket" value="([^"]+)"', page).group(1).decode()
                csrf = re.search(rb'name="csrf" value="([^"]+)"', page).group(1).decode()
                common = [(b'origin', b'https://bridge.example'),
                          (b'content-type', b'application/x-www-form-urlencoded'),
                          (b'cookie', ('brain_csrf=' + csrf).encode())]
                bad = urlencode({'ticket': ticket, 'csrf': csrf, 'owner_code': 'wrong'}).encode()
                good = urlencode({'ticket': ticket, 'csrf': csrf, 'owner_code': 's' * 43}).encode()
                for _ in range(10):
                    status, _, _ = await self.request(app, '/consent', 'POST', bad, common)
                    self.assertEqual(status, 403)
                status, _, _ = await self.request(app, '/consent', 'POST', good, common)
                self.assertEqual(status, 403)
            with patch('chat_recall_oauth.time.time', return_value=1061):
                status, _, _ = await self.request(app, '/consent', 'POST', good, common)
                self.assertEqual(status, 303)
            with patch('chat_recall_oauth.time.time', return_value=2000):
                _, headers, _ = await self.request(app, '/authorize', query=urlencode(params).encode())
                query = urlsplit(headers[b'location'].decode()).query.encode()
                _, _, page = await self.request(app, '/consent', query=query)
                ticket = re.search(rb'name="ticket" value="([^"]+)"', page).group(1).decode()
                csrf = re.search(rb'name="csrf" value="([^"]+)"', page).group(1).decode()
                common = [(b'origin', b'https://bridge.example'),
                          (b'content-type', b'application/x-www-form-urlencoded'),
                          (b'cookie', ('brain_csrf=' + csrf).encode())]
                good = urlencode({'ticket': ticket, 'csrf': csrf, 'owner_code': 's' * 43}).encode()
            with patch('chat_recall_oauth.time.time', return_value=2121):
                status, _, _ = await self.request(app, '/consent', 'POST', good, common)
                self.assertEqual(status, 403)

    async def test_cli_binds_loopback_and_does_not_start_on_invalid_port(self):
        from unittest.mock import patch
        fixture = fixtures.ManagedMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.grant['private_root'] = str(fixture.private.resolve())
        fixture.grant['manifest_pointer'] = str(fixture.pointer.resolve())
        fixture.pin()
        secret = fixture.private.resolve() / 'synthetic-owner-code'
        secret.write_text('s' * 43, encoding='ascii')
        args = ['--grant', str(fixture.grant_path.resolve()), '--grant-sha256', fixture.args[1],
                '--client', fixture.args[2], '--origin', 'https://bridge.example',
                '--client-id', 'synthetic-client', '--callback', 'https://client.example/callback',
                '--owner-code-file', str(secret), '--port', '8765']
        with patch('uvicorn.Server') as server:
            self.assertEqual(main(args), 0)
            config = server.call_args.args[0]
            self.assertEqual(config.host, '127.0.0.1')
            self.assertEqual(config.port, 8765)
            self.assertFalse(config.access_log)
            self.assertFalse(config.proxy_headers)
            server.return_value.run.assert_called_once()
        with patch('uvicorn.Server') as server:
            self.assertEqual(main(args[:-1] + ['0']), 1)
            server.assert_not_called()
        outside = fixture.base.resolve() / 'PRIVATE_PATH_CANARY'
        outside.write_text('s' * 43, encoding='ascii')
        wrong = list(args)
        wrong[wrong.index('--owner-code-file') + 1] = str(outside)
        with patch('uvicorn.Server') as server:
            self.assertEqual(main(wrong), 1)
            server.assert_not_called()

    async def test_cli_always_clears_provider_without_lifespan(self):
        from unittest.mock import patch
        fixture = fixtures.ManagedMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.grant['private_root'] = str(fixture.private.resolve())
        fixture.grant['manifest_pointer'] = str(fixture.pointer.resolve())
        fixture.pin()
        secret = fixture.private.resolve() / 'synthetic-owner-code'
        secret.write_text('s' * 43, encoding='ascii')
        args = ['--grant', str(fixture.grant_path.resolve()), '--grant-sha256', fixture.args[1],
                '--client', fixture.args[2], '--origin', 'https://bridge.example',
                '--client-id', 'synthetic-client', '--callback', 'https://client.example/callback',
                '--owner-code-file', str(secret), '--port', '8765']
        for failure in ('config', 'run', 'normal'):
            with self.subTest(failure=failure):
                app = create_app(fixture.args[0], fixture.args[1], fixture.args[2], 'https://bridge.example',
                                 'synthetic-client', 'https://client.example/callback', 's' * 43)
                owner = next(m.kwargs['owner'] for m in app.user_middleware if 'owner' in m.kwargs)
                client = await owner.get_client('synthetic-client')
                params = AuthorizationParams(state='state', scopes=['memory:read'], code_challenge='a' * 43,
                                             redirect_uri='https://client.example/callback',
                                             redirect_uri_provided_explicitly=True,
                                             resource='https://bridge.example/mcp')
                ticket = (await owner.authorize(client, params)).rsplit('=', 1)[-1]
                csrf = owner.consent_csrf(ticket)
                code, _ = owner.consent(ticket, csrf, csrf, 's' * 43)
                record = await owner.load_authorization_code(client, code)
                token = await owner.exchange_authorization_code(client, record)
                with patch('chat_recall_http.create_app', return_value=app), patch('uvicorn.Config') as config, \
                     patch('uvicorn.Server') as server:
                    if failure == 'config':
                        config.side_effect = RuntimeError('synthetic startup failure')
                    elif failure == 'run':
                        server.return_value.run.side_effect = RuntimeError('synthetic run failure')
                    self.assertEqual(main(args), 0 if failure == 'normal' else 1)
                self.assertTrue(owner._closed)
                self.assertIsNone(await owner.load_access_token(token.access_token))
                app.state.owner_cleanup()
                self.assertIsNone(await owner.load_access_token(token.access_token))

    async def test_expired_authorization_code_refused_by_token_endpoint(self):
        from unittest.mock import patch
        fixture = fixtures.ManagedMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        app = create_app(fixture.args[0], fixture.args[1], fixture.args[2], 'https://bridge.example',
                         'synthetic-client', 'https://client.example/callback', 's' * 43)
        owner = next(m.kwargs['owner'] for m in app.user_middleware if 'owner' in m.kwargs)
        verifier = 'v' * 43
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        params = AuthorizationParams(state='synthetic-state', scopes=['memory:read'], code_challenge=challenge,
                                     redirect_uri='https://client.example/callback', redirect_uri_provided_explicitly=True,
                                     resource='https://bridge.example/mcp')
        async with app.router.lifespan_context(app):
            with patch('chat_recall_oauth.time.time', return_value=1000):
                client = await owner.get_client('synthetic-client')
                ticket = (await owner.authorize(client, params)).rsplit('=', 1)[-1]
                csrf = owner.consent_csrf(ticket)
                code, _ = owner.consent(ticket, csrf, csrf, 's' * 43)
            form = urlencode({'grant_type': 'authorization_code', 'client_id': 'synthetic-client',
                              'redirect_uri': 'https://client.example/callback', 'code': code,
                              'code_verifier': verifier, 'resource': 'https://bridge.example/mcp'}).encode()
            with patch('chat_recall_oauth.time.time', return_value=1061):
                status, _, data = await self.request(app, '/token', 'POST', form,
                                                    [(b'content-type', b'application/x-www-form-urlencoded')])
                self.assertEqual(status, 400)
                self.assertNotIn(code.encode(), data)

    async def test_authorize_accepts_ui_locales_and_prompt(self):
        fixture = fixtures.ManagedMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        app = create_app(fixture.args[0], fixture.args[1], fixture.args[2], 'https://bridge.example',
                         'synthetic-client', 'https://client.example/callback', 's' * 43)
        base = {'client_id': 'synthetic-client', 'redirect_uri': 'https://client.example/callback',
                'response_type': 'code', 'scope': 'memory:read', 'state': 'synthetic-state',
                'code_challenge': 'a' * 43, 'code_challenge_method': 'S256',
                'resource': 'https://bridge.example/mcp'}
        async with app.router.lifespan_context(app):
            # Test valid ui_locales variants
            for locales in ('en-US', 'en', 'en-US,en;q=0.9', 'fr-FR en-US'):
                query = urlencode({**base, 'ui_locales': locales}).encode()
                status, headers, _ = await self.request(app, '/authorize', query=query)
                self.assertEqual(status, 302)
                self.assertTrue(headers[b'location'].startswith(b'https://bridge.example/consent?ticket='))

            # Test valid prompt
            for prompt in ('consent', 'login'):
                query = urlencode({**base, 'prompt': prompt}).encode()
                status, headers, _ = await self.request(app, '/authorize', query=query)
                self.assertEqual(status, 302)
                self.assertTrue(headers[b'location'].startswith(b'https://bridge.example/consent?ticket='))

            # Test both ui_locales and prompt together
            query = urlencode({**base, 'ui_locales': 'en-US', 'prompt': 'consent'}).encode()
            status, headers, _ = await self.request(app, '/authorize', query=query)
            self.assertEqual(status, 302)
            self.assertTrue(headers[b'location'].startswith(b'https://bridge.example/consent?ticket='))

            # Test invalid ui_locales (bad characters or too long)
            for bad_locale in ('en/US', 'en<script>', 'a' * 65):
                query = urlencode({**base, 'ui_locales': bad_locale}).encode()
                status, _, _ = await self.request(app, '/authorize', query=query)
                self.assertEqual(status, 400)

            # Test invalid prompt (bad characters or too long)
            for bad_prompt in ('PROMPT', 'bad-prompt!', 'a' * 33):
                query = urlencode({**base, 'prompt': bad_prompt}).encode()
                status, _, _ = await self.request(app, '/authorize', query=query)
                self.assertEqual(status, 400)

            # Test disallowed unknown parameter
            query = urlencode({**base, 'extra_param': 'disallowed'}).encode()
            status, _, _ = await self.request(app, '/authorize', query=query)
            self.assertEqual(status, 400)


if __name__ == '__main__':
    unittest.main()
