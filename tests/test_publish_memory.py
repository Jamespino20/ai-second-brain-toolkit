import json
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import publish_memory as publisher
from migrate import digest, json_bytes
from save_interactive_memory import stage


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.root, self.vault, self.project = base / 'private', base / 'test-vault', base / 'project'
        for directory in (self.root, self.vault, self.project):
            directory.mkdir()
        self.root, self.vault, self.project = self.root.resolve(), self.vault.resolve(), self.project.resolve()
        (self.root / '.private-staging.json').write_bytes(json_bytes(
            {'live_writes': False, 'external_exports': False}))
        self.policy = json.loads((Path(__file__).resolve().parents[1] /
                                  'examples/brain-publication-policy.example.json').read_bytes())
        self.policy.update(enabled=True, vault_root=str(self.vault))
        self.policy['owner_authorization'] = {'state': 'approved', 'reference': 'synthetic fixture only'}
        self.policy_path = self.root / 'publication-policy.json'
        self.pin_policy()
        self.packet = {'schema': 'brain-save-context-v1', 'role': 'implementer',
                       'coverage': 'visible-context', 'artifacts': [], 'items': [{
                           'kind': 'decision', 'text': 'Keep canonical knowledge in Markdown.',
                           'status': 'reported-completed', 'actor': 'this-session',
                           'support': 'visible-user-message', 'references': ['synthetic request']}]}
        self.receipt = stage(self.root, self.project, self.packet, {'CODEX_THREAD_ID': 'synthetic-publication'})

    def pin_policy(self):
        self.policy_path.write_bytes(json_bytes(self.policy))
        self.pin = digest(self.policy_path.read_bytes())

    def publish(self):
        return publisher.publish_staged(self.root, self.receipt, self.policy_path, self.pin)

    def latest(self):
        directory = self.root / 'publications' / self.policy['policy_id'] / 'managed'
        pointer = json.loads((directory / 'latest.json').read_bytes())
        manifest = directory / pointer['manifest']
        self.assertEqual(digest(manifest.read_bytes()), pointer['sha256'])
        return json.loads(manifest.read_bytes())

    def test_capture_creates_verified_note_and_committed_manifest(self):
        unrelated = self.vault / 'existing.md'
        unrelated.write_bytes(b'Existing owner knowledge\r\n')
        candidate = self.root / self.receipt['candidate']
        original = candidate.read_bytes()
        result = self.publish()
        self.assertEqual(result['status'], 'SAVED')
        self.assertEqual(result['counts'], {'saved': 1, 'updated': 0, 'linked': 0, 'skipped': 0, 'quarantined': 0})
        self.assertEqual(result['sync_status'], 'UNVERIFIED')
        self.assertNotIn(str(self.vault), json.dumps(result))
        note = self.latest()['notes'][0]
        actual = (self.vault / note['path']).read_bytes()
        self.assertEqual(digest(actual), note['sha256'])
        self.assertEqual(len(actual), note['size'])
        self.assertIn(b'Keep canonical knowledge in Markdown.', actual)
        self.assertIn(b'external_processing: false', actual)
        self.assertIn(b'review_state: "policy-validated"', actual)
        self.assertEqual(candidate.read_bytes(), original)
        self.assertEqual(unrelated.read_bytes(), b'Existing owner knowledge\r\n')

    def test_duplicate_stage_replays_without_note_or_manifest_mutation(self):
        first = self.publish()
        before = {p: p.read_bytes() for p in self.vault.rglob('*') if p.is_file()}
        generation = self.latest()['generation']
        self.receipt = stage(self.root, self.project, self.packet, {'CODEX_THREAD_ID': 'synthetic-publication'})
        self.assertEqual(self.receipt['status'], 'DUPLICATE_SOURCE')
        again = self.publish()
        self.assertEqual(again['status'], 'NO_CHANGE')
        self.assertEqual(again['transaction_id'], first['transaction_id'])
        self.assertEqual(again['counts']['saved'], 0)
        self.assertEqual(self.latest()['generation'], generation)
        self.assertEqual(before, {p: p.read_bytes() for p in self.vault.rglob('*') if p.is_file()})

    def test_disabled_changed_revoked_and_out_of_scope_policy_cannot_write(self):
        self.policy['enabled'] = False
        self.pin_policy()
        self.assertEqual(self.publish()['status'], 'DISABLED')
        self.policy['enabled'] = True
        self.policy_path.write_bytes(json_bytes(self.policy))
        with self.assertRaises(ValueError):
            self.publish()
        self.policy['owner_authorization']['state'] = 'revoked'
        self.pin_policy()
        with self.assertRaises(ValueError):
            self.publish()
        self.policy['owner_authorization']['state'] = 'approved'
        self.policy['write_scope']['create_prefixes'] = ['projects/']
        self.pin_policy()
        with self.assertRaises(ValueError):
            self.publish()
        self.assertEqual(list(self.vault.rglob('*.md')), [])

    def test_changed_staged_candidate_is_refused_before_canonical_write(self):
        candidate = self.root / self.receipt['candidate']
        record = json.loads(candidate.read_bytes())
        record['claims'][0]['text'] = 'Changed evidence'
        candidate.write_bytes(json_bytes(record))
        with self.assertRaises(ValueError):
            self.publish()
        self.assertEqual(list(self.vault.rglob('*.md')), [])

    def test_documented_keyword_interface(self):
        result = publisher.publish_staged(private_root=self.root, staged_receipt=self.receipt,
                                          policy_path=self.policy_path, policy_sha256=self.pin)
        self.assertEqual(result['status'], 'SAVED')

    def test_empty_create_prefix_cannot_expand_scope(self):
        self.policy['write_scope']['create_prefixes'] = ['']
        self.pin_policy()
        with self.assertRaises(ValueError):
            self.publish()
        self.assertEqual(list(self.vault.rglob('*.md')), [])

    def test_repository_vault_is_refused(self):
        (self.vault / '.git').mkdir()
        with self.assertRaises(ValueError):
            self.publish()
        self.assertEqual(list(self.vault.rglob('*.md')), [])

    def test_forged_empty_receipt_does_not_hide_meaningful_source(self):
        folder = self.root / Path(self.receipt['candidate']).parent
        path = folder / 'receipt.json'
        record = json.loads(path.read_bytes())
        record.update(proposals=0, status='NO_MEANINGFUL_OUTCOMES')
        path.write_bytes(json_bytes(record))
        with self.assertRaises(ValueError):
            self.publish()

    def test_unknown_repinned_policy_schema_is_refused(self):
        self.policy['schema'] = 'unsupported-policy-v2'
        self.pin_policy()
        with self.assertRaises(ValueError):
            self.publish()
        self.assertEqual(list(self.vault.rglob('*.md')), [])

    def test_identical_concurrent_bytes_are_not_counted_as_our_write(self):
        primitive = 'rename' if os.name == 'nt' else 'link'
        original = getattr(os, primitive)

        def collision(source, target):
            target = Path(target)
            if target.is_relative_to(self.vault) and target.suffix == '.md':
                subprocess.run([sys.executable, '-B', '-c',
                                'import pathlib,sys; pathlib.Path(sys.argv[2]).open("xb").write(pathlib.Path(sys.argv[1]).read_bytes())',
                                str(source), str(target)], check=True, capture_output=True)
            return original(source, target)

        with patch.object(publisher.os, primitive, side_effect=collision):
            result = self.publish()
        self.assertEqual(result['counts']['saved'], 0)
        self.assertEqual(result['status'], 'QUARANTINED')

    def test_later_capture_appends_manifest_and_replay_preserves_owner_edit(self):
        self.publish()
        first = self.latest()['notes'][0]
        self.packet['items'][0]['text'] = 'Keep graph indexes rebuildable.'
        self.receipt = stage(self.root, self.project, self.packet, {'CODEX_THREAD_ID': 'synthetic-publication-2'})
        self.assertEqual(self.publish()['status'], 'SAVED')
        manifest = self.latest()
        self.assertEqual(manifest['generation'], 2)
        self.assertIn(first, manifest['notes'])
        second = manifest['notes'][1]
        target = self.vault / second['path']
        target.write_bytes(b'Later canonical owner edit')
        self.assertEqual(self.publish()['status'], 'QUARANTINED')
        self.assertEqual(target.read_bytes(), b'Later canonical owner edit')

    def test_independent_writer_wins_without_being_overwritten(self):
        original_write = publisher.write_immutable
        collision = []

        def competing_write(target, data):
            target = Path(target)
            if target.is_relative_to(self.vault) and target.suffix == '.md':
                subprocess.run([sys.executable, '-B', '-c',
                                'import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.parent.mkdir(parents=True,exist_ok=True); p.open("xb").write(b"Concurrent owner note")',
                                str(target)], check=True, capture_output=True)
                collision.append(target)
            return original_write(target, data)

        with patch.object(publisher, 'write_immutable', side_effect=competing_write):
            result = self.publish()
        self.assertEqual(result['status'], 'QUARANTINED')
        self.assertEqual(result['counts']['saved'], 0)
        self.assertEqual(collision[0].read_bytes(), b'Concurrent owner note')

    def test_interrupted_manifest_commit_reports_partial_then_recovers(self):
        original_write = publisher.write_immutable

        def fail_manifest(path, data):
            if Path(path).name.endswith('.manifest.json'):
                raise OSError('synthetic interrupted write')
            return original_write(path, data)

        with patch.object(publisher, 'write_immutable', side_effect=fail_manifest):
            result = self.publish()
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual(result['counts']['saved'], 1)
        before = {p: p.read_bytes() for p in self.vault.rglob('*.md')}
        recovered = self.publish()
        self.assertEqual(recovered['status'], 'SAVED')
        self.assertEqual(recovered['counts']['saved'], 0)
        self.assertEqual(len(self.latest()['notes']), 1)
        self.assertEqual(before, {p: p.read_bytes() for p in self.vault.rglob('*.md')})

    def test_recovery_preserves_owner_edits_after_partial_write(self):
        original_write = publisher.write_immutable

        def fail_manifest(path, data):
            if Path(path).name.endswith('.manifest.json'):
                raise OSError('synthetic interrupted write')
            return original_write(path, data)

        with patch.object(publisher, 'write_immutable', side_effect=fail_manifest):
            self.publish()
        note = next(self.vault.rglob('*.md'))
        note.write_bytes(b'Later owner edit')
        result = self.publish()
        self.assertEqual(result['status'], 'QUARANTINED')
        self.assertEqual(note.read_bytes(), b'Later owner edit')

    def test_growing_file_is_bounded_after_stat(self):
        fake = SimpleNamespace(stat=lambda: SimpleNamespace(st_size=1),
                               read_bytes=lambda: b'x' * 100,
                               open=lambda mode: io.BytesIO(b'x' * 100))
        with patch.object(publisher, 'checked_path', return_value=fake), self.assertRaises(ValueError):
            publisher.read_bytes(self.root / 'growing-file', limit=8)

    def test_capacity_is_checked_before_new_note_installation(self):
        self.policy['limits']['max_managed_notes'] = 1
        self.pin_policy()
        self.publish()
        before = {p: p.read_bytes() for p in self.vault.rglob('*.md')}
        self.packet['items'][0]['text'] = 'A second distinct synthetic decision.'
        self.receipt = stage(self.root, self.project, self.packet, {'CODEX_THREAD_ID': 'capacity-2'})
        result = self.publish()
        self.assertEqual(result['status'], 'QUARANTINED')
        self.assertEqual(result['counts']['saved'], 0)
        self.assertEqual(before, {p: p.read_bytes() for p in self.vault.rglob('*.md')})

    def test_missing_completion_receipt_does_not_recreate_owner_deleted_enrolled_note(self):
        outcome = self.publish()
        transaction = self.root / 'publications' / self.policy['policy_id'] / 'transactions' / outcome['transaction_id']
        (transaction / 'receipt.json').unlink()
        note = self.vault / self.latest()['notes'][0]['path']
        note.unlink()
        result = self.publish()
        self.assertEqual(result['status'], 'QUARANTINED')
        self.assertFalse(note.exists())

    def test_intervening_capture_does_not_permanently_block_partial_recovery(self):
        original_receipt = self.receipt
        with patch.object(publisher, 'replace_pointer', side_effect=OSError('synthetic pointer interruption')):
            self.assertEqual(self.publish()['status'], 'PARTIAL')
        self.packet['items'][0]['text'] = 'A different capture commits while the first awaits recovery.'
        self.receipt = stage(self.root, self.project, self.packet, {'CODEX_THREAD_ID': 'intervening-capture'})
        self.assertEqual(self.publish()['status'], 'SAVED')
        self.assertEqual(len(self.latest()['notes']), 1)
        before = {p: p.read_bytes() for p in self.vault.rglob('*.md')}
        self.receipt = original_receipt
        recovered = self.publish()
        self.assertEqual(recovered['status'], 'SAVED')
        self.assertEqual(recovered['counts']['saved'], 0)
        self.assertEqual(self.latest()['generation'], 2)
        self.assertEqual(len(self.latest()['notes']), 2)
        self.assertEqual(before, {p: p.read_bytes() for p in self.vault.rglob('*.md')})
        self.assertEqual(self.publish()['status'], 'NO_CHANGE')


if __name__ == '__main__':
    unittest.main()
