"""CLI recall proof using disposable synthetic metadata and notes only."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
import test_managed_memory as fixtures


class RecallAdapterTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ManagedMemoryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def cli(self, args, overrides=None):
        fixture = self.fixture
        flags = {'--grant': fixture.args[0], '--grant-sha256': fixture.args[1], '--client': fixture.args[2]}
        flags.update(overrides or {})
        script = Path(__file__).resolve().parents[1] / 'scripts/recall_managed_memory.py'
        arguments = [token for item in flags.items() for token in item]
        return subprocess.run([sys.executable, '-B', str(script), *arguments, *args],
                              capture_output=True, cwd=fixture.base)

    def test_search_and_read_citations_without_writes(self):
        fixture = self.fixture
        before = {p: p.read_bytes() for p in fixture.base.rglob('*') if p.is_file()}
        result = self.cli(['search', '--query', 'amber', '--limit', '1'])
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value['matches'][0]['note_id'], 'decision')
        self.assertEqual(value['manifest_generation'], 1)
        result = self.cli(['read', '--note-id', 'decision', '--start-line', '7', '--line-count', '1'])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)['lines'], [{'line': 7, 'text': 'The marker is amber-kite.'}])
        self.assertEqual(before, {p: p.read_bytes() for p in fixture.base.rglob('*') if p.is_file()})

    def test_bounds_and_unknown_arguments_redacted(self):
        cases = [['search', '--query', 'amber', '--limit', '5'],
                 ['read', '--note-id', 'decision', '--line-count', '41'],
                 ['read', '--note-id', 'decision', '--start-line', 'PRIVATE_INPUT_CANARY'],
                 ['search', '--query', 'amber', '--path', 'PRIVATE_INPUT_CANARY'],
                 ['publish'], ['search', '--query', '']]
        for args in cases:
            with self.subTest(args=args):
                result = self.cli(args)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn(b'PRIVATE_INPUT_CANARY', result.stderr + result.stdout)
                self.assertEqual(json.loads(result.stderr)['error_code'], 'MANAGED_RECALL_REFUSED')

    def test_bad_pin_client_stale_note_and_unselected_note_refused(self):
        for overrides in [{'--grant-sha256': '0' * 64}, {'--client': 'claude-anthropic'},
                          {'--grant': str(self.fixture.base / 'PRIVATE_PATH_CANARY.json')}]:
            result = self.cli(['search', '--query', 'amber'], overrides)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn(b'PRIVATE_PATH_CANARY', result.stdout + result.stderr)
        result = self.cli(['read', '--note-id', 'not-enrolled'])
        self.assertEqual(result.returncode, 2)
        self.fixture.note.write_bytes(b'PRIVATE_NOTE_CANARY')
        result = self.cli(['search', '--query', 'amber'])
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(b'PRIVATE_NOTE_CANARY', result.stdout + result.stderr)

    def test_missing_host_settings_refused_without_config_creation(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/recall_managed_memory.py'
        result = subprocess.run([sys.executable, '-B', str(script), 'search', '--query', 'amber'],
                                capture_output=True, cwd=self.fixture.base)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)['error_code'], 'MANAGED_RECALL_REFUSED')

    def test_actual_synthetic_publication_recalled_by_new_cli_process(self):
        import test_publish_memory as publication_fixtures
        from selected_memory import digest
        fixture = publication_fixtures.PublicationTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.assertEqual(fixture.publish()['status'], 'SAVED')
        grant = {'schema': 'brain-managed-read-grant-v1', 'source_kind': 'canonical',
                 'client': 'codex-openai', 'root': str(fixture.vault), 'private_root': str(fixture.root),
                 'policy_path': str(fixture.policy_path), 'policy_sha256': fixture.pin,
                 'manifest_pointer': str(fixture.root / 'publications' / fixture.policy['policy_id'] / 'managed/latest.json'),
                 'prefixes': ['logs/brain-save/'], 'note_ids': [],
                 'owner_authorization': {'state': 'approved', 'reference': 'synthetic fixture only',
                                         'purpose': 'synthetic CLI integration',
                                         'personal_content_external_model_approved': True}}
        path = fixture.root / 'synthetic-grant.json'
        path.write_text(json.dumps(grant), encoding='utf-8')
        before = {p: p.read_bytes() for p in fixture.vault.rglob('*') if p.is_file()}
        result = self.cli(['search', '--query', 'canonical knowledge'],
                          {'--grant': str(path), '--grant-sha256': digest(path.read_bytes())})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)['matches']), 1)
        self.assertEqual(before, {p: p.read_bytes() for p in fixture.vault.rglob('*') if p.is_file()})


if __name__ == '__main__':
    unittest.main()
