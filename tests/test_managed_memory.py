"""Managed recall fixtures are disposable synthetic data, including canonical labels."""
import copy
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import managed_memory as reader
from selected_memory import digest


class ManagedMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'test-vault'
        self.root.mkdir()
        self.private = self.base / 'private'
        self.private.mkdir()
        self.write(self.private / '.private-staging.json', {'live_writes': False, 'external_exports': False})
        self.note = self.root / 'logs/brain-save/decision.md'
        self.note.parent.mkdir(parents=True)
        self.note.write_bytes(b'---\nprivacy: "synthetic"\n---\n\n# Decision\n\nThe marker is amber-kite.\n')
        self.policy_path = self.private / 'policy.json'
        self.policy = {'schema': 'brain-publication-policy-v1', 'policy_id': 'fixture',
                       'enabled': True, 'vault_root': str(self.root),
                       'owner_authorization': {'state': 'approved', 'reference': 'synthetic fixture'},
                       'limits': {'max_managed_notes': 256, 'max_note_bytes': 128000}}
        self.write(self.policy_path, self.policy)
        self.managed = self.private / 'publications/fixture/managed'
        self.pointer = self.managed / 'latest.json'
        self.manifest = {'schema': 'brain-managed-manifest-v1', 'policy_id': 'fixture',
                         'policy_sha256': digest(self.policy_path.read_bytes()), 'generation': 1,
                         'transaction_id': 'synthetic-transaction', 'notes': [self.entry()]}
        self.publish()
        self.grant_path = self.private / 'grant.json'
        self.grant = {'schema': 'brain-managed-read-grant-v1', 'client': 'codex-openai',
                      'source_kind': 'synthetic', 'root': str(self.root), 'private_root': str(self.private),
                      'policy_path': str(self.policy_path), 'policy_sha256': digest(self.policy_path.read_bytes()),
                      'manifest_pointer': str(self.pointer), 'prefixes': ['logs/brain-save/'], 'note_ids': [],
                      'owner_authorization': {'state': 'approved', 'reference': 'synthetic fixture',
                                              'purpose': 'synthetic recall',
                                              'personal_content_external_model_approved': False}}
        self.pin()

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding='utf-8')

    def entry(self):
        return {'id': 'decision', 'path': 'logs/brain-save/decision.md',
                'sha256': digest(self.note.read_bytes()), 'size': self.note.stat().st_size,
                'privacy': 'synthetic', 'external_processing': False,
                'source_references': ['synthetic://fixture/source']}

    def publish(self, name='generation.json'):
        target = self.managed / name
        self.write(target, self.manifest)
        self.write(self.pointer, {'manifest': name, 'sha256': digest(target.read_bytes())})

    def pin(self):
        self.write(self.grant_path, self.grant)
        self.args = (str(self.grant_path), digest(self.grant_path.read_bytes()), 'codex-openai')

    def test_search_read_citations_and_no_mutation(self):
        before = {p: p.read_bytes() for p in self.base.rglob('*') if p.is_file()}
        result = reader.search_managed(*self.args, 'amber')
        self.assertEqual(result['manifest_generation'], 1)
        self.assertEqual(result['mode'], 'managed-read-only-markdown')
        match = result['matches'][0]
        self.assertEqual(match['note_id'], 'decision')
        self.assertEqual(match['source_references'], ['synthetic://fixture/source'])
        self.assertEqual(match['line'], 7)
        result = reader.read_managed(*self.args, 'decision', 7, 1)
        self.assertEqual(result['lines'], [{'line': 7, 'text': 'The marker is amber-kite.'}])
        self.assertEqual(before, {p: p.read_bytes() for p in self.base.rglob('*') if p.is_file()})

    def test_scope_excludes_unmanaged_and_other_prefix(self):
        (self.root / 'unmanaged.md').write_text('CANARY')
        self.grant['prefixes'] = ['projects/']
        self.pin()
        self.assertEqual(reader.search_managed(*self.args, 'amber')['matches'], [])
        with self.assertRaises(ValueError):
            reader.read_managed(*self.args, 'decision')
        self.grant['note_ids'] = ['decision']
        self.pin()
        self.assertEqual(len(reader.search_managed(*self.args, 'amber')['matches']), 1)

    def test_stale_note_and_changed_pins_refused(self):
        self.note.write_text('CHANGED_CANARY')
        with self.assertRaises(ValueError):
            reader.search_managed(*self.args, 'amber')
        self.grant_path.write_text('{}')
        with self.assertRaises(ValueError):
            reader.search_managed(*self.args, 'amber')

    def test_disabled_or_unapproved_policy_refused(self):
        for field, value in [('enabled', False), ('owner_authorization', {'state': 'revoked', 'reference': 'x'})]:
            with self.subTest(field=field):
                policy = copy.deepcopy(self.policy)
                policy[field] = value
                self.write(self.policy_path, policy)
                self.grant['policy_sha256'] = digest(self.policy_path.read_bytes())
                self.manifest['policy_sha256'] = self.grant['policy_sha256']
                self.publish()
                self.pin()
                with self.assertRaises(ValueError):
                    reader.search_managed(*self.args, 'amber')

    def test_invalid_scope_and_client_refused(self):
        for prefixes in [[], ['../'], ['logs'], [''], ['/logs/'], ['logs/../']]:
            self.grant['prefixes'] = prefixes
            self.pin()
            with self.subTest(prefixes=prefixes), self.assertRaises(ValueError):
                reader.search_managed(*self.args, 'amber')
        with self.assertRaises(ValueError):
            reader.search_managed(*self.args[:2], 'claude-anthropic', 'amber')

    def test_canonical_requires_separate_consent(self):
        self.grant['source_kind'] = 'canonical'
        self.note.write_bytes(self.note.read_bytes().replace(b'synthetic', b'personal'))
        self.manifest['notes'] = [{**self.entry(), 'privacy': 'personal'}]
        self.publish()
        self.pin()
        with self.assertRaises(ValueError):
            reader.search_managed(*self.args, 'amber')
        self.grant['owner_authorization']['personal_content_external_model_approved'] = True
        self.pin()
        self.assertEqual(len(reader.search_managed(*self.args, 'amber')['matches']), 1)

    def test_personal_note_cannot_be_read_as_synthetic(self):
        self.note.write_bytes(self.note.read_bytes().replace(b'synthetic', b'personal'))
        self.manifest['notes'] = [self.entry()]
        self.publish()
        with self.assertRaises(ValueError):
            reader.search_managed(*self.args, 'amber')

    def test_rollback_and_same_generation_replacement_refused(self):
        reader.search_managed(*self.args, 'amber')
        self.manifest['transaction_id'] = 'replacement'
        self.publish('other.json')
        with self.assertRaises(ValueError):
            reader.search_managed(*self.args, 'amber')
        self.manifest['generation'] = 2
        self.publish('two.json')
        reader.search_managed(*self.args, 'amber')
        self.manifest['generation'] = 1
        self.publish('old.json')
        with self.assertRaises(ValueError):
            reader.search_managed(*self.args, 'amber')

    def test_pointer_change_during_operation_refused(self):
        original = reader.citation
        def change(*args):
            result = original(*args)
            self.pointer.write_text('{}')
            return result
        with patch.object(reader, 'citation', side_effect=change), self.assertRaises(ValueError):
            reader.search_managed(*self.args, 'amber')

    def test_strict_argument_bounds(self):
        for query, limit in [('', 4), ('a' * 301, 4), (' ' * 301 + 'amber', 4), ('amber', True), ('amber', 5), ([], 1)]:
            with self.subTest(query=query, limit=limit), self.assertRaises(ValueError):
                reader.search_managed(*self.args, query, limit)
        for start, count in [(True, 1), (0, 1), (1, True), (1, 41)]:
            with self.subTest(start=start, count=count), self.assertRaises(ValueError):
                reader.read_managed(*self.args, 'decision', start, count)

    def test_duplicate_synthetic_privacy_property_refused(self):
        self.note.write_bytes(b'---\nprivacy: "personal"\nprivacy: "synthetic"\n---\n# Synthetic\namber\n')
        self.manifest['notes'] = [self.entry()]
        self.publish()
        with self.assertRaises(ValueError):
            reader.search_managed(*self.args, 'amber')

    def test_malformed_configuration_raises_value_error(self):
        self.grant.pop('root')
        self.pin()
        with self.assertRaises(ValueError):
            reader.search_managed(*self.args, 'amber')

    def test_new_published_generation_needs_no_new_grant_pin(self):
        reader.search_managed(*self.args, 'amber')
        second = self.root / 'logs/brain-save/second.md'
        second.write_bytes(b'---\nprivacy: "synthetic"\n---\n# New\nblue-jay\n')
        self.manifest['notes'].append({**self.entry(), 'id': 'second', 'path': 'logs/brain-save/second.md',
                                       'size': second.stat().st_size, 'sha256': digest(second.read_bytes())})
        self.manifest['generation'] = 2
        self.publish('two.json')
        result = reader.search_managed(*self.args, 'blue-jay')
        self.assertEqual(result['matches'][0]['note_id'], 'second')
        self.assertEqual(result['manifest_generation'], 2)

    def test_manifest_paths_duplicates_and_hashes_refused(self):
        original = copy.deepcopy(self.manifest)
        for change in ['escape', 'case-duplicate', 'wrong-hash', 'bool-size', 'oversize']:
            self.manifest = copy.deepcopy(original)
            note = self.manifest['notes'][0]
            if change == 'escape':
                note['path'] = '../outside.md'
            elif change == 'case-duplicate':
                self.manifest['notes'].append({**note, 'id': 'other', 'path': 'logs/brain-save/Decision.md'})
            elif change == 'wrong-hash':
                note['sha256'] = '0' * 64
            elif change == 'bool-size':
                note['size'] = True
            else:
                note['size'] = 128001
            self.publish()
            with self.subTest(change=change), self.assertRaises(ValueError):
                reader.search_managed(*self.args, 'amber')

    def test_pointer_escape_and_wrong_hash_refused(self):
        for pointer in [{'manifest': '../outside.json', 'sha256': '0' * 64},
                        {'manifest': 'generation.json', 'sha256': '0' * 64}]:
            self.write(self.pointer, pointer)
            with self.subTest(pointer=pointer), self.assertRaises(ValueError):
                reader.search_managed(*self.args, 'amber')

    def test_grant_policy_changes_during_read_refused(self):
        original = reader.citation
        for path in [self.grant_path, self.policy_path]:
            before = path.read_bytes()
            def change(*args):
                result = original(*args)
                path.write_text('{}')
                return result
            with self.subTest(path=path.name), patch.object(reader, 'citation', side_effect=change), self.assertRaises(ValueError):
                reader.read_managed(*self.args, 'decision')
            path.write_bytes(before)

    def test_hardlinked_note_refused(self):
        other = self.base / 'other.md'
        os.link(self.note, other)
        with self.assertRaises(ValueError):
            reader.search_managed(*self.args, 'amber')

    def test_long_read_and_search_lines_refused(self):
        self.note.write_bytes(b'---\nprivacy: "synthetic"\n---\n# Decision\n' + b'amber' * 1601 + b'\n')
        self.manifest['notes'] = [self.entry()]
        self.publish()
        with self.assertRaises(ValueError):
            reader.read_managed(*self.args, 'decision', 5, 1)
        with self.assertRaises(ValueError):
            reader.search_managed(*self.args, 'amber')

    def test_concurrent_same_generation_reads_are_consistent(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: reader.search_managed(*self.args, 'amber'), range(8)))
        self.assertTrue(all(value['manifest_generation'] == 1 for value in results))

    def test_citation_references_over_bounds_refused_without_truncation(self):
        for refs in [['x' * 50000], ['a'] * 9, ['x' * 513], ['x' * 512] * 5, ['C:\\leaked\\note.md'], ['/etc/passwd'], ['notes/../../secret']]:
            self.manifest['generation'] += 1
            self.manifest['notes'][0]['source_references'] = refs
            self.publish()
            with self.subTest(lengths=[len(value) for value in refs]):
                with self.assertRaises(ValueError):
                    reader.search_managed(*self.args, 'amber')
                with self.assertRaises(ValueError):
                    reader.read_managed(*self.args, 'decision')

    def test_citation_references_at_bounds_retained_exactly(self):
        refs = ['x' * 512] * 4
        self.manifest['notes'][0]['source_references'] = refs
        self.publish()
        self.assertEqual(reader.search_managed(*self.args, 'amber')['matches'][0]['source_references'], refs)


if __name__ == '__main__':
    unittest.main()
