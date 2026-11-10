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

    def test_export_preserves_attachment_metadata_and_structured_source_pointers(self):
        attachment = {'id': 'file-example', 'name': 'example.pdf', 'extra': {'unknown': True}}
        part = {'content_type': 'image_asset_pointer', 'asset_pointer': 'file-service://example'}
        data = [{'id': 'media-session', 'current_node': 'node/~1', 'mapping': {
            'node/~1': {'parent': None, 'message': {'id': 'message-1',
                'author': {'role': 'user'}, 'create_time': None,
                'content': {'content_type': 'multimodal_text', 'parts': ['Question', part]},
                'metadata': {'attachments': [attachment, {}]}}}}}]
        original = json.dumps(data, sort_keys=True)
        result = list(m.normalize(data))[0]
        message = result['messages'][0]
        self.assertEqual(message['text'], 'Question')
        self.assertEqual(message['structured_parts'], [{
            'source_locator': '#/0/mapping/node~1~01/message/content/parts/1',
            'content_type': 'image_asset_pointer', 'status': 'not-loaded'}])
        self.assertEqual(result['source_locator'], '#/0')
        self.assertEqual(result['attachments'][0]['metadata'], attachment)
        self.assertEqual(result['attachments'][0]['node_id'], 'node/~1')
        self.assertEqual(result['attachments'][0]['source_locator'],
                         '#/0/mapping/node~1~01/message/metadata/attachments/0')
        self.assertTrue(all(x['status'] == 'not-loaded' for x in result['attachments']))
        self.assertEqual(result['attachments'][1]['metadata'], {})
        self.assertEqual(message['content_coverage'], 'text-with-unloaded-content')
        self.assertIsNone(message['date'])
        self.assertTrue(message['on_current_branch'])
        self.assertEqual(json.dumps(data, sort_keys=True), original)

    def test_export_unknown_nontext_content_is_explicitly_unloaded(self):
        data = {'id': 'unknown-media', 'mapping': {'a': {'parent': None, 'message': {
            'author': {'role': 'assistant'}, 'content': {'content_type': 'future-format'},
            'metadata': None}}}, 'current_node': 'a'}
        message = list(m.normalize(data))[0]['messages'][0]
        self.assertEqual(message['text'], '')
        self.assertEqual(message['content_reference'], {
            'source_locator': '#/mapping/a/message/content',
            'content_type': 'future-format', 'status': 'not-loaded'})
        self.assertEqual(message['content_coverage'], 'text-with-unloaded-content')

    def test_export_preserves_supported_list_content(self):
        data = {'id': 'list-content', 'mapping': {'a': {'message': {
            'content': [{'text': 'Question'}, {'unknown': True}]}}}}
        message = list(m.normalize(data))[0]['messages'][0]
        self.assertEqual(message['text'], 'Question\n')
        self.assertEqual(message['content_reference']['source_locator'], '#/mapping/a/message/content')
        self.assertEqual(message['content_reference']['status'], 'not-loaded')

    def test_export_unknown_metadata_shape_remains_source_referenced(self):
        data = {'id': 'list-metadata', 'mapping': {'a': {'message': {
            'content': {'parts': ['Question']}, 'metadata': ['unknown']}}}}
        message = list(m.normalize(data))[0]['messages'][0]
        self.assertEqual(message['text'], 'Question')
        self.assertEqual(message['metadata_reference'], {
            'source_locator': '#/mapping/a/message/metadata', 'status': 'not-loaded'})

    def test_export_empty_single_attachment_metadata_is_not_dropped(self):
        data = {'id': 'empty-attachment', 'mapping': {'a': {'message': {
            'content': {'parts': ['Question']}, 'metadata': {'attachments': {}}}}}}
        result = list(m.normalize(data))[0]
        self.assertEqual(len(result['attachments']), 1)
        self.assertEqual(result['attachments'][0]['metadata'], {})
        self.assertEqual(result['attachments'][0]['source_locator'], '#/mapping/a/message/metadata/attachments')
        self.assertEqual(result['messages'][0]['content_coverage'], 'text-with-unloaded-content')

    def test_new_normalization_version_preserves_old_record_and_exact_source(self):
        source = self.root / 'source.json'
        raw = json.dumps({'id': 'versioned', 'mapping': {}}).encode()
        source.write_bytes(raw)
        sha = m.digest(raw)
        old = self.root / 'normalized' / 'versioned' / (sha + '.v1_1.json')
        old.parent.mkdir(parents=True)
        old.write_bytes(b'legacy-record-bytes')
        m.intake(source, self.root)
        target = old.with_name(sha + '.v1_2.json')
        self.assertTrue(target.exists())
        self.assertEqual(json.loads(target.read_bytes())['normalization_version'], '1.2')
        self.assertEqual(old.read_bytes(), b'legacy-record-bytes')
        self.assertEqual((self.root / 'archive' / (sha + '.json')).read_bytes(), raw)
        before = target.read_bytes()
        m.intake(source, self.root)
        self.assertEqual(target.read_bytes(), before)

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
