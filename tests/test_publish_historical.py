"""Historical import uses only disposable synthetic data."""
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from publish_historical import publish_historical, validate_historical


def sha(data):
    return hashlib.sha256(data).hexdigest()


class HistoricalTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        self.private = self.base / 'private'
        self.vault = self.base / 'test-vault'
        self.private.mkdir()
        self.vault.mkdir()
        self.write_json('.private-staging.json', {'live_writes': False, 'external_exports': False})
        self.payload = b'---\nid: "one"\nprivacy: "synthetic"\nexternal_processing: false\nsources: ["synthetic:source"]\n---\n# One\n\nSynthetic.\n'
        (self.private / 'note.md').write_bytes(self.payload)
        (self.private / 'review.txt').write_bytes(b'synthetic review')
        self.manifest = {'schema': 'brain-historical-import-v1', 'batch_id': 'batch', 'client': 'codex-openai',
                         'review_evidence': [{'path': 'review.txt', 'size': 16, 'sha256': sha(b'synthetic review')}],
                         'notes': [{'id': 'one', 'source': 'note.md', 'path': 'projects/one.md',
                                    'sha256': sha(self.payload), 'size': len(self.payload), 'privacy': 'synthetic',
                                    'external_processing': False, 'source_references': ['synthetic:source']}]}
        self.authorization = {'schema': 'brain-historical-import-authorization-v1', 'state': 'approved',
                              'reference': 'fixture', 'purpose': 'synthetic', 'client': 'codex-openai',
                              'batch_id': 'batch', 'policy_id': 'historical', 'vault_root': str(self.vault)}
        self.policy = {'schema': 'brain-publication-policy-v1', 'enabled': True, 'policy_id': 'historical',
                       'vault_root': str(self.vault), 'owner_authorization': {'state': 'approved', 'reference': 'fixture'},
                       'limits': {'max_managed_notes': 16, 'max_note_bytes': 128000},
                       'write_scope': {'updates': False, 'bootstrap': False, 'create_prefixes': ['projects/']}}
        self.pin()

    def write_json(self, name, obj):
        data = json.dumps(obj).encode()
        (self.private / name).write_bytes(data)
        return sha(data)

    def pin(self):
        mh = self.write_json('manifest.json', self.manifest)
        self.authorization['manifest_sha256'] = mh
        ah = self.write_json('authorization.json', self.authorization)
        self.policy['historical_import'] = {'batch_id': 'batch', 'client': 'codex-openai',
                                            'manifest_sha256': mh, 'authorization_sha256': ah}
        ph = self.write_json('policy.json', self.policy)
        self.args = (self.private, self.private / 'manifest.json', mh, self.private / 'policy.json', ph,
                     self.private / 'authorization.json', ah)

    def test_validates_without_mutation(self):
        before = {p: p.read_bytes() for p in self.base.rglob('*') if p.is_file()}
        result = validate_historical(*self.args)
        self.assertEqual(result['status'], 'VALID')
        self.assertEqual(result['note_ids'], ['one'])
        self.assertEqual(before, {p: p.read_bytes() for p in self.base.rglob('*') if p.is_file()})

    def test_wrong_pin_and_source_drift_refuse(self):
        args = list(self.args)
        args[2] = '0' * 64
        self.assertEqual(validate_historical(*args)['status'], 'REFUSED')
        (self.private / 'note.md').write_bytes(b'changed')
        self.assertEqual(validate_historical(*self.args)['status'], 'REFUSED')
        self.assertFalse(any(self.vault.iterdir()))

    def test_duplicate_json_and_unapproved_authorization_refuse(self):
        self.authorization['state'] = 'pending'
        self.pin()
        self.assertEqual(validate_historical(*self.args)['status'], 'REFUSED')
        raw = b'{"schema":"one","schema":"two"}'
        (self.private / 'manifest.json').write_bytes(raw)
        args = list(self.args)
        args[2] = sha(raw)
        self.assertEqual(validate_historical(*args)['status'], 'REFUSED')

    def test_invalid_destinations_and_scope_refuse(self):
        for path in ('projects/CON.md', 'projects/../escape.md', 'system/one.md',
                     'projects/name..', 'projects/evil:stream.md', 'other/one.md'):
            with self.subTest(path=path):
                self.manifest['notes'][0]['path'] = path
                self.pin()
                self.assertEqual(validate_historical(*self.args)['status'], 'REFUSED')

    def test_oversized_and_metadata_mismatch_refuse(self):
        self.manifest['notes'][0]['privacy'] = 'personal'
        self.pin()
        self.assertEqual(validate_historical(*self.args)['status'], 'REFUSED')
        self.manifest['notes'][0]['privacy'] = 'synthetic'
        oversized = b'x' * 128001
        (self.private / 'note.md').write_bytes(oversized)
        self.manifest['notes'][0].update(size=len(oversized), sha256=sha(oversized))
        self.pin()
        self.assertEqual(validate_historical(*self.args)['status'], 'REFUSED')

    def test_outside_link_and_unknown_heading_refuse(self):
        for suffix in ('[[projects/outside]]', '[[#Missing]]', '![[projects/one]]', '[x](file.md)'):
            with self.subTest(suffix=suffix):
                data = self.payload + (suffix + '\n').encode()
                (self.private / 'note.md').write_bytes(data)
                self.manifest['notes'][0].update(size=len(data), sha256=sha(data))
                self.pin()
                self.assertEqual(validate_historical(*self.args)['status'], 'REFUSED')

    def test_create_and_exact_replay(self):
        first = publish_historical(*self.args)
        self.assertEqual(first['status'], 'COMPLETED')
        self.assertEqual(first['counts']['saved'], 1)
        self.assertEqual((self.vault / 'projects/one.md').read_bytes(), self.payload)
        replay = publish_historical(*self.args)
        self.assertEqual(replay['status'], 'NO_CHANGE')
        self.assertEqual(replay['counts']['saved'], 0)

    def test_equal_unmanaged_target_is_collision(self):
        target = self.vault / 'projects/one.md'
        target.parent.mkdir()
        target.write_bytes(self.payload)
        result = publish_historical(*self.args)
        self.assertIn(result['status'], ('QUARANTINED', 'REFUSED'))
        self.assertEqual(result['counts']['saved'], 0)
        self.assertEqual(target.read_bytes(), self.payload)

    def test_interruption_after_create_without_positive_marker_never_adopts(self):
        import publish_historical as module
        real_write = module.write_immutable
        def fail_after_create(path, data):
            if path == self.vault / 'projects/one.md':
                real_write(path, data)
                raise OSError('simulated crash after installation')
            return real_write(path, data)
        with patch.object(module, 'write_immutable', side_effect=fail_after_create):
            result = publish_historical(*self.args)
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual(result['counts']['saved'], 0)
        self.assertEqual((self.vault / 'projects/one.md').read_bytes(), self.payload)
        retry = publish_historical(*self.args)
        self.assertNotIn(retry['status'], ('COMPLETED', 'NO_CHANGE'))
        self.assertFalse((self.private / 'publications/historical/managed/latest.json').exists())

    def test_receipt_interruption_recovers_without_new_generation(self):
        import publish_historical as module
        real_write = module.write_immutable
        def fail_receipt(path, data):
            if path.name == 'receipt.json':
                raise OSError('synthetic interruption')
            return real_write(path, data)
        with patch.object(module, 'write_immutable', side_effect=fail_receipt):
            first = publish_historical(*self.args)
        self.assertEqual(first['status'], 'PARTIAL')
        self.assertEqual(first['counts']['saved'], 1)
        pointer = self.private / 'publications/historical/managed/latest.json'
        before = pointer.read_bytes()
        retry = publish_historical(*self.args)
        self.assertEqual(retry['status'], 'COMPLETED')
        self.assertEqual(retry['counts']['saved'], 0)
        self.assertEqual(retry['counts']['recovered'], 1)
        self.assertEqual(pointer.read_bytes(), before)

    def test_later_edit_or_deletion_refuses_replay(self):
        self.assertEqual(publish_historical(*self.args)['status'], 'COMPLETED')
        target = self.vault / 'projects/one.md'
        target.write_bytes(b'owner edit')
        self.assertNotEqual(publish_historical(*self.args)['status'], 'NO_CHANGE')
        self.assertEqual(target.read_bytes(), b'owner edit')
        target.unlink()
        self.assertNotEqual(publish_historical(*self.args)['status'], 'NO_CHANGE')
        self.assertFalse(target.exists())

    def test_published_note_is_searchable_with_separate_synthetic_grant(self):
        import managed_memory
        self.assertEqual(publish_historical(*self.args)['status'], 'COMPLETED')
        grant = {'schema': 'brain-managed-read-grant-v1', 'client': 'codex-openai',
                 'source_kind': 'synthetic', 'root': str(self.vault), 'private_root': str(self.private),
                 'policy_path': str(self.private / 'policy.json'), 'policy_sha256': self.args[4],
                 'manifest_pointer': str(self.private / 'publications/historical/managed/latest.json'),
                 'prefixes': ['projects/'], 'note_ids': [],
                 'owner_authorization': {'state': 'approved', 'reference': 'synthetic fixture',
                                         'purpose': 'synthetic recall',
                                         'personal_content_external_model_approved': False}}
        pin = self.write_json('grant.json', grant)
        args = (str(self.private / 'grant.json'), pin, 'codex-openai')
        search = managed_memory.search_managed(*args, 'Synthetic')
        self.assertEqual(search['matches'][0]['note_id'], 'one')
        self.assertEqual(search['matches'][0]['source_references'], ['synthetic:source'])
        read = managed_memory.read_managed(*args, 'one', 7, 1)
        self.assertEqual(read['lines'][0]['text'], '# One')

    def test_competing_process_equal_or_different_target_is_never_enrolled(self):
        import publish_historical as module
        real_write = module.write_immutable
        for competing in (self.payload, b'competitor'):
            with self.subTest(equal=competing == self.payload):
                child = HistoricalTests()
                child.setUp()
                self.addCleanup(child.doCleanups)
                def create_competitor(path, data):
                    if path == child.vault / 'projects/one.md':
                        path.parent.mkdir(parents=True, exist_ok=True)
                        code = 'from pathlib import Path; import sys; Path(sys.argv[1]).write_bytes(bytes.fromhex(sys.argv[2]))'
                        subprocess.run([sys.executable, '-B', '-c', code, str(path), competing.hex()], check=True)
                    return real_write(path, data)
                with patch.object(module, 'write_immutable', side_effect=create_competitor):
                    result = publish_historical(*child.args)
                self.assertEqual(result['status'], 'PARTIAL')
                self.assertEqual(result['counts']['saved'], 0)
                self.assertEqual((child.vault / 'projects/one.md').read_bytes(), competing)
                self.assertFalse((child.private / 'publications/historical/managed/latest.json').exists())
                self.assertNotIn(publish_historical(*child.args)['status'], ('COMPLETED', 'NO_CHANGE'))

    def test_lock_contention_refuses_without_mutation(self):
        from publish_memory import publication_lock
        with publication_lock(self.private, self.vault) as acquired:
            self.assertTrue(acquired)
            self.assertEqual(publish_historical(*self.args)['status'], 'BUSY')
        self.assertFalse(any(self.vault.iterdir()))

    def test_target_deleted_after_positive_marker_is_not_recreated(self):
        import publish_historical as module
        real_write = module.write_immutable
        def interrupt(path, data):
            if path.name == 'receipt.json':
                raise OSError('synthetic interruption')
            return real_write(path, data)
        with patch.object(module, 'write_immutable', side_effect=interrupt):
            self.assertEqual(publish_historical(*self.args)['status'], 'PARTIAL')
        target = self.vault / 'projects/one.md'
        target.unlink()
        self.assertNotIn(publish_historical(*self.args)['status'], ('COMPLETED', 'NO_CHANGE'))
        self.assertFalse(target.exists())

    def test_batch_internal_links_and_heading_are_checked(self):
        other = b'---\nid: "two"\nprivacy: "synthetic"\nexternal_processing: false\nsources: ["synthetic:source"]\n---\n# Two\n'
        (self.private / 'two.md').write_bytes(other)
        self.manifest['notes'].append({'id': 'two', 'source': 'two.md', 'path': 'projects/two.md',
                                       'sha256': sha(other), 'size': len(other), 'privacy': 'synthetic',
                                       'external_processing': False, 'source_references': ['synthetic:source']})
        data = self.payload + b'[[projects/two#Two|second]]\n'
        (self.private / 'note.md').write_bytes(data)
        self.manifest['notes'][0].update(size=len(data), sha256=sha(data))
        self.pin()
        self.assertEqual(validate_historical(*self.args)['status'], 'VALID')
        self.assertEqual(publish_historical(*self.args)['counts']['saved'], 2)

    def test_pin_path_cannot_escape_private_root_via_parent(self):
        outside = self.base / 'outside.json'
        outside.write_bytes((self.private / 'manifest.json').read_bytes())
        args = list(self.args)
        args[1] = self.private / '..' / 'outside.json'
        self.assertEqual(validate_historical(*args)['status'], 'REFUSED')
        outside_auth = self.base / 'outside-auth.json'
        outside_auth.write_bytes((self.private / 'authorization.json').read_bytes())
        args = list(self.args)
        args[5] = self.private / '..' / 'outside-auth.json'
        self.assertEqual(validate_historical(*args)['status'], 'REFUSED')
        self.assertFalse(any(self.vault.iterdir()))

    def test_fence_length_and_inline_code_handling(self):
        data = self.payload + b'````\n```\n[[projects/missing]]\n````\n`` [[projects/missing]] ``\n'
        (self.private / 'note.md').write_bytes(data)
        self.manifest['notes'][0].update(size=len(data), sha256=sha(data))
        self.pin()
        self.assertEqual(validate_historical(*self.args)['status'], 'VALID')
        data += b'[[projects/missing]]\n'
        (self.private / 'note.md').write_bytes(data)
        self.manifest['notes'][0].update(size=len(data), sha256=sha(data))
        self.pin()
        self.assertEqual(validate_historical(*self.args)['status'], 'REFUSED')

    def test_fault_after_attempt_before_create_fails_closed(self):
        import publish_historical as module
        real_write = module.write_immutable
        def interrupt(path, data):
            if path == self.vault / 'projects/one.md':
                raise OSError('before create')
            return real_write(path, data)
        with patch.object(module, 'write_immutable', side_effect=interrupt):
            first = publish_historical(*self.args)
        self.assertEqual(first['status'], 'PARTIAL')
        self.assertEqual(first['outcomes'][0]['status'], 'ATTEMPTED_UNCERTAIN')
        self.assertEqual(first['counts']['saved'], 0)
        self.assertNotIn(publish_historical(*self.args)['status'], ('COMPLETED', 'NO_CHANGE'))
        self.assertFalse((self.vault / 'projects/one.md').exists())

    def test_pointer_replaced_then_exception_recovers(self):
        import publish_historical as module
        actual = module.replace_pointer
        def interrupt(path, data):
            actual(path, data)
            raise OSError('after pointer')
        with patch.object(module, 'replace_pointer', side_effect=interrupt):
            result = publish_historical(*self.args)
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual(result['counts']['saved'], 1)
        pointer = self.private / 'publications/historical/managed/latest.json'
        before = pointer.read_bytes()
        result = publish_historical(*self.args)
        self.assertEqual(result['status'], 'COMPLETED')
        self.assertEqual(result['counts']['saved'], 0)
        self.assertEqual(pointer.read_bytes(), before)

    def test_policy_and_authorization_drift_fail_closed(self):
        for index, name in ((3, 'policy.json'), (5, 'authorization.json')):
            with self.subTest(name=name):
                original = (self.private / name).read_bytes()
                (self.private / name).write_bytes(original + b' ')
                self.assertEqual(publish_historical(*self.args)['status'], 'REFUSED')
                self.assertFalse(any(self.vault.iterdir()))
                (self.private / name).write_bytes(original)

    def test_oversized_pinned_evidence_refuses(self):
        huge = b'z' * 128001
        (self.private / 'review.txt').write_bytes(huge)
        self.manifest['review_evidence'][0].update(size=len(huge), sha256=sha(huge))
        self.pin()
        self.assertEqual(publish_historical(*self.args)['status'], 'REFUSED')
        self.assertFalse(any(self.vault.iterdir()))

    def test_retry_checks_later_collision_before_creating_remaining_note(self):
        import publish_historical as module
        second = b'---\nid: "two"\nprivacy: "synthetic"\nexternal_processing: false\nsources: ["synthetic:source"]\n---\n# Two\n'
        (self.private / 'two.md').write_bytes(second)
        self.manifest['notes'].append({'id': 'two', 'source': 'two.md', 'path': 'projects/two.md',
                                       'sha256': sha(second), 'size': len(second), 'privacy': 'synthetic',
                                       'external_processing': False, 'source_references': ['synthetic:source']})
        self.pin()
        actual = module.write_immutable
        def stop_before_second_attempt(path, data):
            if path.name == 'two.attempt.json':
                raise OSError('synthetic stop')
            return actual(path, data)
        with patch.object(module, 'write_immutable', side_effect=stop_before_second_attempt):
            result = publish_historical(*self.args)
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual(result['counts']['saved'], 1)
        (self.vault / 'projects/one.md').write_bytes(b'later edit')
        result = publish_historical(*self.args)
        self.assertNotIn(result['status'], ('COMPLETED', 'NO_CHANGE'))
        self.assertFalse((self.vault / 'projects/two.md').exists())
        self.assertEqual((self.vault / 'projects/one.md').read_bytes(), b'later edit')

    def test_error_result_does_not_echo_private_contents_or_paths(self):
        (self.private / 'note.md').write_bytes(b'PRIVATE_BODY_CANARY')
        result = publish_historical(*self.args)
        self.assertEqual(result['status'], 'REFUSED')
        self.assertNotIn('PRIVATE_BODY_CANARY', str(result))
        self.assertNotIn(str(self.base), str(result))

    def test_disabled_policy_does_not_create_intent(self):
        self.policy['enabled'] = False
        self.pin()
        self.assertEqual(publish_historical(*self.args)['status'], 'DISABLED')
        self.assertFalse(any(self.vault.iterdir()))
        self.assertFalse((self.private / 'publications').exists())

    def test_casefolded_duplicate_ids_and_wrong_scope_type_refuse(self):
        second = dict(self.manifest['notes'][0], id='ONE', source='two.md', path='projects/two.md')
        (self.private / 'two.md').write_bytes(self.payload)
        self.manifest['notes'].append(second)
        self.pin()
        self.assertEqual(validate_historical(*self.args)['status'], 'REFUSED')

    def test_private_record_faults_recover_or_refuse_by_marker(self):
        import publish_historical as module
        real_write = module.write_immutable
        cases = [('intent.json', 'COMPLETED'), ('one.attempt.json', 'REFUSED'),
                 ('one.installed.json', 'COMPLETED'), ('receipt.json', 'NO_CHANGE')]
        for name, expected in cases:
            with self.subTest(record=name):
                child = HistoricalTests()
                child.setUp()
                self.addCleanup(child.doCleanups)
                def fail_after_record(path, data):
                    result = real_write(path, data)
                    if path.name == name:
                        raise OSError('synthetic after-record failure')
                    return result
                with patch.object(module, 'write_immutable', side_effect=fail_after_record):
                    first = publish_historical(*child.args)
                self.assertEqual(first['status'], 'PARTIAL')
                retry = publish_historical(*child.args)
                self.assertEqual(retry['status'], expected)
                if name == 'one.attempt.json':
                    self.assertFalse((child.vault / 'projects/one.md').exists())

    def test_oversized_pins_and_pointer_refuse_without_changing_target(self):
        for arg_index, filename in ((1, 'manifest.json'), (5, 'authorization.json')):
            with self.subTest(filename=filename):
                original = (self.private / filename).read_bytes()
                huge = b'a' * 128001
                (self.private / filename).write_bytes(huge)
                args = list(self.args)
                args[arg_index + 1] = sha(huge)
                self.assertEqual(publish_historical(*args)['status'], 'REFUSED')
                (self.private / filename).write_bytes(original)
        self.assertEqual(publish_historical(*self.args)['status'], 'COMPLETED')
        pointer = self.private / 'publications/historical/managed/latest.json'
        pointer.write_bytes(b'x' * 4097)
        self.assertNotEqual(publish_historical(*self.args)['status'], 'NO_CHANGE')
        self.assertEqual((self.vault / 'projects/one.md').read_bytes(), self.payload)

    def test_duplicate_policy_keys_and_deep_json_are_sanitized(self):
        for arg_index, name, raw in ((3, 'policy.json', b'{"schema":"one","schema":"two"}'),
                                     (1, 'manifest.json', b'[' * 2000 + b']' * 2000)):
            with self.subTest(name=name):
                original = (self.private / name).read_bytes()
                (self.private / name).write_bytes(raw)
                args = list(self.args)
                args[arg_index + 1] = sha(raw)
                self.assertEqual(publish_historical(*args)['status'], 'REFUSED')
                (self.private / name).write_bytes(original)
        self.assertFalse(any(self.vault.iterdir()))

    def test_reference_style_and_malformed_wikilinks_refuse(self):
        for suffix in ('[x]: other.md\n[x]', '[[projects/[bad]]]]', '[[projects/one#]]'):
            with self.subTest(suffix=suffix):
                data = self.payload + suffix.encode()
                (self.private / 'note.md').write_bytes(data)
                self.manifest['notes'][0].update(size=len(data), sha256=sha(data))
                self.pin()
                self.assertEqual(validate_historical(*self.args)['status'], 'REFUSED')

    def test_redirected_destination_parent_refuses(self):
        outside = self.base / 'outside'
        outside.mkdir()
        try:
            (self.vault / 'projects').symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest('Windows symlink creation privilege unavailable')
        self.assertNotIn(publish_historical(*self.args)['status'], ('COMPLETED', 'NO_CHANGE'))
        self.assertFalse(any(outside.iterdir()))

    def test_intervening_manifest_conflict_is_checked_before_remaining_create(self):
        import publish_historical as module
        second = b'---\nid: "two"\nprivacy: "synthetic"\nexternal_processing: false\nsources: ["synthetic:source"]\n---\n# Two\n'
        (self.private / 'two.md').write_bytes(second)
        self.manifest['notes'].append({'id': 'two', 'source': 'two.md', 'path': 'projects/two.md',
                                       'sha256': sha(second), 'size': len(second), 'privacy': 'synthetic',
                                       'external_processing': False, 'source_references': ['synthetic:source']})
        self.pin()
        actual = module.write_immutable
        def interrupt(path, data):
            if path.name == 'two.attempt.json':
                raise OSError('before second attempt')
            return actual(path, data)
        with patch.object(module, 'write_immutable', side_effect=interrupt):
            self.assertEqual(publish_historical(*self.args)['status'], 'PARTIAL')
        entry = {k: v for k, v in self.manifest['notes'][1].items() if k != 'source'}
        entry['id'] = 'other'
        state = {'schema': 'brain-managed-manifest-v1', 'policy_id': 'historical',
                 'policy_sha256': self.args[4], 'generation': 1, 'transaction_id': 'other', 'notes': [entry]}
        data = (json.dumps(state, sort_keys=True, separators=(',', ':')) + '\n').encode()
        name = sha(data) + '.manifest.json'
        managed = self.private / 'publications/historical/managed'
        managed.mkdir(parents=True, exist_ok=True)
        (managed / name).write_bytes(data)
        (managed / 'latest.json').write_text(json.dumps({'manifest': name, 'sha256': sha(data)}))
        result = publish_historical(*self.args)
        self.assertNotIn(result['status'], ('COMPLETED', 'NO_CHANGE'))
        self.assertFalse((self.vault / 'projects/two.md').exists())

    def test_interruption_after_manifest_file_before_pointer_recovers(self):
        import publish_historical as module
        actual = module.write_immutable
        def interrupt(path, data):
            result = actual(path, data)
            if path.name.endswith('.manifest.json'):
                raise OSError('after manifest file')
            return result
        with patch.object(module, 'write_immutable', side_effect=interrupt):
            result = publish_historical(*self.args)
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual(result['counts']['saved'], 1)
        pointer = self.private / 'publications/historical/managed/latest.json'
        self.assertFalse(pointer.exists())
        result = publish_historical(*self.args)
        self.assertEqual(result['status'], 'COMPLETED')
        self.assertEqual(result['counts']['saved'], 0)
        self.assertEqual(result['counts']['recovered'], 1)

    def test_oversized_attempt_marker_refuses_without_readoption(self):
        import publish_historical as module
        actual = module.write_immutable
        def interrupt(path, data):
            if path == self.vault / 'projects/one.md':
                raise OSError('before target')
            return actual(path, data)
        with patch.object(module, 'write_immutable', side_effect=interrupt):
            result = publish_historical(*self.args)
        self.assertEqual(result['status'], 'PARTIAL')
        attempt = self.private / 'publications/historical/historical' / result['transaction_id'] / 'one.attempt.json'
        attempt.write_bytes(b'x' * 128001)
        self.assertEqual(publish_historical(*self.args)['status'], 'REFUSED')
        self.assertFalse((self.vault / 'projects/one.md').exists())

    def test_completed_replay_rejects_changed_attempt_and_collision_marker(self):
        result = publish_historical(*self.args)
        self.assertEqual(result['status'], 'COMPLETED')
        txdir = self.private / 'publications/historical/historical' / result['transaction_id']
        attempt = txdir / 'one.attempt.json'
        original = attempt.read_bytes()
        attempt.write_bytes(b'changed')
        self.assertNotEqual(publish_historical(*self.args)['status'], 'NO_CHANGE')
        attempt.write_bytes(original)
        (txdir / 'one.collision.json').write_bytes(b'{}')
        self.assertNotEqual(publish_historical(*self.args)['status'], 'NO_CHANGE')

    def test_completed_replay_rejects_matching_receipt_with_empty_manifest(self):
        result = publish_historical(*self.args)
        self.assertEqual(result['status'], 'COMPLETED')
        managed = self.private / 'publications/historical/managed'
        pointer = managed / 'latest.json'
        state_pointer = json.loads(pointer.read_bytes())
        state = json.loads((managed / state_pointer['manifest']).read_bytes())
        state['notes'] = []
        raw = (json.dumps(state, sort_keys=True, separators=(',', ':')) + '\n').encode()
        name = sha(raw) + '.manifest.json'
        (managed / name).write_bytes(raw)
        pointer.write_text(json.dumps({'manifest': name, 'sha256': sha(raw)}))
        receipt = self.private / 'publications/historical/historical' / result['transaction_id'] / 'receipt.json'
        receipt_data = json.loads(receipt.read_bytes())
        receipt_data['manifest_sha256'] = sha(raw)
        receipt.write_text(json.dumps(receipt_data))
        commit = receipt.parent / 'commit.json'
        commit_data = json.loads(commit.read_bytes())
        commit_data['manifest_sha256'] = sha(raw)
        commit_data['pointer_sha256'] = sha(pointer.read_bytes())
        commit.write_text(json.dumps(commit_data))
        self.assertNotEqual(publish_historical(*self.args)['status'], 'NO_CHANGE')

    def test_missing_pointer_after_commit_does_not_drop_prior_enrollment(self):
        import publish_historical as module
        managed = self.private / 'publications/historical/managed'
        managed.mkdir(parents=True)
        prior = {'id': 'prior', 'path': 'projects/prior.md', 'sha256': sha(b'prior'), 'size': 5,
                 'privacy': 'synthetic', 'external_processing': False, 'source_references': ['synthetic:prior']}
        state = {'schema': 'brain-managed-manifest-v1', 'policy_id': 'historical', 'policy_sha256': self.args[4],
                 'generation': 1, 'transaction_id': 'prior', 'notes': [prior]}
        raw = (json.dumps(state, sort_keys=True, separators=(',', ':')) + '\n').encode()
        name = sha(raw) + '.manifest.json'
        (managed / name).write_bytes(raw)
        pointer = managed / 'latest.json'
        pointer.write_text(json.dumps({'manifest': name, 'sha256': sha(raw)}))
        actual = module.write_immutable
        def interrupt(path, data):
            if path.name == 'receipt.json':
                raise OSError('before receipt')
            return actual(path, data)
        with patch.object(module, 'write_immutable', side_effect=interrupt):
            result = publish_historical(*self.args)
        self.assertEqual(result['status'], 'PARTIAL')
        pointer.unlink()
        self.assertNotIn(publish_historical(*self.args)['status'], ('COMPLETED', 'NO_CHANGE'))
        self.assertFalse(pointer.exists())
        self.assertEqual((self.vault / 'projects/one.md').read_bytes(), self.payload)

    def test_ambiguous_pre_pointer_failure_refuses_automatic_retry(self):
        import publish_historical as module
        with patch.object(module, 'replace_pointer', side_effect=OSError('before pointer')):
            result = publish_historical(*self.args)
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertNotIn(publish_historical(*self.args)['status'], ('COMPLETED', 'NO_CHANGE'))
        self.assertFalse((self.private / 'publications/historical/managed/latest.json').exists())

    def test_initial_prior_pointer_deleted_before_enrollment_refuses(self):
        import publish_historical as module
        managed = self.private / 'publications/historical/managed'
        managed.mkdir(parents=True)
        prior = {'id': 'prior', 'path': 'projects/prior.md', 'sha256': sha(b'prior'), 'size': 5,
                 'privacy': 'synthetic', 'external_processing': False, 'source_references': ['synthetic:prior']}
        state = {'schema': 'brain-managed-manifest-v1', 'policy_id': 'historical', 'policy_sha256': self.args[4],
                 'generation': 1, 'transaction_id': 'prior', 'notes': [prior]}
        raw = (json.dumps(state, sort_keys=True, separators=(',', ':')) + '\n').encode()
        name = sha(raw) + '.manifest.json'
        (managed / name).write_bytes(raw)
        pointer = managed / 'latest.json'
        pointer.write_text(json.dumps({'manifest': name, 'sha256': sha(raw)}))
        actual = module.write_immutable
        def interrupt(path, data):
            if path.name == 'one.attempt.json':
                raise OSError('before attempt')
            return actual(path, data)
        with patch.object(module, 'write_immutable', side_effect=interrupt):
            self.assertEqual(publish_historical(*self.args)['status'], 'PARTIAL')
        pointer.unlink()
        self.assertNotIn(publish_historical(*self.args)['status'], ('COMPLETED', 'NO_CHANGE'))
        self.assertFalse(pointer.exists())
        self.assertFalse((self.vault / 'projects/one.md').exists())

    def test_device_name_note_id_refuses_even_with_matching_payload(self):
        data = self.payload.replace(b'id: "one"', b'id: "CON"')
        (self.private / 'note.md').write_bytes(data)
        self.manifest['notes'][0].update(id='CON', size=len(data), sha256=sha(data))
        self.pin()
        self.assertEqual(validate_historical(*self.args)['status'], 'REFUSED')
        self.assertEqual(publish_historical(*self.args)['status'], 'REFUSED')
        self.assertFalse(any(self.vault.iterdir()))

    def test_case_alias_note_ids_refuse_with_matching_payloads(self):
        data = self.payload.replace(b'id: "one"', b'id: "ONE"')
        (self.private / 'two.md').write_bytes(data)
        self.manifest['notes'].append(dict(self.manifest['notes'][0], id='ONE', source='two.md',
                                           path='projects/two.md', size=len(data), sha256=sha(data)))
        self.pin()
        self.assertEqual(validate_historical(*self.args)['status'], 'REFUSED')
        self.assertFalse(any(self.vault.iterdir()))

    def test_device_name_policy_id_refuses_before_mutation(self):
        self.policy['policy_id'] = 'NUL'
        self.authorization['policy_id'] = 'NUL'
        self.pin()
        self.assertEqual(validate_historical(*self.args)['status'], 'REFUSED')
        self.assertFalse(any(self.vault.iterdir()))
        self.manifest['notes'].pop()
        self.policy['write_scope']['updates'] = 0
        self.pin()
        self.assertEqual(validate_historical(*self.args)['status'], 'REFUSED')


if __name__ == '__main__':
    unittest.main()
