"""Entirely synthetic capture -> publisher -> scoped recall integration."""
import json
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import test_publish_memory as fixtures
from migrate import digest, json_bytes
from save_interactive_memory import stage
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    HAS_MCP = True
except ImportError:
    HAS_MCP = False


@unittest.skipUnless(HAS_MCP, 'Optional MCP dependency unavailable')
class MemoryRoundtripTests(unittest.IsolatedAsyncioTestCase):
    async def test_two_captures_recalled_without_repinning_the_grant(self):
        fixture = fixtures.PublicationTests('test_capture_creates_verified_note_and_committed_manifest')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.assertEqual(fixture.publish()['status'], 'SAVED')
        grant = {'schema': 'brain-managed-read-grant-v1', 'client': 'codex-openai',
                 'source_kind': 'canonical', 'root': str(fixture.vault),
                 'private_root': str(fixture.root), 'policy_path': str(fixture.policy_path),
                 'policy_sha256': fixture.pin,
                 'manifest_pointer': str(fixture.root / 'publications/inert-example/managed/latest.json'),
                 'prefixes': ['logs/brain-save/'], 'note_ids': [],
                 'owner_authorization': {'state': 'approved', 'reference': 'synthetic fixture only',
                                         'purpose': 'synthetic capture/read integration',
                                         'personal_content_external_model_approved': True}}
        grant_path = fixture.root / 'fixture-grant.json'
        grant_path.write_bytes(json_bytes(grant))
        args = (str(grant_path), digest(grant_path.read_bytes()), 'codex-openai')
        env = dict(os.environ, SECOND_BRAIN_MANAGED_GRANT=args[0],
                   SECOND_BRAIN_MANAGED_GRANT_SHA256=args[1], SECOND_BRAIN_MANAGED_CLIENT=args[2],
                   PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8')
        server = Path(__file__).resolve().parents[1] / 'scripts/managed_memory_mcp.py'
        parameters = StdioServerParameters(command=sys.executable, args=['-B', str(server)],
                                          env=env, cwd=str(fixture.project))
        async with stdio_client(parameters) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()

                async def call(name, arguments):
                    response = await session.call_tool(name, arguments)
                    value = response.model_dump(mode='json', by_alias=True)
                    self.assertFalse(value.get('isError'))
                    return value.get('structuredContent') or json.loads(value['content'][0]['text'])

                first = await call('search_managed_memory', {'query': 'Markdown'})
                self.assertEqual(first['manifest_generation'], 1)
                self.assertEqual(len(first['matches']), 1)
                match = first['matches'][0]
                excerpt = await call('read_managed_memory', {'note_id': match['note_id'],
                                                           'start_line': match['line'], 'line_count': 1})
                self.assertIn('Markdown', excerpt['lines'][0]['text'])
                before = grant_path.read_bytes()
                fixture.packet['items'][0]['text'] = 'Keep graph indexes rebuildable.'
                fixture.receipt = stage(fixture.root, fixture.project, fixture.packet,
                                        {'CODEX_THREAD_ID': 'synthetic-roundtrip-2'})
                self.assertEqual(fixture.publish()['status'], 'SAVED')
                second = await call('search_managed_memory', {'query': 'rebuildable'})
                self.assertEqual(second['manifest_generation'], 2)
                self.assertEqual(len(second['matches']), 1)
                self.assertEqual(second['selected_note_count'], 2)
                self.assertEqual(grant_path.read_bytes(), before)
        pointer_path = Path(grant['manifest_pointer'])
        pointer = json.loads(pointer_path.read_bytes())
        manifest_path = pointer_path.parent / pointer['manifest']
        self.assertEqual(digest(manifest_path.read_bytes()), pointer['sha256'])


if __name__ == '__main__':
    unittest.main()
