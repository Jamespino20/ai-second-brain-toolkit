import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from read_memory import search


class ReadMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / 'placement-manifest.json'
        self.notes = []
        for number in range(4):
            path = self.root / 'notes' / f'note-{number}.md'
            path.parent.mkdir(exist_ok=True)
            data = ('---\nprivacy: "personal"\nscopes: ["engineering"]\n---\n\n'
                    f'# Example {number}\n\ncanonical evidence {number}\n\n   Source: fixture/message/{number}\n').encode()
            path.write_bytes(data)
            self.notes.append({'id': f'note-{number}', 'preview_path': str(path),
                               'destination_relative': path.name, 'sha256': hashlib.sha256(data).hexdigest(),
                               'size': len(data), 'content_approval': 'owner-approved', 'publication_state': 'NOT_PUBLISHED'})
        self.value = {'live_publication_authorized': False, 'publication': 'NOT_PUBLISHED', 'notes': self.notes}
        self.pin = self.write_manifest()

    def write_manifest(self):
        self.manifest.write_text(json.dumps(self.value), encoding='utf-8')
        return hashlib.sha256(self.manifest.read_bytes()).hexdigest()

    def test_returns_citations_and_does_not_modify_corpus(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = search(self.manifest, self.pin, 'canonical')
        self.assertEqual(len(result['matches']), 4)
        self.assertEqual(result['matches'][0]['source_references'], ['fixture/message/0'])
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_changed_note_rejects_entire_result_even_when_other_note_matches(self):
        Path(self.notes[-1]['preview_path']).write_text('changed', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'stale retrieval refused'):
            search(self.manifest, self.pin, 'canonical')

    def test_changed_manifest_is_refused(self):
        self.manifest.write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'manifest changed'):
            search(self.manifest, self.pin, 'canonical')

    def test_path_escape_is_refused(self):
        self.notes[0]['destination_relative'] = '../outside.md'
        pin = self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'Invalid selected-note path'):
            search(self.manifest, pin, 'canonical')

    def test_unapproved_is_refused(self):
        self.notes[0]['content_approval'] = 'candidate'
        pin = self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'Unapproved'):
            search(self.manifest, pin, 'canonical')

    def test_out_of_scope_returns_no_notes_and_no_recursive_scan(self):
        (self.root/'secret.md').write_text('unselected secret zebra', encoding='utf-8')
        self.assertEqual(search(self.manifest, self.pin, 'zebra')['matches'], [])


if __name__ == '__main__':
    unittest.main()
