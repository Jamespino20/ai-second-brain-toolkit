import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import migrate as m
from backup import snapshot
from capture_codex import capture


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'private'
        self.root.mkdir()
        (self.root / '.private-staging.json').write_text(json.dumps({'live_writes': False, 'external_exports': False}))
        self.note = {'schema_version': '1.0', 'id': 'demo-decision', 'title': 'Demo decision',
            'kind': 'decision', 'review_state': 'candidate', 'created': '2026-10-19T00:00:00+08:00',
            'updated': '2026-10-19T00:00:00+08:00', 'as_of': None, 'privacy': 'personal',
            'scopes': ['engineering'], 'sources': ['source-1'], 'supersedes': [],
            'external_processing': False, 'claims': [{'text': 'Markdown is canonical',
            'evidence': 'user-stated', 'locator': 'source-1/message-1'}]}

    def tearDown(self):
        self.tmp.cleanup()

    def test_replay_and_revision_preserve_sources(self):
        src = self.root / 'source.json'
        d = {'id': 'session-1', 'title': 'Title', 'mapping': {}, 'create_time': None}
        src.write_text(json.dumps(d))
        m.intake(src, self.root)
        m.intake(src, self.root)
        self.assertEqual(len(list((self.root / 'normalized' / 'session-1').glob('*.json'))), 1)
        d['title'] = 'Revised title'
        src.write_text(json.dumps(d))
        m.intake(src, self.root)
        self.assertEqual(len(list((self.root / 'normalized' / 'session-1').glob('*.json'))), 2)

    def test_unknown_date_not_capture_time_and_branches_retained(self):
        d = {'id': 'branch-test', 'mapping': {'a': {'parent': None, 'message': {'author': {'role': 'user'}, 'content': {'parts': ['One']}}},
            'b': {'parent': 'a', 'message': {'author': {'role': 'assistant'}, 'content': {'parts': ['Two']}}},
            'c': {'parent': 'a', 'message': {'author': {'role': 'assistant'}, 'content': {'parts': ['Alternate']}}}}, 'current_node': 'b'}
        result = list(m.normalize(d))[0]
        self.assertIsNone(result['original_date'])
        self.assertEqual([x['on_current_branch'] for x in result['messages']], [True, True, False])
        self.assertTrue(all(x['date'] is None for x in result['messages']))

    def test_placeholder_is_unavailable(self):
        d = {'thread': {'id': 't'}, 'turns': [{'items': [{'type': 'agentMessage', 'text': '::chatgpt-content-reference{index="0"}'}]}]}
        self.assertTrue(list(m.normalize(d))[0]['messages'][0]['unavailable'])

    def test_truncation_marker_preserved(self):
        d = {'thread': {'id': 't'}, 'turns': [{'items': [{'type': 'agentMessage', 'text': 'Partial answer', 'truncated': True}]}]}
        self.assertTrue(list(m.normalize(d))[0]['messages'][0]['truncated'])

    def test_local_rollout_retains_bytes_but_extracts_dialogue_only(self):
        source = Path(self.tmp.name) / 'rollout.jsonl'
        events = [
            {'type': 'session_meta', 'timestamp': '2026-10-19T00:00:00Z', 'payload': {'id': 'local-session'}},
            {'type': 'response_item', 'timestamp': '2026-10-19T00:01:00Z', 'payload': {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': 'Question'}]}},
            {'type': 'response_item', 'payload': {'type': 'message', 'role': 'system', 'content': [{'type': 'input_text', 'text': 'EXCLUDED_CANARY'}]}},
            {'type': 'response_item', 'timestamp': '2026-10-19T00:02:00Z', 'payload': {'type': 'message', 'role': 'assistant', 'content': [{'type': 'output_text', 'text': 'Answer'}]}}
        ]
        source.write_bytes(('\n'.join(json.dumps(x) for x in events) + '\n').encode())
        result = capture(source, self.root, 'Original title')
        self.assertEqual(result['messages'], 2)
        self.assertEqual((self.root / 'archive' / (result['source_sha256'] + '.jsonl')).read_bytes(), source.read_bytes())
        extracted = Path(result['capture']).read_text(encoding='utf-8')
        self.assertNotIn('EXCLUDED_CANARY', extracted)
        self.assertEqual(result['published'], 0)

    def test_no_overwrite_or_approved_draft(self):
        m.render(self.note, self.root, 'projects/demo/decision.md')
        m.render(self.note, self.root, 'projects/demo/decision.md')
        self.note['claims'][0]['text'] = 'Changed'
        with self.assertRaises(ValueError):
            m.render(self.note, self.root, 'projects/demo/decision.md')
        self.note['review_state'] = 'reviewed'
        with self.assertRaises(ValueError):
            m.render(self.note, self.root, 'projects/demo/other.md')

    def test_live_and_repository_outputs_refused(self):
        with self.assertRaises(FileNotFoundError):
            m.private_root(self.root / 'missing-marker')
        od = self.root / 'OneDrive' / 'AI-Second-Brain'
        od.mkdir(parents=True)
        with self.assertRaises(ValueError):
            m.private_root(od)
        with self.assertRaises(ValueError):
            m.render(self.note, self.root, '../outside.md')
        (self.root / '.git').mkdir()
        with self.assertRaises(ValueError):
            m.private_root(self.root)

    def test_only_allowlisted_notes_indexed_and_stale_refused(self):
        path = Path(m.render(self.note, self.root, 'projects/demo/decision.md'))
        (self.root / 'raw').mkdir()
        (self.root / 'raw' / 'private.txt').write_text('RAW_CANARY')
        self.assertEqual(m.build_index(self.root, ['projects/demo/decision.md']), 1)
        self.assertEqual(m.search(self.root, 'RAW_CANARY'), [])
        self.assertEqual(len(m.search(self.root, 'Markdown')), 1)
        path.write_text(path.read_text() + 'Changed')
        with self.assertRaises(ValueError):
            m.search(self.root, 'Markdown')

    def test_restricted_and_path_escape_not_indexed(self):
        self.note['privacy'] = 'restricted'
        m.render(self.note, self.root, 'restricted.md')
        with self.assertRaises(ValueError):
            m.build_index(self.root, ['restricted.md'])
        with self.assertRaises(ValueError):
            m.build_index(self.root, ['../raw/source.json'])

    def test_backup_restores_hidden_bytes_and_empty_directories(self):
        vault = Path(self.tmp.name) / 'synthetic-vault'
        (vault / '.obsidian').mkdir(parents=True)
        (vault / '.obsidian' / 'app.json').write_bytes(b'{}\r\n')
        (vault / 'empty').mkdir()
        result = snapshot(vault, self.root)
        restored = Path(result['restore_directory'])
        self.assertEqual((restored / '.obsidian' / 'app.json').read_bytes(), b'{}\r\n')
        self.assertTrue((restored / 'empty').is_dir())
        self.assertTrue(result['source_unchanged'])


if __name__ == '__main__':
    unittest.main()
