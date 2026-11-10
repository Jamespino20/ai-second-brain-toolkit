"""Optional real stdio protocol regression. Only temporary synthetic notes are used."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


@unittest.skipUnless(importlib.util.find_spec('mcp'), 'Optional MCP dependency not installed')
class SelectedMemoryProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_allowlist_citations_bounds_and_unchanged_sources(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            vault = base / 'test-vault'
            vault.mkdir()
            note = vault / 'decision.md'
            note.write_bytes(b'---\nprivacy: "synthetic"\n---\n\n# Rehearsal\n\nThe handoff marker is amber-kite.\n')
            (vault / 'excluded.md').write_text('UNSELECTED_CANARY', encoding='utf-8')
            grant = base / 'selected-grant.json'
            grant.write_text(json.dumps({
                'schema': 'selected-memory-readonly-v1', 'source_kind': 'synthetic',
                'client': 'codex-openai', 'root': str(vault),
                'owner_authorization': {'state': 'approved', 'reference': 'synthetic protocol fixture'},
                'notes': [{'id': 'decision', 'path': 'decision.md', 'size': note.stat().st_size,
                           'sha256': hashlib.sha256(note.read_bytes()).hexdigest(),
                           'source_references': ['synthetic://fixture/rehearsal']}]}), encoding='utf-8')
            before = {p: p.read_bytes() for p in base.rglob('*') if p.is_file()}
            environment = {k: v for k, v in os.environ.items() if k.upper() in
                           ('SYSTEMROOT', 'WINDIR', 'PATH', 'TEMP', 'TMP', 'USERPROFILE',
                            'APPDATA', 'LOCALAPPDATA', 'COMSPEC')}
            environment.update(SECOND_BRAIN_GRANT=str(grant),
                               SECOND_BRAIN_GRANT_SHA256=hashlib.sha256(grant.read_bytes()).hexdigest(),
                               SECOND_BRAIN_CLIENT='codex-openai', PYTHONDONTWRITEBYTECODE='1',
                               PYTHONIOENCODING='utf-8')
            server = Path(__file__).resolve().parents[1] / 'scripts' / 'selected_memory_mcp.py'
            parameters = StdioServerParameters(command=sys.executable,
                                               args=['-B', str(server)], env=environment, cwd=str(base))
            cases = [
                ('search_selected_memory', {'query': 'handoff marker'}, False),
                ('read_selected_memory', {'note_id': 'decision', 'start_line': 7, 'line_count': 1}, False),
                ('search_selected_memory', {'query': 'UNSELECTED_CANARY'}, False),
                ('read_selected_memory', {'note_id': 'excluded'}, True),
                ('publish_memory', {'note_id': 'decision'}, True),
                ('read_selected_memory', {'note_id': '../outside.md'}, True),
                ('search_selected_memory', {'query': 'handoff', 'limit': 10}, True),
                ('search_selected_memory', {'query': 'handoff', 'path': 'outside.md'}, False)]
            async with stdio_client(parameters) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    catalog = await session.list_tools()
                    tools = [tool.model_dump(mode='json', by_alias=True) for tool in catalog.tools]
                    self.assertEqual({tool['name'] for tool in tools},
                                     {'search_selected_memory', 'read_selected_memory'})
                    self.assertTrue(all(tool['annotations']['readOnlyHint'] and
                                        not tool['annotations']['destructiveHint'] for tool in tools))
                    for name, arguments, expected_error in cases:
                        with self.subTest(tool=name, arguments=arguments):
                            response = await session.call_tool(name, arguments)
                            value = response.model_dump(mode='json', by_alias=True)
                            self.assertEqual(bool(value.get('isError')), expected_error)
                            if expected_error:
                                continue
                            payload = value.get('structuredContent')
                            if payload is None:
                                payload = json.loads(value['content'][0]['text'])
                            if name == 'search_selected_memory':
                                if arguments['query'] == 'UNSELECTED_CANARY':
                                    self.assertEqual(payload['matches'], [])
                                else:
                                    match = payload['matches'][0]
                                    self.assertEqual(match['path'], 'decision.md')
                                    self.assertEqual(match['line'], 7)
                                    self.assertEqual(match['sha256'], hashlib.sha256(note.read_bytes()).hexdigest())
                                    self.assertEqual(match['source_references'], ['synthetic://fixture/rehearsal'])
                            else:
                                self.assertEqual(payload['lines'], [{'line': 7, 'text': 'The handoff marker is amber-kite.'}])
            self.assertEqual(before, {p: p.read_bytes() for p in base.rglob('*') if p.is_file()})


if __name__ == '__main__':
    unittest.main()
