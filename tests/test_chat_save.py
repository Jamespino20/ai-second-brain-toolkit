"""Exhaustive tests for explicit create-only chat saving via MCP (Task T13b)."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from chat_recall_http import create_app, _RedactedServer
from chat_recall_oauth import OwnerOAuth
from mcp.server.auth.provider import AuthorizationParams
from mcp.server.mcpserver.exceptions import ToolError
from migrate import digest, json_bytes
from save_interactive_memory import stage_chat_memory
import test_managed_memory as fixtures


class ChatSaveDirectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'private'
        self.root.mkdir()
        (self.root / '.private-staging.json').write_text(
            json.dumps({'live_writes': False, 'external_exports': False}),
            encoding='utf-8'
        )

    def test_stage_valid_chat_memory(self):
        title = "Deterministic SQLite cache layout"
        text = "Decided to use an in-memory SQLite database for test runs to avoid filesystem locking issues."
        tags = ["architecture", "database", "testing"]
        metadata = {"priority": "high", "topic": "storage"}

        result = stage_chat_memory(
            self.root,
            title=title,
            text=text,
            tags=tags,
            metadata=metadata,
            kind="decision"
        )

        self.assertEqual(result['status'], 'STAGED')
        self.assertEqual(result['proposals'], 1)
        self.assertEqual(result['title'], title)
        self.assertTrue(result['note_id'].startswith('brain-save-'))
        self.assertEqual(len(result['source_sha256']), 64)

        # Check candidate note
        candidate_path = self.root / result['candidate']
        self.assertTrue(candidate_path.exists())
        candidate = json.loads(candidate_path.read_text(encoding='utf-8'))
        self.assertEqual(candidate['title'], title)
        self.assertEqual(candidate['kind'], 'decision')
        self.assertEqual(candidate['review_state'], 'candidate')
        self.assertEqual(candidate['privacy'], 'personal')
        self.assertFalse(candidate['external_processing'])
        self.assertEqual(candidate['tags'], tags)
        self.assertEqual(candidate['chat_capture']['metadata'], metadata)
        self.assertEqual(candidate['body'], text)

        # Check rendered markdown proposal in test-vault
        proposal_path = self.root / result['proposal']
        self.assertTrue(proposal_path.exists())
        md_content = proposal_path.read_text(encoding='utf-8')
        self.assertIn(f'# {title}', md_content)
        self.assertIn(text, md_content)
        self.assertIn('> [!warning] Candidate only', md_content)
        self.assertIn('## Evidence', md_content)

        # Check raw archive
        archive_path = self.root / result['source']
        self.assertTrue(archive_path.exists())
        archive = json.loads(archive_path.read_text(encoding='utf-8'))
        self.assertEqual(archive['chat_summary']['title'], title)

    def test_idempotent_duplicate_replay(self):
        title = "Stable API design principle"
        text = "Prefer explicit keyword arguments and strict fail-closed validation on all endpoints."

        first = stage_chat_memory(self.root, title=title, text=text)
        self.assertEqual(first['status'], 'STAGED')
        self.assertEqual(first['proposals'], 1)

        first_md = (self.root / first['proposal']).read_bytes()
        first_candidate = (self.root / first['candidate']).read_bytes()

        # Replay with exact same input
        second = stage_chat_memory(self.root, title=title, text=text)
        self.assertEqual(second['status'], 'DUPLICATE_SOURCE')
        self.assertEqual(second['proposals'], 0)
        self.assertEqual(second['note_id'], first['note_id'])
        self.assertEqual(second['source_sha256'], first['source_sha256'])

        # Verify no file mutations occurred on replay
        self.assertEqual((self.root / second['proposal']).read_bytes(), first_md)
        self.assertEqual((self.root / second['candidate']).read_bytes(), first_candidate)

    def test_summary_fallback_when_text_omitted(self):
        title = "Summary only proposal"
        summary = "Short summary of the discussion."

        result = stage_chat_memory(self.root, title=title, summary=summary)
        self.assertEqual(result['status'], 'STAGED')
        candidate = json.loads((self.root / result['candidate']).read_text(encoding='utf-8'))
        self.assertEqual(candidate['body'], summary)

    def test_text_takes_precedence_if_both_provided(self):
        title = "Both text and summary"
        result = stage_chat_memory(self.root, title=title, text="Primary text", summary="Fallback summary")
        candidate = json.loads((self.root / result['candidate']).read_text(encoding='utf-8'))
        self.assertEqual(candidate['body'], "Primary text")

    def test_refuse_missing_content(self):
        with self.assertRaisesRegex(ValueError, 'INVALID_CONTENT'):
            stage_chat_memory(self.root, title="Valid title")
        with self.assertRaisesRegex(ValueError, 'INVALID_CONTENT'):
            stage_chat_memory(self.root, title="Valid title", text="   ")

    def test_refuse_title_violations(self):
        valid_text = "Some valid content."

        # Empty or whitespace title
        for bad_title in ("", "   ", "\t", "\n"):
            with self.subTest(title=bad_title):
                with self.assertRaises((ValueError, Exception)):
                    stage_chat_memory(self.root, title=bad_title, text=valid_text)

        # Title too long (> 120 chars)
        with self.assertRaisesRegex(ValueError, 'INVALID_TITLE_LENGTH'):
            stage_chat_memory(self.root, title="a" * 121, text=valid_text)

        # Traversal attempts in title
        for bad_title in ("../escape", "..\\escape", "folder/title", "folder\\title", "..", "foo/../bar"):
            with self.subTest(traversal=bad_title):
                with self.assertRaisesRegex(ValueError, 'INVALID_TITLE_CHARACTERS'):
                    stage_chat_memory(self.root, title=bad_title, text=valid_text)

        # Forbidden filesystem characters in title
        for bad_char in (':', '*', '?', '"', '<', '>', '|', '\r', '\n', '\0'):
            with self.subTest(char=bad_char):
                with self.assertRaisesRegex(ValueError, 'INVALID_TITLE_CHARACTERS'):
                    stage_chat_memory(self.root, title=f"title{bad_char}test", text=valid_text)

    def test_refuse_oversized_content(self):
        title = "Valid title"
        oversized = "x" * 16385
        with self.assertRaisesRegex(ValueError, 'INVALID_CONTENT_LENGTH'):
            stage_chat_memory(self.root, title=title, text=oversized)

        # UTF-8 byte boundary check (16KB)
        multi_byte = "\u2603" * 6000  # 3 bytes each = 18,000 bytes > 16,384 bytes
        with self.assertRaisesRegex(ValueError, 'CONTENT_TOO_LARGE'):
            stage_chat_memory(self.root, title=title, text=multi_byte)

    def test_refuse_privacy_risks(self):
        valid_title = "Safe title"
        valid_text = "Safe content text."

        # Secret patterns in title
        with self.assertRaises(Exception):
            stage_chat_memory(self.root, title='Note with "password": "super-secret"', text=valid_text)

        # Secret patterns in text
        with self.assertRaises(Exception):
            stage_chat_memory(self.root, title=valid_title, text='Setting "api_key": "sk-123456789012345678901234567890"')

        # Secret patterns in tags (e.g. email or github personal access token pattern)
        with self.assertRaises(Exception):
            stage_chat_memory(self.root, title=valid_title, text=valid_text, tags=['ghp_' + 'a' * 25])

        # Secret patterns in metadata
        with self.assertRaises(Exception):
            stage_chat_memory(self.root, title=valid_title, text=valid_text, metadata={'api_key': 'ghp_' + 'a' * 25})

    def test_refuse_tag_violations(self):
        title = "Valid title"
        text = "Valid text"

        # Not a list
        with self.assertRaisesRegex(ValueError, 'INVALID_TAGS'):
            stage_chat_memory(self.root, title=title, text=text, tags="not-a-list")

        # Too many tags (> 16)
        with self.assertRaisesRegex(ValueError, 'INVALID_TAGS'):
            stage_chat_memory(self.root, title=title, text=text, tags=[f"tag{i}" for i in range(17)])

        # Tag too long (> 40 chars)
        with self.assertRaisesRegex(ValueError, 'INVALID_TAG_LENGTH'):
            stage_chat_memory(self.root, title=title, text=text, tags=["a" * 41])

        # Invalid characters in tag (spaces, slashes, punctuation)
        for bad_tag in ("tag with spaces", "tag/slash", "tag.dot", "tag$val"):
            with self.subTest(tag=bad_tag):
                with self.assertRaisesRegex(ValueError, 'INVALID_TAG_CHARACTERS'):
                    stage_chat_memory(self.root, title=title, text=text, tags=[bad_tag])

        # Duplicate tags
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_TAGS'):
            stage_chat_memory(self.root, title=title, text=text, tags=["topic", "Topic"])

    def test_refuse_metadata_violations(self):
        title = "Valid title"
        text = "Valid text"

        # Too many entries (> 16)
        with self.assertRaisesRegex(ValueError, 'INVALID_METADATA'):
            stage_chat_memory(self.root, title=title, text=text, metadata={f"k{i}": "val" for i in range(17)})

        # Key too long (> 40 chars)
        with self.assertRaisesRegex(ValueError, 'INVALID_METADATA_LENGTH'):
            stage_chat_memory(self.root, title=title, text=text, metadata={"a" * 41: "val"})

        # Value too long (> 200 chars)
        with self.assertRaisesRegex(ValueError, 'INVALID_METADATA_LENGTH'):
            stage_chat_memory(self.root, title=title, text=text, metadata={"key": "v" * 201})

        # Key with invalid chars
        with self.assertRaisesRegex(ValueError, 'INVALID_METADATA_KEY'):
            stage_chat_memory(self.root, title=title, text=text, metadata={"bad key": "val"})

        # Value with control characters / newlines
        with self.assertRaisesRegex(ValueError, 'INVALID_METADATA_VALUE'):
            stage_chat_memory(self.root, title=title, text=text, metadata={"key": "val\nbreak"})

    def test_refuse_invalid_kind(self):
        with self.assertRaisesRegex(ValueError, 'INVALID_KIND'):
            stage_chat_memory(self.root, title="Valid title", text="Valid text", kind="malicious_kind")

    def test_refuse_lock_contention(self):
        title = "Concurrent lock test"
        text = "Content"
        scope = 'chat/' + digest(title.casefold().encode('utf-8'))[:16]
        envelope = {
            'schema': 'brain-chat-save-archive-v1',
            'identity': {'client': 'chat-mcp', 'surface': 'regular-chat', 'invocation_kind': 'chat-mcp-create-only'},
            'chat_summary': {'title': title, 'content': text, 'tags': [], 'metadata': {}, 'kind': 'session'},
        }
        sha = digest(json_bytes(envelope))
        lock_file = self.root / 'staging/brain-save' / scope / sha / '.lock'
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.touch()

        with self.assertRaisesRegex(ValueError, 'SAVE_BUSY_RETRY_ONCE'):
            stage_chat_memory(self.root, title=title, text=text)

    def test_replay_detects_tampered_cache(self):
        title = "Tamper check"
        text = "First content"
        res = stage_chat_memory(self.root, title=title, text=text)

        # Corrupt archive
        archive = self.root / res['source']
        archive.write_bytes(b'{"corrupted": true}')

        with self.assertRaisesRegex(ValueError, 'CACHED_SOURCE_MISMATCH'):
            stage_chat_memory(self.root, title=title, text=text)

    def test_adversarial_hardening_cases(self):
        # 1. Split-key privacy detection
        with self.assertRaises((ValueError, Exception)):
            stage_chat_memory(self.root, title="Safe title", text="Safe text", metadata={'api_key': 'ghp_secrettoken12345'})

        # 2. Reserved metadata key rejection
        with self.assertRaisesRegex(ValueError, 'RESERVED_METADATA_KEY'):
            stage_chat_memory(self.root, title="Safe title", text="Safe text", metadata={'id': 'clobber_attempt'})

        # 3. Windows device names and trailing dot
        for bad_title in ('CON', 'PRN', 'AUX', 'NUL', 'COM1', 'LPT1', '.', 'note.'):
            with self.subTest(bad_title=bad_title):
                with self.assertRaises((ValueError, Exception)):
                    stage_chat_memory(self.root, title=bad_title, text="Safe text")

        # 4. Kind forwarding
        receipt = stage_chat_memory(self.root, title="Architectural Decision", text="We decided on SQLite.", kind="decision")
        self.assertEqual(receipt['status'], 'STAGED')
        candidate_file = self.root / receipt['candidate']
        candidate = json.loads(candidate_file.read_bytes())
        self.assertEqual(candidate['kind'], 'decision')


class ChatSaveMCPToolTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.fixture = fixtures.ManagedMemoryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    async def test_tool_registration_respects_enable_chat_save_flag(self):
        server_recall = []
        with patch('chat_recall_http._RedactedServer', side_effect=lambda *a, **kw: server_recall.append(_RedactedServer(*a, **kw)) or server_recall[-1]):
            app_recall = create_app(self.fixture.args[0], self.fixture.args[1], self.fixture.args[2],
                                    'https://bridge.example', 'synthetic-client',
                                    'https://client.example/callback', 's' * 43,
                                    enable_chat_save=False)
        tools_recall = {tool.name for tool in await server_recall[0].list_tools()}
        self.assertEqual(tools_recall, {'search_managed_memory', 'read_managed_memory', 'search', 'fetch'})
        app_recall.state.owner_cleanup()

        server_save = []
        with patch('chat_recall_http._RedactedServer', side_effect=lambda *a, **kw: server_save.append(_RedactedServer(*a, **kw)) or server_save[-1]):
            app_save = create_app(self.fixture.args[0], self.fixture.args[1], self.fixture.args[2],
                                  'https://bridge.example', 'synthetic-client',
                                  'https://client.example/callback', 's' * 43,
                                  enable_chat_save=True)
        tools_save = {tool.name for tool in await server_save[0].list_tools()}
        self.assertEqual(tools_save, {
            'search_managed_memory', 'read_managed_memory', 'search', 'fetch',
            'save_chat_memory', 'save_memory'
        })
        app_save.state.owner_cleanup()

    async def test_save_chat_memory_and_alias_via_server_call(self):
        servers = []
        with patch('chat_recall_http._RedactedServer', side_effect=lambda *a, **kw: servers.append(_RedactedServer(*a, **kw)) or servers[-1]):
            app = create_app(self.fixture.args[0], self.fixture.args[1], self.fixture.args[2],
                             'https://bridge.example', 'synthetic-client',
                             'https://client.example/callback', 's' * 43,
                             enable_chat_save=True)
        self.addCleanup(app.state.owner_cleanup)
        server = servers[0]

        # Call save_chat_memory
        args1 = {'title': 'Architecture decision', 'text': 'Use decoupled message bus for chat events.', 'tags': ['bus', 'arch']}
        res1 = await server.call_tool('save_chat_memory', args1)
        raw1 = res1.content[0].text
        data1 = json.loads(raw1)
        self.assertEqual(data1['status'], 'STAGED')
        self.assertEqual(data1['proposals'], 1)
        self.assertEqual(data1['title'], 'Architecture decision')
        self.assertTrue(data1['note_id'].startswith('brain-save-'))
        self.assertTrue(data1['proposal'].startswith('test-vault/'))

        # Call alias save_memory with different note
        args2 = {'title': 'Cache policy', 'summary': 'Store session tokens with 15-minute TTL.', 'tags': ['auth']}
        res2 = await server.call_tool('save_memory', args2)
        data2 = json.loads(res2.content[0].text)
        self.assertEqual(data2['status'], 'STAGED')
        self.assertEqual(data2['title'], 'Cache policy')

        # Replay save_chat_memory -> DUPLICATE_SOURCE
        res1_replay = await server.call_tool('save_chat_memory', args1)
        data1_replay = json.loads(res1_replay.content[0].text)
        self.assertEqual(data1_replay['status'], 'DUPLICATE_SOURCE')
        self.assertEqual(data1_replay['proposals'], 0)

    async def test_save_chat_memory_refuses_invalid_inputs_with_redacted_error(self):
        servers = []
        with patch('chat_recall_http._RedactedServer', side_effect=lambda *a, **kw: servers.append(_RedactedServer(*a, **kw)) or servers[-1]):
            app = create_app(self.fixture.args[0], self.fixture.args[1], self.fixture.args[2],
                             'https://bridge.example', 'synthetic-client',
                             'https://client.example/callback', 's' * 43,
                             enable_chat_save=True)
        self.addCleanup(app.state.owner_cleanup)
        server = servers[0]

        invalid_calls = [
            ('save_chat_memory', {}),  # Missing title
            ('save_chat_memory', {'title': ''}),  # Empty title
            ('save_chat_memory', {'title': '../escaped', 'text': 'safe text'}),  # Path traversal in title
            ('save_chat_memory', {'title': 'a' * 121, 'text': 'safe text'}),  # Title too long
            ('save_chat_memory', {'title': 'valid', 'text': 'x' * 20000}),  # Content too long
            ('save_chat_memory', {'title': 'valid', 'text': 'secret password: "CONFIDENTIAL_CANARY"'}),  # Privacy risk
            ('save_memory', {'title': 'bad:title', 'text': 'safe text'}),  # Forbidden char in alias
            ('save_memory', {'title': 'valid', 'text': 'safe', 'tags': ['invalid/tag']}),  # Bad tag
        ]

        for tool_name, args in invalid_calls:
            with self.subTest(tool=tool_name, args=args):
                with self.assertRaises(ToolError) as caught:
                    await server.call_tool(tool_name, args)
                rendered = str(caught.exception)
                self.assertIn('MANAGED_SAVE_REFUSED', rendered)
                self.assertNotIn('CONFIDENTIAL_CANARY', rendered)
                self.assertNotIn('Traceback', rendered)

    async def test_operation_guard_intercepts_save_calls(self):
        for fail_at in (1, 2):
            with self.subTest(fail_at=fail_at):
                calls, servers = [], []
                def guard():
                    calls.append('guard')
                    if len([x for x in calls if x == 'guard']) == fail_at:
                        raise ValueError('PRIVATE_GUARD_CANARY')

                with patch('chat_recall_http._RedactedServer', side_effect=lambda *a, **kw: servers.append(_RedactedServer(*a, **kw)) or servers[-1]):
                    app = create_app(self.fixture.args[0], self.fixture.args[1], self.fixture.args[2],
                                     'https://bridge.example', 'synthetic-client',
                                     'https://client.example/callback', 's' * 43,
                                     operation_guard=guard, enable_chat_save=True)
                server = servers[0]
                with self.assertRaises(ToolError) as caught:
                    await server.call_tool('save_chat_memory', {'title': 'Guard test', 'text': 'Some text'})
                app.state.owner_cleanup()
                rendered = str(caught.exception)
                self.assertIn('MANAGED_SAVE_REFUSED', rendered)
                self.assertNotIn('PRIVATE_GUARD_CANARY', rendered)


class ChatSaveHTTPTransportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.fixture = fixtures.ManagedMemoryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

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

    async def authorize_token(self, app):
        import base64
        import re
        from urllib.parse import urlsplit

        client_id = 'synthetic-client'
        callback = 'https://client.example/callback'
        secret = 's' * 43

        verifier = 'v' * 43
        challenge = hashlib.sha256(verifier.encode('ascii')).digest()
        challenge_b64 = base64.urlsafe_b64encode(challenge).decode('ascii').rstrip('=')

        auth_query = urlencode({
            'client_id': client_id, 'redirect_uri': callback, 'response_type': 'code',
            'scope': 'memory:read', 'state': 'xyzstate123', 'code_challenge': challenge_b64,
            'code_challenge_method': 'S256', 'resource': 'https://bridge.example/mcp'
        }).encode('ascii')

        status, headers, _ = await self.request(app, '/authorize', query=auth_query)
        self.assertEqual(status, 302)
        location = headers[b'location'].decode('ascii')
        ticket = location.rsplit('=', 1)[-1]

        # GET /consent to get CSRF token and cookie
        status, consent_headers, page = await self.request(app, '/consent', query=urlsplit(location).query.encode('ascii'))
        self.assertEqual(status, 200)
        csrf = re.search(rb'name="csrf" value="([^"]+)"', page).group(1).decode('ascii')

        # POST /consent with credentials and cookie
        consent_form = urlencode({'ticket': ticket, 'csrf': csrf, 'owner_code': secret}).encode('ascii')
        post_headers = [
            (b'origin', b'https://bridge.example'),
            (b'content-type', b'application/x-www-form-urlencoded'),
            (b'cookie', f'brain_csrf={csrf}'.encode('ascii'))
        ]
        status, consent_resp_headers, _ = await self.request(app, '/consent', 'POST', consent_form, post_headers)
        self.assertEqual(status, 303)
        callback_url = consent_resp_headers[b'location'].decode('ascii')
        code = parse_qs(urlsplit(callback_url).query)['code'][0]

        # POST /token
        token_form = urlencode({
            'grant_type': 'authorization_code', 'client_id': client_id,
            'redirect_uri': callback, 'code': code,
            'code_verifier': verifier, 'resource': 'https://bridge.example/mcp'
        }).encode('ascii')
        token_headers = [(b'content-type', b'application/x-www-form-urlencoded')]
        status, _, data = await self.request(app, '/token', 'POST', token_form, token_headers)
        self.assertEqual(status, 200)
        token_info = json.loads(data.decode('utf-8'))
        return token_info['access_token']

    async def test_full_mcp_chat_save_roundtrip(self):
        app = create_app(self.fixture.args[0], self.fixture.args[1], self.fixture.args[2],
                         'https://bridge.example', 'synthetic-client',
                         'https://client.example/callback', 's' * 43,
                         enable_chat_save=True)
        self.addCleanup(app.state.owner_cleanup)

        async with app.router.lifespan_context(app):
            token = await self.authorize_token(app)
            mcp_headers = [
                (b'origin', b'https://bridge.example'),
                (b'authorization', f'Bearer {token}'.encode('ascii')),
                (b'content-type', b'application/json'),
                (b'accept', b'application/json, text/event-stream'),
                (b'mcp-protocol-version', b'2025-03-26'),
            ]

            # 1. tools/list includes save_chat_memory and save_memory
            list_req = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}
            status, _, body = await self.request(app, '/mcp', 'POST', json.dumps(list_req).encode(), mcp_headers)
            self.assertEqual(status, 200)
            tools = json.loads(body)['result']['tools']
            tool_names = {t['name'] for t in tools}
            self.assertIn('save_chat_memory', tool_names)
            self.assertIn('save_memory', tool_names)
            self.assertIn('search_managed_memory', tool_names)
            self.assertIn('read_managed_memory', tool_names)

            # 2. tools/call save_chat_memory
            save_req = {
                'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
                'params': {
                    'name': 'save_chat_memory',
                    'arguments': {
                        'title': 'Event streaming pipeline design',
                        'text': 'We adopted Server-Sent Events for one-way stream updates to ChatGPT clients.',
                        'tags': ['sse', 'streaming', 'architecture'],
                        'metadata': {'version': '2.0'}
                    }
                }
            }
            status, _, body = await self.request(app, '/mcp', 'POST', json.dumps(save_req).encode(), mcp_headers)
            self.assertEqual(status, 200)
            res = json.loads(body)['result']
            payload = res.get('structuredContent') or json.loads(res['content'][0]['text'])
            self.assertEqual(payload['status'], 'STAGED')
            self.assertEqual(payload['proposals'], 1)
            self.assertEqual(payload['title'], 'Event streaming pipeline design')

            # 3. Duplicate tools/call -> DUPLICATE_SOURCE
            status, _, body = await self.request(app, '/mcp', 'POST', json.dumps(save_req).encode(), mcp_headers)
            self.assertEqual(status, 200)
            res_dup = json.loads(body)['result']
            payload_dup = res_dup.get('structuredContent') or json.loads(res_dup['content'][0]['text'])
            self.assertEqual(payload_dup['status'], 'DUPLICATE_SOURCE')
            self.assertEqual(payload_dup['proposals'], 0)

            # 4. tools/call save_chat_memory with invalid input -> MANAGED_SAVE_REFUSED
            bad_req = {
                'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call',
                'params': {
                    'name': 'save_chat_memory',
                    'arguments': {'title': '../traversal/attempt', 'text': 'safe text'}
                }
            }
            status, _, body = await self.request(app, '/mcp', 'POST', json.dumps(bad_req).encode(), mcp_headers)
            self.assertEqual(status, 200)
            body_text = body.decode()
            self.assertIn('MANAGED_SAVE_REFUSED', body_text)
            self.assertNotIn('traversal/attempt', body_text)


if __name__ == '__main__':
    unittest.main()
