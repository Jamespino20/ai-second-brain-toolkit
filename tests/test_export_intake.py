import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import import_export as exporter
from migrate import digest, json_bytes


class ExportIntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'private'
        self.root.mkdir()
        (self.root / '.private-staging.json').write_bytes(json_bytes(
            {'live_writes': False, 'external_exports': False}))
        self.source = self.base / 'export.zip'
        self.record = {'id': 'synthetic-session', 'mapping': {'a': {'message': {
            'content': {'parts': ['Synthetic question']},
            'metadata': {'attachments': [{'id': 'file-synthetic'}]}}}}}

    def archive(self, members):
        with zipfile.ZipFile(self.source, 'w') as archive:
            for name, value in members:
                archive.writestr(name, value)

    def test_nested_shards_archive_exact_bytes_and_reconcile_on_replay(self):
        raw = json_bytes([self.record])
        nested = io.BytesIO()
        with zipfile.ZipFile(nested, 'w') as archive:
            archive.writestr('conversations-1.json', raw)
            archive.writestr('attachments/not-fetched.txt', b'PRIVATE_ATTACHMENT_CANARY')
        self.archive([('account.zip', nested.getvalue())])
        before = self.source.read_bytes()
        result = exporter.import_archive(self.source, self.root)
        self.assertEqual(result['conversations'], 1)
        self.assertEqual(result['attachments'], 1)
        self.assertEqual((self.root / 'archive' / (digest(raw) + '.json')).read_bytes(), raw)
        files = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(exporter.import_archive(self.source, self.root), result)
        self.assertEqual(files, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        self.assertEqual(self.source.read_bytes(), before)
        self.assertFalse(any(b'PRIVATE_ATTACHMENT_CANARY' in value for value in files.values()))

    def test_normalized_cache_tamper_is_refused(self):
        self.archive([('conversations.json', json_bytes([self.record]))])
        exporter.import_archive(self.source, self.root)
        target = next((self.root / 'normalized').rglob('*.v1_2.json'))
        record = json.loads(target.read_bytes())
        record['messages'][0]['text'] = 'Changed evidence'
        target.write_bytes(json_bytes(record))
        with self.assertRaises(ValueError):
            exporter.import_archive(self.source, self.root)

    def test_traversal_members_are_refused_without_extraction(self):
        self.archive([('../conversations.json', json_bytes([self.record]))])
        with self.assertRaises(ValueError):
            exporter.import_archive(self.source, self.root)
        self.assertFalse((self.base / 'conversations.json').exists())

    def test_oversized_json_is_refused(self):
        self.archive([('conversations.json', json_bytes([self.record]))])
        with patch.object(exporter, 'MAX_JSON_BYTES', 8), self.assertRaises(ValueError):
            exporter.import_archive(self.source, self.root)

    def test_missing_conversation_data_is_not_success(self):
        self.archive([('unrelated.csv', b'not a conversation')])
        with self.assertRaises(ValueError):
            exporter.import_archive(self.source, self.root)

    def test_duplicate_case_insensitive_source_member_is_refused(self):
        raw = json_bytes([self.record])
        self.archive([('conversations.json', raw), ('CONVERSATIONS.JSON', raw)])
        with self.assertRaisesRegex(ValueError, 'UNSAFE_OR_DUPLICATE_MEMBER'):
            exporter.import_archive(self.source, self.root)

    def test_changed_outer_archive_cannot_receive_success_receipt(self):
        self.archive([('conversations.json', json_bytes([self.record]))])
        with patch.object(exporter, 'file_hash', side_effect=['a' * 64, 'b' * 64]):
            with self.assertRaisesRegex(ValueError, 'SOURCE_CHANGED_DURING_INTAKE'):
                exporter.import_archive(self.source, self.root)
        self.assertFalse((self.root / 'staging/export-intake').exists())

    def test_nested_archive_count_is_bounded(self):
        child = io.BytesIO()
        with zipfile.ZipFile(child, 'w') as archive:
            archive.writestr('unrelated.txt', b'no conversations')
        self.archive([(f'child-{i}.zip', child.getvalue()) for i in range(17)])
        with self.assertRaisesRegex(ValueError, 'NESTED_ARCHIVE_LIMIT'):
            exporter.import_archive(self.source, self.root)


if __name__ == '__main__':
    unittest.main()
