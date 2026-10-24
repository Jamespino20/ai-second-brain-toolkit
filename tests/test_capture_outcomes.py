import copy
import json
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from capture_outcomes import CaptureError, completed_report, load_config, privacy_check, stage_report
from migrate import json_bytes
from run_codex_capture import capture_lock, replay_capture, run_capture, set_enabled


class CaptureMVPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'private'
        self.root.mkdir()
        (self.root / '.private-staging.json').write_bytes(json_bytes({'live_writes': False, 'external_exports': False}))
        self.cwd = Path(self.temp.name) / 'synthetic-project'
        self.cwd.mkdir()
        self.prompt = 'Use Markdown for canonical notes.'
        self.prompt_file = self.root / 'request.txt'
        self.prompt_file.write_text(self.prompt, encoding='utf-8')
        self.codex_home = self.root / 'codex-home'
        self.codex_home.mkdir()
        self.profile = self.codex_home / 'synthetic-capture-test.config.toml'
        self.profile.write_bytes(b'sandbox_mode = "read-only"\n')
        environment = patch.dict('os.environ', {'CODEX_HOME': str(self.codex_home)})
        environment.start()
        self.addCleanup(environment.stop)
        self.config = {'schema': 'codex-capture-config-v1', 'enabled': True,
                       'workspace': str(self.root), 'allowed_cwds': [str(self.cwd)],
                       'profile': 'synthetic-capture-test', 'source_privacy': 'synthetic',
                       'profile_sha256': hashlib.sha256(self.profile.read_bytes()).hexdigest()}
        self.config_path = self.root / 'capture-config.json'
        self.save_config()
        self.report = {'schema_version': '1.0', 'items': [
            {'kind': 'outcome', 'text': 'The synthetic session supplied an outcome report.',
             'basis': 'assistant-reported', 'source_quote': ''},
            {'kind': 'decision', 'text': self.prompt, 'basis': 'user-stated', 'source_quote': self.prompt},
            {'kind': 'lesson', 'text': 'Verify source receipts before treating reports as accepted work.',
             'basis': 'inferred', 'source_quote': ''},
            {'kind': 'milestone', 'text': 'A synthetic proposal is ready for review.',
             'basis': 'assistant-reported', 'source_quote': ''}]}

    def save_config(self):
        self.config_path.write_bytes(json_bytes(self.config))

    def output(self, session='fixture-session-1', report=None):
        report = self.report if report is None else report
        final = json_bytes(report)
        events = [{'type': 'thread.started', 'thread_id': session}, {'type': 'turn.started'},
                  {'type': 'item.completed', 'item': {'id': 'item_1', 'type': 'agent_message', 'text': final.decode()}},
                  {'type': 'turn.completed', 'usage': {'input_tokens': 1, 'output_tokens': 1}}]
        return b''.join(json_bytes(event).replace(b'\n', b'') + b'\n' for event in events), final

    def stage(self, raw=None, final=None, exit_code=0):
        if raw is None:
            raw, final = self.output()
        return stage_report(self.config, self.root, raw, final, self.prompt, exit_code)

    def launcher(self, session='fixture-session-1', report=None, exit_code=0, mutate=None, incomplete=False):
        def run(command, request, cwd, run_dir, timeout):
            raw, final = self.output(session, report)
            if incomplete:
                raw = b'\n'.join(raw.splitlines()[:-1]) + b'\n'
            (run_dir / 'events.jsonl').write_bytes(raw)
            (run_dir / 'stderr.txt').write_bytes(b'fixture diagnostics')
            (run_dir / 'final.json').write_bytes(final)
            if mutate:
                mutate()
            return exit_code
        return run

    def run_fixture(self, **kwargs):
        with patch('run_codex_capture.shutil.which', return_value='synthetic-codex'):
            return run_capture(self.config_path, self.cwd, self.prompt_file,
                               launcher=kwargs.pop('launcher', self.launcher()), **kwargs)

    def test_stages_frozen_metadata_and_differentiates_claims(self):
        result = self.stage()
        self.assertEqual(result['status'], 'STAGED')
        md = (self.root / result['proposal']).read_text(encoding='utf-8')
        for value in ('review_state: "candidate"', 'external_processing: false',
                      '**user-stated**', '**summary-derived**', '**inferred**', 'as_of: null'):
            self.assertIn(value, md)
        self.assertFalse(result['domain_claims_independently_verified'])
        self.assertEqual(result['observed_runner_facts']['process_exit_code'], 0)
        self.assertIn('#L3/item/item_1', result['source'])

    def test_exact_source_replay_changes_nothing(self):
        self.stage()
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = self.stage()
        self.assertEqual(result['status'], 'DUPLICATE_SOURCE')
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_repeated_sessions_reuse_content_and_keep_both_provenances(self):
        first = self.stage()
        raw, final = self.output('fixture-session-2')
        second = self.stage(raw, final)
        self.assertEqual(second['status'], 'CONTENT_REUSED')
        self.assertEqual(first['proposal'], second['proposal'])
        self.assertNotEqual(first['source'], second['source'])
        self.assertEqual(len(list((self.root / 'staging/codex-capture/receipts').glob('*.json'))), 2)

    def test_changed_report_keeps_separate_revision(self):
        first = self.stage()
        report = copy.deepcopy(self.report)
        report['items'][0]['text'] = 'A changed synthetic outcome was reported.'
        second = self.stage(*self.output('fixture-session-2', report))
        self.assertNotEqual(first['proposal'], second['proposal'])

    def test_object_key_order_does_not_duplicate_content(self):
        first = self.stage()
        reordered = dict(reversed(list(self.report.items())))
        second = self.stage(*self.output('fixture-session-2', reordered))
        self.assertEqual(second['status'], 'CONTENT_REUSED')
        self.assertEqual(first['proposal'], second['proposal'])

    def test_startup_diagnostics_retained_but_in_turn_error_refused(self):
        raw, final = self.output()
        lines = raw.splitlines(keepends=True)
        warning = b'{"type":"item.completed","item":{"type":"error","message":"fixture startup warning"}}\n'
        result = self.stage(b''.join(lines[:1] + [warning] + lines[1:]), final)
        self.assertEqual(result['startup_diagnostic_count'], 1)
        with self.assertRaisesRegex(CaptureError, 'EVENT_FAILURE'):
            self.stage(b''.join(lines[:2] + [warning] + lines[2:]), final)

    def test_personal_and_synthetic_provenance_do_not_merge(self):
        first = self.stage()
        self.config['source_privacy'] = 'personal'
        second = self.stage(*self.output('fixture-session-2'))
        self.assertNotEqual(first['proposal'], second['proposal'])

    def test_no_items_is_an_explicit_no_proposal(self):
        result = self.stage(*self.output(report={'schema_version': '1.0', 'items': []}))
        self.assertEqual(result['status'], 'NO_MEANINGFUL_OUTCOMES')
        self.assertFalse((self.root / 'test-vault').exists())

    def test_exit_zero_without_completion_is_failure(self):
        raw, final = self.output()
        incomplete = b'\n'.join(raw.splitlines()[:-1]) + b'\n'
        with self.assertRaisesRegex(CaptureError, 'INCOMPLETE'):
            self.stage(incomplete, final)
        self.assertFalse((self.root / 'test-vault').exists())

    def test_failed_process_or_event_is_not_success(self):
        with self.assertRaisesRegex(CaptureError, 'PROCESS_FAILED'):
            self.stage(exit_code=1)
        raw, final = self.output()
        raw += b'{"type":"turn.failed"}\n'
        with self.assertRaisesRegex(CaptureError, 'EVENT_FAILURE'):
            self.stage(raw, final)

    def test_final_file_must_match_actual_source_item(self):
        raw, _ = self.output()
        with self.assertRaisesRegex(CaptureError, 'NOT_IN_EVENT_STREAM'):
            self.stage(raw, json_bytes({'schema_version': '1.0', 'items': []}))

    def test_user_claim_needs_exact_request_quote(self):
        report = copy.deepcopy(self.report)
        report['items'][1]['text'] = 'An unsupported claim.'
        with self.assertRaisesRegex(CaptureError, 'UNSUPPORTED_USER_CLAIM'):
            self.stage(*self.output(report=report))

    def test_invalid_report_kinds_extra_paths_and_duplicates_are_refused(self):
        for mutation in ('kind', 'path', 'duplicate'):
            report = copy.deepcopy(self.report)
            if mutation == 'kind':
                report['items'][0]['kind'] = []
            elif mutation == 'path':
                report['proposal_path'] = '../outside.md'
            else:
                report['items'].append(report['items'][0])
            with self.subTest(mutation=mutation), self.assertRaises(CaptureError):
                self.stage(*self.output(report=report))

    def test_privacy_filter_blocks_batch_and_does_not_echo_values(self):
        secrets = ['ghp_' + 'x' * 30, 'fixture' + '@' + 'example.test', 'password=' + 'not-a-real-key',
                   'C:' + '/Users/' + 'Example/private-note.md']
        for secret in secrets:
            with self.subTest(category=secret.split(':')[0]), self.assertRaises(CaptureError) as error:
                privacy_check(secret)
            self.assertNotIn(secret, str(error.exception))
        report = copy.deepcopy(self.report)
        report['items'][-1]['text'] = secrets[0]
        with self.assertRaisesRegex(CaptureError, 'PRIVACY'):
            self.stage(*self.output(report=report))
        self.assertFalse((self.root / 'test-vault').exists())

    def test_blank_jsonl_lines_and_malformed_shapes_are_refused(self):
        raw, final = self.output()
        for invalid in (b'\n' + raw, b'[]\n', b'not-json\n'):
            with self.subTest(raw=invalid[:10]), self.assertRaises(CaptureError):
                self.stage(invalid, final)

    def test_tampered_receipt_cannot_redirect_reads(self):
        self.stage()
        receipt = next((self.root / 'staging/codex-capture/receipts').glob('*.json'))
        value = json.loads(receipt.read_bytes())
        value['candidate'] = '../../outside.json'
        receipt.write_bytes(json_bytes(value))
        with self.assertRaisesRegex(CaptureError, 'RECEIPT_MISMATCH'):
            self.stage()

    def test_changed_proposal_is_not_overwritten(self):
        first = self.stage()
        path = self.root / first['proposal']
        path.write_text('owner edited candidate', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.stage()
        self.assertEqual(path.read_text(), 'owner edited candidate')

    def test_workspace_inside_git_or_onedrive_is_refused_before_write(self):
        for name in ('git-root', 'OneDrive'):
            path = Path(self.temp.name) / name
            path.mkdir()
            (path / '.private-staging.json').write_bytes(json_bytes({'live_writes': False, 'external_exports': False}))
            if name == 'git-root':
                (path / '.git').mkdir()
            self.config['workspace'] = str(path)
            self.save_config()
            with self.subTest(root=name), self.assertRaises(CaptureError):
                load_config(self.config_path)
            self.assertFalse((path / 'staging').exists())

    def test_fixture_process_end_to_end_and_replay(self):
        result = self.run_fixture()
        self.assertEqual(result['status'], 'STAGED')
        repeated = replay_capture(self.config_path, result['run_directory'])
        self.assertEqual(repeated['status'], 'DUPLICATE_SOURCE')

    def test_process_failure_is_journaled_and_not_replayable(self):
        result = self.run_fixture(launcher=self.launcher(exit_code=7))
        self.assertEqual(result['status'], 'FAILED')
        job = json.loads((Path(result['run_directory']) / 'job.json').read_bytes())
        self.assertEqual(job['codex_exit_code'], 7)
        with self.assertRaisesRegex(CaptureError, 'NOT_REPLAYABLE'):
            replay_capture(self.config_path, result['run_directory'])

    def test_incomplete_fixture_process_is_journaled(self):
        result = self.run_fixture(launcher=self.launcher(incomplete=True))
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('INCOMPLETE', result['error_code'])

    def test_disabled_never_launches_and_can_be_reenabled(self):
        set_enabled(self.config_path, False)
        self.assertEqual(self.run_fixture(launcher=lambda *a: self.fail('launched'))['status'], 'DISABLED')
        set_enabled(self.config_path, True)
        self.assertEqual(self.run_fixture()['status'], 'STAGED')

    def test_disable_during_run_prevents_staging(self):
        result = self.run_fixture(launcher=self.launcher(mutate=lambda: set_enabled(self.config_path, False)))
        self.assertEqual(result['status'], 'DISABLED_AFTER_RUN')
        self.assertFalse((self.root / 'test-vault').exists())

    def test_config_change_during_run_refused(self):
        def mutate():
            self.config['source_privacy'] = 'personal'
            self.save_config()
        result = self.run_fixture(launcher=self.launcher(mutate=mutate))
        self.assertEqual(result['error_code'], 'CONFIG_CHANGED_DURING_RUN')
        self.assertFalse((self.root / 'test-vault').exists())

    def test_missing_or_changed_profile_refused_before_launch(self):
        self.profile.write_bytes(b'changed profile')
        with self.assertRaisesRegex(CaptureError, 'PROFILE_CHANGED'):
            self.run_fixture(launcher=lambda *a: self.fail('launched'))
        self.profile.unlink()
        with self.assertRaisesRegex(CaptureError, 'PROFILE_MISSING'):
            self.run_fixture(launcher=lambda *a: self.fail('launched'))

    def test_profile_change_during_run_refused(self):
        result = self.run_fixture(launcher=self.launcher(mutate=lambda: self.profile.write_bytes(b'changed')))
        self.assertEqual(result['error_code'], 'PROFILE_CHANGED')
        self.assertFalse((self.root / 'test-vault').exists())

    def test_timeout_is_journaled_without_proposal(self):
        def timeout(*args):
            raise CaptureError('CODEX_TIMEOUT_OR_INTERRUPTED')
        result = self.run_fixture(launcher=timeout)
        self.assertEqual(result['status'], 'FAILED')
        self.assertEqual(result['error_code'], 'CODEX_TIMEOUT_OR_INTERRUPTED')
        self.assertFalse((self.root / 'test-vault').exists())

    def test_privacy_prompt_refused_before_launch(self):
        self.prompt_file.write_text('password=' + 'not-a-real-key', encoding='utf-8')
        with self.assertRaisesRegex(CaptureError, 'PRIVACY'):
            self.run_fixture(launcher=lambda *a: self.fail('launched'))

    def test_unauthorized_cwd_and_prompt_are_refused_before_launch(self):
        with patch('run_codex_capture.shutil.which', return_value='fixture'):
            with self.assertRaisesRegex(CaptureError, 'CWD_NOT_AUTHORIZED'):
                run_capture(self.config_path, self.root, self.prompt_file, launcher=lambda *a: self.fail('launched'))
            outside = Path(self.temp.name) / 'outside.txt'
            outside.write_text('not authorized', encoding='utf-8')
            with self.assertRaisesRegex(CaptureError, 'PROMPT_NOT_IN_PRIVATE'):
                run_capture(self.config_path, self.cwd, outside, launcher=lambda *a: self.fail('launched'))

    def test_busy_or_crashed_lock_is_not_bypassed(self):
        directory = self.root / 'staging/codex-capture'
        directory.mkdir(parents=True)
        lock = directory / '.capture-lock'
        lock.write_bytes(b'other process')
        with self.assertRaisesRegex(CaptureError, 'BUSY_OR_STALE_LOCK'):
            self.run_fixture()
        self.assertEqual(lock.read_bytes(), b'other process')

    def test_replay_outside_run_area_and_changed_raw_are_refused(self):
        with self.assertRaisesRegex(CaptureError, 'RUN_DIRECTORY_NOT_AUTHORIZED'):
            replay_capture(self.config_path, self.cwd)
        result = self.run_fixture()
        (Path(result['run_directory']) / 'events.jsonl').write_bytes(b'changed')
        with self.assertRaisesRegex(CaptureError, 'RAW_SOURCE_CHANGED'):
            replay_capture(self.config_path, result['run_directory'])

    def test_r1_quoted_assignments_refused_before_child(self):
        fixtures = [json.dumps({key: 'SYNTHETIC_CREDENTIAL_ONLY'})
                    for key in ('api_key', 'password', 'access_token', 'secret')]
        fixtures += ["'password' = 'synthetic short value'", '"api-key": "x"',
                     r'{"pass\u0077ord": "SYNTHETIC_ONLY"}',
                     r'Configuration: {\"password\": \"SYNTHETIC_ONLY\"}']
        for text in fixtures:
            with self.subTest(fixture=text):
                self.prompt_file.write_text(text, encoding='utf-8')
                with self.assertRaisesRegex(CaptureError, 'PRIVACY_SECRET_ASSIGNMENT'):
                    self.run_fixture(launcher=lambda *a: self.fail('child launched'))
        self.assertFalse((self.root / 'staging').exists())

    def test_r1_report_text_and_quotes_block_entire_batch(self):
        for field in ('text', 'source_quote'):
            for key in ('api_key', 'password', 'access_token', 'secret'):
                report = copy.deepcopy(self.report)
                report['items'][-1][field] = 'Configuration: ' + json.dumps({key: 'SYNTHETIC_ONLY'})
                with self.subTest(field=field, key=key):
                    result = self.run_fixture(launcher=self.launcher(report=report))
                    self.assertEqual(result['error_code'], 'PRIVACY_SECRET_ASSIGNMENT')
                    self.assertFalse((self.root / 'test-vault').exists())
                    self.assertFalse((self.root / 'archive').exists())

    def test_r1_untrusted_source_identifiers_filtered(self):
        raw, final = self.output()
        for location in ('session', 'item'):
            events = [json.loads(line) for line in raw.splitlines()]
            fake = 'ghp_' + 'x' * 30
            if location == 'session':
                events[0]['thread_id'] = fake
            else:
                events[2]['item']['id'] = fake
            with self.subTest(location=location), self.assertRaisesRegex(CaptureError, 'PRIVACY'):
                self.stage(b''.join(json.dumps(event).encode() + b'\n' for event in events), final)
        self.assertFalse((self.root / 'test-vault').exists())

    def test_r2_complete_candidate_reconstructed_on_replay_and_reuse(self):
        first = self.run_fixture()
        path, note = self.root / first['candidate'], self.root / first['proposal']
        original, markdown = path.read_bytes(), note.read_bytes()
        receipt_path = next((self.root / 'staging/codex-capture/receipts').glob('*.json'))
        original_receipt = receipt_path.read_bytes()
        for field in ('claim_text', 'evidence', 'locator', 'sources', 'body', 'metadata', 'report', 'extra'):
            candidate = json.loads(original)
            if field == 'claim_text':
                candidate['claims'][0]['text'] = 'All production acceptance tests passed.'
            elif field == 'evidence':
                candidate['claims'][0]['evidence'] = 'observed'
            elif field == 'locator':
                candidate['claims'][0]['locator'] = 'archive/nonexistent.jsonl#L1'
            elif field == 'sources':
                candidate['sources'] = ['archive/nonexistent.jsonl#L1']
            elif field == 'body':
                candidate['body'] = 'Acceptance has been approved.'
            elif field == 'metadata':
                candidate['as_of'] = '2026-10-24'
            elif field == 'report':
                candidate['capture_report']['items'][0]['text'] = 'A mismatched report.'
            else:
                candidate['unreviewed_extra'] = 'unexpected data'
            path.write_bytes(json_bytes(candidate))
            # Even recomputing a raw candidate hash cannot bless fabricated claims.
            receipt = json.loads(original_receipt)
            receipt['candidate_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            receipt_path.write_bytes(json_bytes(receipt))
            note.unlink()
            with self.subTest(field=field, branch='replay'), self.assertRaises(CaptureError):
                replay_capture(self.config_path, first['run_directory'])
            with self.subTest(field=field, branch='reuse'):
                result = self.run_fixture(launcher=self.launcher(session='fixture-session-2'))
                self.assertEqual(result['status'], 'FAILED')
                self.assertFalse(note.exists(), 'must not render a cached claim after corruption')
            path.write_bytes(original)
            note.write_bytes(markdown)
            receipt_path.write_bytes(original_receipt)

    def test_r2_missing_markdown_and_candidate_fail_closed(self):
        first = self.run_fixture()
        for key in ('proposal', 'candidate'):
            path = self.root / first[key]
            saved = path.read_bytes()
            path.unlink()
            with self.subTest(missing=key), self.assertRaises(CaptureError):
                replay_capture(self.config_path, first['run_directory'])
            result = self.run_fixture(launcher=self.launcher(session='fixture-session-2'))
            self.assertEqual(result['status'], 'FAILED')
            self.assertFalse(path.exists(), 'missing cached state must not be silently recreated')
            path.write_bytes(saved)

    def test_r3_missing_or_changed_archives_refuse_replay_and_reuse(self):
        first = self.run_fixture()
        original_receipt = next((self.root / 'staging/codex-capture/receipts').glob('*.json')).read_bytes()
        for kind in ('events', 'final', 'prompt'):
            sha = first[kind + '_sha256']
            suffix = {'events': 'codex-events.jsonl', 'final': 'codex-final.json', 'prompt': 'codex-prompt.txt'}[kind]
            archive = self.root / 'archive' / (sha + '.' + suffix)
            saved = archive.read_bytes()
            for mode in ('delete', 'alter'):
                if mode == 'delete':
                    archive.unlink()
                else:
                    archive.write_bytes(b'changed unrelated synthetic evidence')
                with self.subTest(kind=kind, mode=mode, branch='replay'), self.assertRaisesRegex(CaptureError, 'ARCHIVE'):
                    replay_capture(self.config_path, first['run_directory'])
                with self.subTest(kind=kind, mode=mode, branch='reuse'):
                    result = self.run_fixture(launcher=self.launcher(session='fixture-session-2'))
                    self.assertEqual(result['status'], 'FAILED')
                    self.assertEqual(len(list((self.root / 'staging/codex-capture/receipts').glob('*.json'))), 1)
                    if mode == 'delete':
                        self.assertFalse(archive.exists())
                    else:
                        self.assertEqual(archive.read_bytes(), b'changed unrelated synthetic evidence')
                archive.write_bytes(saved)
        self.assertEqual(next((self.root / 'staging/codex-capture/receipts').glob('*.json')).read_bytes(), original_receipt)

    def test_r3_receipt_identity_and_source_locator_verified(self):
        first = self.run_fixture()
        path = next((self.root / 'staging/codex-capture/receipts').glob('*.json'))
        saved = path.read_bytes()
        for key, value in [('source', first['source'].replace('#L3/', '#L99/')),
                           ('session_id', 'unrelated-session'), ('prompt_sha256', '0' * 64),
                           ('observed_runner_facts', {'process_exit_code': 0, 'turn_completed': False}),
                           ('external_processing', True), ('unexpected', 'extra metadata')]:
            receipt = json.loads(saved)
            receipt[key] = value
            path.write_bytes(json_bytes(receipt))
            with self.subTest(key=key), self.assertRaises(CaptureError):
                replay_capture(self.config_path, first['run_directory'])
            result = self.run_fixture(launcher=self.launcher(session='fixture-session-2'))
            self.assertEqual(result['status'], 'FAILED')
            path.write_bytes(saved)

    def test_r3_unrelated_valid_source_cannot_be_substituted(self):
        first = self.run_fixture()
        changed = copy.deepcopy(self.report)
        changed['items'][0]['text'] = 'Unrelated synthetic work.'
        other = self.run_fixture(launcher=self.launcher(session='unrelated-session', report=changed))
        path = self.root / first['candidate']
        candidate = json.loads(path.read_bytes())
        candidate['sources'] = [other['source']]
        path.write_bytes(json_bytes(candidate))
        with self.assertRaisesRegex(CaptureError, 'CANDIDATE_MISMATCH'):
            replay_capture(self.config_path, first['run_directory'])
        result = self.run_fixture(launcher=self.launcher(session='fixture-session-2'))
        self.assertEqual(result['status'], 'FAILED')

    def test_r3_reused_receipt_checks_both_current_and_original_sources(self):
        first = self.run_fixture()
        second = self.run_fixture(launcher=self.launcher(session='fixture-session-2'))
        self.assertEqual(second['status'], 'CONTENT_REUSED')
        self.assertEqual(replay_capture(self.config_path, second['run_directory'])['status'], 'DUPLICATE_SOURCE')
        (self.root / first['source'].split('#')[0]).unlink()
        with self.assertRaisesRegex(CaptureError, 'ARCHIVE'):
            replay_capture(self.config_path, second['run_directory'])

    def test_r3_old_or_missing_receipts_not_silently_upgraded(self):
        first = self.run_fixture()
        path = next((self.root / 'staging/codex-capture/receipts').glob('*.json'))
        original = path.read_bytes()
        value = json.loads(original)
        del value['final_sha256']
        path.write_bytes(json_bytes(value))
        with self.assertRaisesRegex(CaptureError, 'RECEIPT_MISMATCH'):
            replay_capture(self.config_path, first['run_directory'])
        path.unlink()
        with self.assertRaises(CaptureError):
            replay_capture(self.config_path, first['run_directory'])
        self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
