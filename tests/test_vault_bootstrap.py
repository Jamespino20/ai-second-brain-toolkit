import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from bootstrap_vault import bootstrap_vault, BootstrapRefused, TARGETS


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name).resolve()
        self.source, self.vault, self.journal = (root / x for x in ('source', 'vault', 'private'))
        for directory in (self.source, self.vault, self.journal):
            directory.mkdir()
        (self.journal / '.private-staging.json').write_text('{"live_writes": false, "external_exports": false}')
        self.payload = {name: ('synthetic ' + name).encode() for name in TARGETS}
        self.hashes = {name: hashlib.sha256(data).hexdigest() for name, data in self.payload.items()}
        for name, data in self.payload.items():
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def run_bootstrap(self):
        return bootstrap_vault(self.source, self.vault, self.journal, self.hashes)

    def test_create_and_replay(self):
        result = self.run_bootstrap()
        self.assertEqual(set(result['created']), set(TARGETS))
        self.assertEqual(result['recovered'], [])
        replay = self.run_bootstrap()
        self.assertEqual(replay['created'], [])
        self.assertEqual(set(replay['recovered']), set(TARGETS))

    def test_equal_preexisting_target_refuses_without_intent(self):
        (self.vault / TARGETS[0]).write_bytes(self.payload[TARGETS[0]])
        with self.assertRaises(BootstrapRefused):
            self.run_bootstrap()
        self.assertFalse((self.vault / TARGETS[1]).exists())

    def test_later_edit_blocks_all_further_writes(self):
        self.run_bootstrap()
        (self.vault / TARGETS[0]).write_bytes(b'user edit')
        (self.vault / TARGETS[-1]).unlink()
        with self.assertRaises(BootstrapRefused):
            self.run_bootstrap()
        self.assertFalse((self.vault / TARGETS[-1]).exists())
        self.assertEqual((self.vault / TARGETS[0]).read_bytes(), b'user edit')

    def test_source_or_hash_drift_refused(self):
        (self.source / TARGETS[0]).write_bytes(b'drift')
        with self.assertRaises(BootstrapRefused):
            self.run_bootstrap()
        self.assertFalse(any(self.vault.iterdir()))

    def test_interruption_before_and_after_each_target_recovers(self):
        import bootstrap_vault as module
        real_write = module.write_immutable
        for position in range(5):
            for after in (False, True):
                with self.subTest(position=position, after=after), tempfile.TemporaryDirectory() as temporary:
                    self.setUp_fresh(Path(temporary).resolve())
                    target = self.vault / TARGETS[position]
                    def interrupted(path, data):
                        if path == target:
                            if after:
                                real_write(path, data)
                            raise OSError('simulated interruption')
                        return real_write(path, data)
                    with patch.object(module, 'write_immutable', side_effect=interrupted):
                        with self.assertRaises(BootstrapRefused):
                            self.run_bootstrap()
                    result = self.run_bootstrap()
                    self.assertEqual(len(result['created']) + len(result['recovered']), 5)
                    self.assertEqual([ (self.vault / n).read_bytes() for n in TARGETS ],
                                     [ self.payload[n] for n in TARGETS ])

    def setUp_fresh(self, root):
        self.source, self.vault, self.journal = (root / x for x in ('source', 'vault', 'private'))
        for directory in (self.source, self.vault, self.journal):
            directory.mkdir()
        (self.journal / '.private-staging.json').write_text('{"live_writes": false, "external_exports": false}')
        for name, data in self.payload.items():
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def test_interrupted_intent_rejects_changed_payload_and_competing_target(self):
        import bootstrap_vault as module
        real_write = module.write_immutable
        def interrupt(path, data):
            if path == self.vault / TARGETS[1]:
                raise OSError('interrupted')
            return real_write(path, data)
        with patch.object(module, 'write_immutable', side_effect=interrupt):
            with self.assertRaises(BootstrapRefused):
                self.run_bootstrap()
        (self.vault / TARGETS[1]).write_bytes(b'competitor')
        with self.assertRaises(BootstrapRefused):
            self.run_bootstrap()
        self.assertEqual((self.vault / TARGETS[1]).read_bytes(), b'competitor')
        self.assertFalse((self.vault / TARGETS[2]).exists())
        (self.vault / TARGETS[1]).unlink()
        (self.source / TARGETS[0]).write_bytes(b'new source')
        changed = dict(self.hashes, **{TARGETS[0]: hashlib.sha256(b'new source').hexdigest()})
        with self.assertRaises(BootstrapRefused):
            bootstrap_vault(self.source, self.vault, self.journal, changed)

    def test_lock_contention_and_unrelated_bytes(self):
        from publish_memory import publication_lock
        unrelated = self.vault / 'untouched.md'
        unrelated.write_bytes(b'keep')
        with publication_lock(self.journal, self.vault) as acquired:
            self.assertTrue(acquired)
            with self.assertRaises(BootstrapRefused):
                self.run_bootstrap()
        self.assertEqual(unrelated.read_bytes(), b'keep')
        self.assertEqual(sorted(p.name for p in self.vault.iterdir()), ['untouched.md'])

    def test_matching_target_created_during_first_write_is_collision(self):
        import bootstrap_vault as module
        real_write = module.write_immutable
        def competing(path, data):
            if path == self.vault / TARGETS[0]:
                path.write_bytes(data)
            return real_write(path, data)
        with patch.object(module, 'write_immutable', side_effect=competing):
            with self.assertRaises(BootstrapRefused):
                self.run_bootstrap()
        self.assertFalse((self.vault / TARGETS[1]).exists())

    def test_partial_error_reports_created_and_observed_paths(self):
        import bootstrap_vault as module
        real_write = module.write_immutable
        def interrupted(path, data):
            if path == self.vault / TARGETS[1]:
                real_write(path, data)
                raise OSError('after write')
            return real_write(path, data)
        with patch.object(module, 'write_immutable', side_effect=interrupted):
            with self.assertRaises(BootstrapRefused) as caught:
                self.run_bootstrap()
        self.assertEqual(caught.exception.created, [TARGETS[0]])
        self.assertIn(TARGETS[1], caught.exception.recovered)

    def test_changed_vault_and_missing_private_marker_refused(self):
        self.run_bootstrap()
        other = self.vault.parent / 'other'
        other.mkdir()
        with self.assertRaises(BootstrapRefused):
            bootstrap_vault(self.source, other, self.journal, self.hashes)
        self.assertFalse(any(other.iterdir()))
        (self.journal / '.private-staging.json').unlink()
        with self.assertRaises(BootstrapRefused):
            self.run_bootstrap()

    def test_redirected_target_parent_refused(self):
        outside = self.vault.parent / 'outside'
        outside.mkdir()
        try:
            (self.vault / 'system').symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest('Windows symlink creation privilege unavailable')
        with self.assertRaises(BootstrapRefused):
            self.run_bootstrap()
        self.assertFalse(any(outside.iterdir()))
        self.assertFalse((self.vault / TARGETS[0]).exists())

    def test_oversized_source_refuses_without_target_or_intent(self):
        oversized = b'x' * 128001
        (self.source / TARGETS[0]).write_bytes(oversized)
        self.hashes[TARGETS[0]] = hashlib.sha256(oversized).hexdigest()
        with self.assertRaises(BootstrapRefused) as caught:
            self.run_bootstrap()
        self.assertIn('PUBLICATION_STATE_TOO_LARGE', str(caught.exception.__cause__))
        self.assertEqual((self.source / TARGETS[0]).read_bytes(), oversized)
        self.assertFalse(any(self.vault.iterdir()))
        self.assertFalse((self.journal / 'bootstrap-intents' / 'intent.json').exists())

    def test_oversized_target_on_retry_refuses_without_filling_missing(self):
        self.run_bootstrap()
        oversized = b'y' * 128001
        target = self.vault / TARGETS[0]
        target.write_bytes(oversized)
        (self.vault / TARGETS[-1]).unlink()
        with self.assertRaises(BootstrapRefused) as caught:
            self.run_bootstrap()
        self.assertIn('PUBLICATION_STATE_TOO_LARGE', str(caught.exception.__cause__))
        self.assertEqual(target.read_bytes(), oversized)
        self.assertFalse((self.vault / TARGETS[-1]).exists())

    def test_oversized_intent_refuses_without_target_writes(self):
        intent = self.journal / 'bootstrap-intents' / 'intent.json'
        intent.parent.mkdir()
        oversized = b'z' * 128001
        intent.write_bytes(oversized)
        with self.assertRaises(BootstrapRefused) as caught:
            self.run_bootstrap()
        self.assertIn('PUBLICATION_STATE_TOO_LARGE', str(caught.exception.__cause__))
        self.assertEqual(intent.read_bytes(), oversized)
        self.assertFalse(any(self.vault.iterdir()))


if __name__ == '__main__':
    unittest.main()
