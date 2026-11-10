import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from selected_memory import citation, digest, is_safe_source_reference, read_selected, search_selected


class SelectedMemoryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.root = self.base / 'test-vault' / 'synthetic'
        self.root.mkdir(parents=True)
        self.path = self.root / 'decision.md'
        self.path.write_bytes(b'---\nprivacy: "synthetic"\n---\n\n# Rehearsal\n\nThe handoff marker is amber-kite.\n')
        self.manifest = self.base / 'grant.json'
        self.grant = {'schema': 'selected-memory-readonly-v1', 'source_kind': 'synthetic',
                      'client': 'codex-openai', 'root': str(self.root),
                      'owner_authorization': {'state': 'approved', 'reference': 'synthetic-test'},
                      'notes': [{'id': 'decision', 'path': 'decision.md', 'size': self.path.stat().st_size,
                                 'sha256': digest(self.path.read_bytes()), 'source_references': ['synthetic://fixture/1']}]}
        self.pin = self.repin()

    def repin(self):
        self.manifest.write_text(json.dumps(self.grant), encoding='utf-8')
        return digest(self.manifest.read_bytes())

    def search(self, query='handoff', client='codex-openai'):
        return search_selected(self.manifest, self.pin, client, query)

    def test_citations_read_ranges_and_no_writes(self):
        before = {p: p.read_bytes() for p in self.base.rglob('*') if p.is_file()}
        match = self.search()['matches'][0]
        self.assertEqual(match['line'], 7)
        self.assertEqual(match['source_references'], ['synthetic://fixture/1'])
        self.assertIn('obsidian://open?', match['obsidian_uri'])
        result = read_selected(self.manifest, self.pin, 'codex-openai', 'decision', 7, 1)
        self.assertEqual(result['lines'][0]['text'], 'The handoff marker is amber-kite.')
        self.assertEqual(before, {p: p.read_bytes() for p in self.base.rglob('*') if p.is_file()})

    def test_unselected_file_never_read(self):
        (self.root / 'unselected.md').write_text('unselected-zebra', encoding='utf-8')
        self.assertEqual(self.search('unselected-zebra')['matches'], [])

    def test_manifest_tamper_refused(self):
        self.manifest.write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Manifest changed'):
            self.search()

    def test_any_stale_selected_note_refuses_whole_query(self):
        other = self.root / 'other.md'
        other.write_bytes(self.path.read_bytes())
        self.grant['notes'].append({**self.grant['notes'][0], 'id': 'other', 'path': 'other.md'})
        self.pin = self.repin()
        other.write_text('stale unrelated selected note', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'stale retrieval'):
            self.search()

    def test_traversal_absolute_ads_and_backslash_refused(self):
        for path in ('../outside.md', '/outside.md', 'C:/outside.md', 'decision.md:stream.md', 'dir\\decision.md', 'a/./decision.md'):
            with self.subTest(path=path):
                self.grant['notes'][0]['path'] = path
                self.pin = self.repin()
                with self.assertRaisesRegex(ValueError, 'Invalid'):
                    self.search()

    def test_duplicate_case_insensitive_path_refused(self):
        self.grant['notes'].append({**self.grant['notes'][0], 'id': 'other', 'path': 'DECISION.md'})
        self.pin = self.repin()
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.search()

    def test_client_mismatch_refused(self):
        with self.assertRaisesRegex(ValueError, 'Client not authorized'):
            self.search(client='claude-anthropic')

    def test_revoked_grant_refused(self):
        self.grant['owner_authorization']['state'] = 'revoked'
        self.pin = self.repin()
        with self.assertRaisesRegex(ValueError, 'authorization required'):
            self.search()

    def test_live_grant_needs_separate_personal_external_consent(self):
        self.grant['source_kind'] = 'canonical'
        self.pin = self.repin()
        with self.assertRaisesRegex(ValueError, 'Separate personal-content'):
            self.search()

    def test_canonical_mode_reads_in_place_only_with_explicit_grant_using_synthetic_fixture(self):
        self.grant['source_kind'] = 'canonical'
        self.grant['owner_authorization']['personal_content_external_model_approved'] = True
        self.pin = self.repin()
        self.assertEqual(self.search()['matches'][0]['path'], self.grant['notes'][0]['path'])

    def test_personal_material_cannot_be_labeled_synthetic(self):
        self.path.write_bytes(self.path.read_bytes().replace(b'"synthetic"', b'"personal"'))
        self.grant['notes'][0].update(size=self.path.stat().st_size, sha256=digest(self.path.read_bytes()))
        self.pin = self.repin()
        with self.assertRaisesRegex(ValueError, 'refuses personal'):
            self.search()

    def test_hardlink_refused(self):
        linked = self.root / 'linked.md'
        os.link(self.path, linked)
        with self.assertRaisesRegex(ValueError, 'non-hardlinked'):
            self.search()

    def test_unknown_note_and_read_bounds_refused(self):
        with self.assertRaisesRegex(ValueError, 'not authorized'):
            read_selected(self.manifest, self.pin, 'codex-openai', '../outside')
        for start, count in ((0, 1), (1, 41), (99, 1)):
            with self.subTest(start=start, count=count), self.assertRaises(ValueError):
                read_selected(self.manifest, self.pin, 'codex-openai', 'decision', start, count)

    def test_is_safe_source_reference_policy(self):
        valid = ['synthetic://fixture/1', 'synthetic:source', 'fixture/message/0', 'valid_ref-123', 'a' * 512]
        for ref in valid:
            with self.subTest(valid=ref):
                self.assertTrue(is_safe_source_reference(ref))

        invalid = [
            'C:\\Users\\leaked\\path.md', 'c:/Users/leaked/path.md', 'D:notes.md',
            '\\\\server\\share\\note.md', '//server/share/note.md',
            '/root/absolute.md', '\\windows\\system32',
            'notes/../../traversal', '..', 'notes/..',
            'file:///C:/Users/secret.md', 'file://localhost/etc/passwd',
            '', '   ', 'x' * 513, 123, None, ['nested'],
        ]
        for ref in invalid:
            with self.subTest(invalid=ref):
                self.assertFalse(is_safe_source_reference(ref))

    def test_unsafe_source_references_in_grant_refused(self):
        for unsafe in ('C:\\secret.md', '/etc/passwd', 'notes/../../secret', 'file:///c:/secret'):
            with self.subTest(unsafe=unsafe):
                self.grant['notes'][0]['source_references'] = [unsafe]
                self.pin = self.repin()
                with self.assertRaisesRegex(ValueError, 'Invalid'):
                    self.search()

    def test_citation_filters_unsafe_source_references(self):
        note = {
            'id': 'decision', 'path': 'decision.md', 'sha256': 'a' * 64,
            'source_references': ['synthetic://safe/1', 'C:\\leaked\\note.md', '/etc/shadow', 'file:///c:/pass', 'valid://safe/2']
        }
        cite = citation(self.grant, note, self.path)
        self.assertEqual(cite['source_references'], ['synthetic://safe/1', 'valid://safe/2'])


if __name__ == '__main__':
    unittest.main()
