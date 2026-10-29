import copy
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from save_interactive_memory import stage


class InteractiveMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.root, self.project = base / 'private', base / 'project'
        self.root.mkdir()
        self.project.mkdir()
        (self.root / '.private-staging.json').write_text(json.dumps({'live_writes': False, 'external_exports': False}))
        (self.project / 'example.py').write_text('value = 42\n')
        self.packet = {'schema': 'brain-save-context-v1', 'role': 'reviewer', 'coverage': 'visible-context',
                       'items': [{'kind': 'test', 'text': 'The focused test run reported one failure; no fix was applied.',
                                  'status': 'reported-failed', 'actor': 'this-session', 'support': 'visible-tool-output',
                                  'references': ['visible tool result: unittest exit 1']}], 'artifacts': ['example.py']}
        self.environment = {'CODEX_THREAD_ID': 'synthetic-session-1'}

    def save(self, packet=None, environment=None):
        return stage(self.root, self.project, packet or self.packet, self.environment if environment is None else environment)

    def test_stage_role_evidence_and_duplicate(self):
        first = self.save()
        markdown = self.root / first['proposal']
        before = markdown.read_bytes()
        second = self.save()
        self.assertEqual((first['status'], second['status'], second['proposals']), ('STAGED', 'DUPLICATE_SOURCE', 0))
        self.assertEqual(markdown.read_bytes(), before)
        note = json.loads((self.root / first['candidate']).read_bytes())
        self.assertEqual(note['interactive_capture']['role'], 'reviewer')
        self.assertFalse(note['interactive_capture']['full_transcript'])
        self.assertEqual(note['claims'][0]['evidence'], 'summary-derived')
        self.assertIn('reported-failed', note['claims'][0]['text'])
        self.assertEqual(len(note['interactive_capture']['artifacts'][0]['sha256']), 64)
        self.assertFalse(note['external_processing'])

    def test_parallel_projects_sessions_and_roles_do_not_mix(self):
        jobs = [('planner', 'plan-session'), ('reviewer', 'review-session'), ('implementer', 'implementation-session')]
        def run(job):
            packet = copy.deepcopy(self.packet)
            packet['role'] = job[0]
            return self.save(packet, {'CODEX_THREAD_ID': job[1]})
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(run, jobs))
        self.assertEqual(len({x['scope'] for x in results}), 3)
        self.assertEqual(len({x['proposal'] for x in results}), 3)
        for result, (_, session) in zip(results, jobs):
            candidate = json.loads((self.root / result['candidate']).read_bytes())
            self.assertEqual(candidate['interactive_capture']['session_reference'], session)

    def test_different_projects_never_dedupe(self):
        first = self.save()
        other = self.project.parent / 'other-project'
        other.mkdir()
        (other / 'example.py').write_text('value = 42\n')
        second = stage(self.root, other, self.packet, self.environment)
        self.assertNotEqual(first['scope'], second['scope'])

    def test_unknown_host_identity_is_not_fabricated_session(self):
        result = self.save(environment={})
        note = json.loads((self.root / result['candidate']).read_bytes())
        self.assertEqual(note['interactive_capture']['session_reference_kind'], 'invocation-id-not-a-session-id')

    def test_no_outcomes_and_repeat(self):
        packet = {**self.packet, 'items': [], 'artifacts': []}
        first, second = self.save(packet), self.save(packet)
        self.assertEqual((first['status'], first['proposals']), ('NO_MEANINGFUL_OUTCOMES', 0))
        self.assertNotIn('proposal', first)
        self.assertEqual((second['status'], second['proposals']), ('DUPLICATE_SOURCE', 0))

    def test_quoted_credential_and_report_fields_refused_before_archive(self):
        for field in ('text', 'references'):
            packet = copy.deepcopy(self.packet)
            secret = 'Synthetic example: "password": "fixture-only-secret"'
            packet['items'][0][field] = [secret] if field == 'references' else secret
            with self.assertRaises(ValueError):
                self.save(packet)
        self.assertFalse((self.root / 'archive').exists())

    def test_reviewer_and_planner_cannot_claim_implementation(self):
        for role in ('reviewer', 'planner'):
            packet = copy.deepcopy(self.packet)
            packet['role'] = role
            packet['items'][0].update(kind='work', status='reported-completed')
            with self.assertRaisesRegex(ValueError, 'ROLE_CANNOT'):
                self.save(packet)

    def test_unexecuted_tests_and_next_actions(self):
        packet = copy.deepcopy(self.packet)
        packet['items'][0].update(kind='next-action', status='reported-completed')
        with self.assertRaises(ValueError):
            self.save(packet)
        packet['items'][0].update(kind='test', status='proposed', support='inference')
        self.assertEqual(self.save(packet)['status'], 'STAGED')

    def test_unsupported_result_and_missing_reference(self):
        packet = copy.deepcopy(self.packet)
        packet['items'][0]['support'] = 'unsupported'
        with self.assertRaises(ValueError):
            self.save(packet)
        packet['items'][0].update(status='unknown', references=[])
        with self.assertRaises(ValueError):
            self.save(packet)

    def test_external_history_credentials_and_traversal_artifacts_refused(self):
        for name in ('../outside.py', '/tmp/outside.py', '.codex/sessions/log.jsonl', '.env', 'auth.json', 'C:/outside.md'):
            with self.subTest(name=name), self.assertRaises((ValueError, OSError)):
                self.save({**self.packet, 'artifacts': [name]})

    def test_missing_or_altered_cached_source_candidate_markdown_receipt(self):
        for target in ('source', 'candidate', 'proposal', 'receipt'):
            # Fresh role/session namespace for every negative case.
            environment = {'CODEX_THREAD_ID': 'tamper-' + target}
            result = self.save(environment=environment)
            path = self.root / result[target] if target != 'receipt' else self.root / result['candidate'].replace('candidate.json', 'receipt.json')
            path.write_text('{}')
            with self.assertRaises((ValueError, OSError, KeyError)):
                self.save(environment=environment)

    def test_deleted_markdown_is_not_healed(self):
        result = self.save()
        path = self.root / result['proposal']
        path.unlink()
        with self.assertRaises((ValueError, OSError)):
            self.save()
        self.assertFalse(path.exists())

    def test_artifact_changed_results_in_new_proposal(self):
        first = self.save()
        (self.project / 'example.py').write_text('value = 43\n')
        second = self.save()
        self.assertNotEqual(first['source_sha256'], second['source_sha256'])

    def test_staging_root_boundary(self):
        outside = self.root.parent / 'unmarked'
        outside.mkdir()
        with self.assertRaises((ValueError, OSError)):
            stage(outside, self.project, self.packet, self.environment)
    @unittest.skipIf(os.name == 'nt', 'Native Windows symlink creation needs unavailable privilege; not a passing symlink test')
    def test_symlink_boundary(self):
        linked = self.project / 'redirect.py'
        linked.symlink_to(self.project / 'example.py')
        with self.assertRaises(ValueError):
            self.save({**self.packet, 'artifacts': ['redirect.py']})

    def test_hardlinked_artifact_refused(self):
        linked = self.project / 'linked.py'
        os.link(self.project / 'example.py', linked)
        with self.assertRaises(ValueError):
            self.save({**self.packet, 'artifacts': ['linked.py']})

    def test_cli_failure_contains_no_secret_and_no_model_process(self):
        adapter = Path(__file__).resolve().parents[1] / 'scripts/save_interactive_memory.py'
        result = subprocess.run([sys.executable, '-B', str(adapter), '--root', str(self.root)],
                                input=b'{"password":"fixture-only-secret"}', capture_output=True, cwd=self.project)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(b'fixture-only-secret', result.stderr)
        self.assertEqual(json.loads(result.stderr)['status'], 'REFUSED')


if __name__ == '__main__':
    unittest.main()
