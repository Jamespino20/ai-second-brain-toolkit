"""Real local stdio protocol proof with temporary synthetic notes only."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import test_managed_memory as fixtures


@unittest.skipUnless(importlib.util.find_spec('mcp'), 'Optional MCP dependency not installed')
class ManagedProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_read_small_window_and_explicit_oversize_refusal(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        fixture = fixtures.ManagedMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.note.write_bytes(('---\nprivacy: "synthetic"\n---\n# Long note\n' +
                                  ('x' * 500 + '\n') * 45).encode('utf-8'))
        fixture.manifest['notes'] = [fixture.entry()]
        fixture.publish()
        before = {p: p.read_bytes() for p in fixture.base.rglob('*') if p.is_file()}
        env = {key: value for key, value in os.environ.items() if key.upper() in
               {'SYSTEMROOT', 'WINDIR', 'PATH', 'TEMP', 'TMP', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'COMSPEC'}}
        env.update(SECOND_BRAIN_MANAGED_GRANT=fixture.args[0],
                   SECOND_BRAIN_MANAGED_GRANT_SHA256=fixture.args[1],
                   SECOND_BRAIN_MANAGED_CLIENT=fixture.args[2],
                   PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8')
        server = Path(__file__).resolve().parents[1] / 'scripts/managed_memory_mcp.py'
        params = StdioServerParameters(command=sys.executable, args=['-B', str(server)], env=env,
                                       cwd=str(fixture.base))
        with tempfile.TemporaryFile(mode='w+', encoding='utf-8') as stderr:
            async with stdio_client(params, errlog=stderr) as streams:
                async with ClientSession(*streams) as session:
                    init = await session.initialize()
                    tools = await session.list_tools()
                    read = next(t for t in tools.tools if t.name == 'read_managed_memory')
                    response = await session.call_tool('read_managed_memory', {'note_id': 'decision', 'start_line': 5})
                    value = response.model_dump(mode='json', by_alias=True)
                    self.assertFalse(value.get('isError'))
                    payload = value.get('structuredContent') or json.loads(value['content'][0]['text'])
                    self.assertEqual(len(payload['lines']), 5)
                    self.assertTrue(all(line['text'] == 'x' * 500 for line in payload['lines']))
                    refused = await session.call_tool('read_managed_memory',
                                                      {'note_id': 'decision', 'start_line': 5, 'line_count': 40})
                    self.assertTrue(refused.model_dump(by_alias=True).get('isError'))
                    self.assertIn('MANAGED_RECALL_REFUSED', str(refused.content))
                    self.assertIn('8000', init.instructions)
                    self.assertIn('40', init.instructions)
                    self.assertIn('8000', read.description)
                    self.assertIn('40', read.description)
        self.assertEqual(before, {p: p.read_bytes() for p in fixture.base.rglob('*') if p.is_file()})

    async def test_only_read_tools_citations_redaction_and_no_mutations(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        fixture = fixtures.ManagedMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        before = {p: p.read_bytes() for p in fixture.base.rglob('*') if p.is_file()}
        env = {key: value for key, value in os.environ.items() if key.upper() in
               {'SYSTEMROOT', 'WINDIR', 'PATH', 'TEMP', 'TMP', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'COMSPEC'}}
        env.update(SECOND_BRAIN_MANAGED_GRANT=fixture.args[0],
                   SECOND_BRAIN_MANAGED_GRANT_SHA256=fixture.args[1],
                   SECOND_BRAIN_MANAGED_CLIENT=fixture.args[2],
                   PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8')
        server = Path(__file__).resolve().parents[1] / 'scripts/managed_memory_mcp.py'
        params = StdioServerParameters(command=sys.executable, args=['-B', str(server)],
                                       env=env, cwd=str(fixture.base))
        stderr = tempfile.TemporaryFile(mode='w+', encoding='utf-8')
        self.addCleanup(stderr.close)
        async with stdio_client(params, errlog=stderr) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                catalog = await session.list_tools()
                self.assertEqual({t.name for t in catalog.tools}, {'search_managed_memory', 'read_managed_memory'})
                for tool in catalog.tools:
                    exposed = tool.model_dump(mode='json', by_alias=True)
                    self.assertTrue(exposed['annotations']['readOnlyHint'])
                    self.assertFalse(exposed['annotations']['destructiveHint'])
                    self.assertNotIn('grant_path', exposed['inputSchema']['properties'])
                    self.assertNotIn('path', exposed['inputSchema']['properties'])
                    if tool.name == 'search_managed_memory':
                        self.assertEqual(exposed['inputSchema']['properties']['limit']['maximum'], 4)
                        self.assertEqual(exposed['inputSchema']['properties']['query']['maxLength'], 300)
                    else:
                        self.assertEqual(exposed['inputSchema']['properties']['line_count']['maximum'], 40)
                response = await session.call_tool('search_managed_memory', {'query': 'amber'})
                value = response.model_dump(mode='json', by_alias=True)
                self.assertFalse(value.get('isError'))
                payload = value.get('structuredContent') or json.loads(value['content'][0]['text'])
                self.assertEqual(payload['manifest_generation'], 1)
                self.assertEqual(payload['matches'][0]['note_id'], 'decision')
                response = await session.call_tool('read_managed_memory', {'note_id': 'decision', 'start_line': 7, 'line_count': 1})
                self.assertFalse(response.model_dump(by_alias=True).get('isError'))
                for tool, args in [('read_managed_memory', {'note_id': '../private'}),
                                   ('search_managed_memory', {'query': 'amber', 'limit': True}),
                                   ('publish_memory', {})]:
                    with self.subTest(tool=tool, args=args):
                        response = await session.call_tool(tool, args)
                        self.assertTrue(response.model_dump(by_alias=True).get('isError'))
                for tool, arguments in [
                    ('search_managed_memory', {'query': 'amber', 'limit': 'PRIVATE_INPUT_CANARY'}),
                    ('search_managed_memory', {'query': 'PRIVATE_INPUT_CANARY' * 30}),
                    ('read_managed_memory', {'note_id': 'decision', 'start_line': 'PRIVATE_INPUT_CANARY'}),
                    ('read_managed_memory', {'note_id': 'PRIVATE_INPUT_CANARY' * 10}),
                    ('search_managed_memory', {'query': 'amber', 'limit': str(fixture.base / 'PRIVATE_PATH_CANARY')}),
                    ('PRIVATE_INPUT_CANARY', {})]:
                    with self.subTest(validation=arguments):
                        response = await session.call_tool(tool, arguments)
                        value = response.model_dump(mode='json', by_alias=True)
                        self.assertTrue(value.get('isError'))
                        text = json.dumps(value)
                        self.assertNotIn('PRIVATE_INPUT_CANARY', text)
                        self.assertNotIn('PRIVATE_PATH_CANARY', text)
                        self.assertNotIn(str(fixture.base), text)
                fixture.note.write_text('PRIVATE_CANARY')
                response = await session.call_tool('search_managed_memory', {'query': 'amber'})
                self.assertTrue(response.model_dump(by_alias=True).get('isError'))
                text = str(response.content)
                self.assertNotIn('PRIVATE_CANARY', text)
                self.assertNotIn(str(fixture.base), text)
                fixture.note.write_bytes(before[fixture.note])
                self.assertEqual(before, {p: p.read_bytes() for p in fixture.base.rglob('*') if p.is_file()})
                fixture.manifest['generation'] = 2
                fixture.manifest['notes'][0]['source_references'] = ['CITATION_CANARY' * 1000]
                fixture.publish('two.json')
                oversized_before = {p: p.read_bytes() for p in fixture.base.rglob('*') if p.is_file()}
                for tool, arguments in [('search_managed_memory', {'query': 'amber'}),
                                        ('read_managed_memory', {'note_id': 'decision'})]:
                    response = await session.call_tool(tool, arguments)
                    self.assertTrue(response.model_dump(by_alias=True).get('isError'))
                    self.assertNotIn('CITATION_CANARY', str(response.content))
        self.assertEqual(oversized_before, {p: p.read_bytes() for p in fixture.base.rglob('*') if p.is_file()})
        stderr.seek(0)
        errors = stderr.read()
        self.assertNotIn('PRIVATE_INPUT_CANARY', errors)
        self.assertNotIn('PRIVATE_PATH_CANARY', errors)
        self.assertNotIn(str(fixture.base), errors)


if __name__ == '__main__':
    unittest.main()
