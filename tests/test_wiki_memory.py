from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from wiki_memory import (
    WikiMemoryError,
    deterministic_claim_id,
    deterministic_note_id,
    integrate_cross_session_knowledge,
    load_local_read_corpus,
    merge_session_claims,
    render_managed_index_routes,
    render_managed_log_entries,
    render_wiki_knowledge_note,
    resolve_wikilinks,
    restore_managed_preimage,
    route_claim,
    sanitize_model_output,
    update_managed_section,
    validate_wiki_relpath,
)


class Slice1RoutingAndMatchingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.vault = self.root / 'test-vault'
        self.vault.mkdir()

    def _write_note(self, relpath, title, headings=(), privacy='synthetic'):
        path = self.vault.joinpath(*relpath.split('/'))
        path.parent.mkdir(parents=True, exist_ok=True)
        body_headings = '\n\n'.join(f'## {h}\nContent for {h}.' for h in headings)
        content = (
            '---\n'
            f'title: "{title}"\n'
            f'privacy: "{privacy}"\n'
            'external_processing: false\n'
            '---\n\n'
            f'# {title}\n\n'
            f'{body_headings}\n'
        ).encode('utf-8')
        path.write_bytes(content)
        return path, content

    def test_deterministic_ids_are_stable_and_normalized(self):
        nid1 = deterministic_note_id('project', 'Alpha Tooling', ' Lock Protocol ')
        nid2 = deterministic_note_id('project', 'alpha-tooling', 'lock-protocol')
        self.assertEqual(nid1, nid2)
        self.assertTrue(nid1.startswith('project-alpha-tooling-lock-protocol-'))

        cid1 = deterministic_claim_id('lock-protocol', 'Use   atomic  rename\non Windows. ')
        cid2 = deterministic_claim_id('LOCK-PROTOCOL', 'use atomic rename on windows.')
        self.assertEqual(cid1, cid2)
        self.assertTrue(cid1.startswith('claim-'))

    def test_route_claim_maps_project_lesson_and_session_targets(self):
        lesson_claim = {
            'kind': 'lesson',
            'topic': 'Windows File Locking',
            'text': 'Share-zero handles block os.replace on the same file.',
        }
        routed_lesson = route_claim(lesson_claim, project_slug='second-brain', project_id='a' * 64)
        self.assertEqual(routed_lesson['target_kind'], 'lesson')
        self.assertEqual(routed_lesson['relative_path'], 'permanent/engineering/windows-file-locking.md')

        decision_claim = {
            'kind': 'decision',
            'topic': 'Manifest Pointer',
            'text': 'Use content-addressed manifest files with atomic pointer swap.',
        }
        routed_project = route_claim(decision_claim, project_slug='second-brain', project_id='b' * 64)
        self.assertEqual(routed_project['target_kind'], 'project')
        self.assertEqual(routed_project['relative_path'], 'projects/second-brain/manifest-pointer.md')
        self.assertEqual(routed_project['session_hub_path'], 'projects/second-brain/index.md')

    def test_validate_wiki_relpath_rejects_traversal_backslashes_and_prefixes(self):
        self.assertEqual(
            validate_wiki_relpath('projects/second-brain/manifest-pointer.md'),
            'projects/second-brain/manifest-pointer.md',
        )
        invalid_paths = [
            '../secret.md',
            'projects/../../secret.md',
            'projects\\second-brain\\note.md',
            'C:/vault/note.md',
            '//server/share/note.md',
            '/absolute/note.md',
            '.obsidian/workspace.md',
            '.git/config.md',
            'projects/CON.md',
            'projects/note.txt',
        ]
        for bad in invalid_paths:
            with self.subTest(bad=bad):
                with self.assertRaises(WikiMemoryError):
                    validate_wiki_relpath(bad)

    def test_conservative_matching_links_unambiguous_and_skips_ambiguous(self):
        self._write_note(
            'projects/second-brain/manifest-pointer.md',
            'Manifest Pointer Architecture',
            headings=('Atomic Swap', 'Recovery'),
        )
        self._write_note(
            'permanent/engineering/atomic-writes.md',
            'Atomic Writes Guide',
            headings=('Overview',),
        )
        # Two notes sharing the same normalized topic/alias "caching" -> ambiguous
        self._write_note('projects/second-brain/caching.md', 'Caching Strategy')
        self._write_note('permanent/engineering/caching.md', 'Caching Strategy')

        allowed_notes = [
            {
                'id': 'note-manifest',
                'path': 'projects/second-brain/manifest-pointer.md',
                'title': 'Manifest Pointer Architecture',
                'headings': ['Atomic Swap', 'Recovery'],
                'privacy': 'synthetic',
            },
            {
                'id': 'note-atomic',
                'path': 'permanent/engineering/atomic-writes.md',
                'title': 'Atomic Writes Guide',
                'headings': ['Overview'],
                'privacy': 'synthetic',
            },
            {
                'id': 'note-cache-1',
                'path': 'projects/second-brain/caching.md',
                'title': 'Caching Strategy',
                'headings': [],
                'privacy': 'synthetic',
            },
            {
                'id': 'note-cache-2',
                'path': 'permanent/engineering/caching.md',
                'title': 'Caching Strategy',
                'headings': [],
                'privacy': 'synthetic',
            },
        ]

        candidates = [
            {'query': 'Manifest Pointer Architecture', 'heading': 'Atomic Swap', 'label': 'atomic pointer swap'},
            {'query': 'permanent/engineering/atomic-writes.md', 'label': 'Atomic Writes'},
            {'query': 'Caching Strategy', 'label': 'caching'},
            {'query': 'Nonexistent Topic', 'label': 'ghost'},
            {'query': 'Manifest Pointer Architecture', 'heading': 'Missing Heading', 'label': 'bad heading'},
        ]

        res = resolve_wikilinks(candidates, allowed_notes=allowed_notes, vault_root=self.vault)
        self.assertEqual(
            res['linked'],
            [
                {
                    'query': 'Manifest Pointer Architecture',
                    'target_id': 'note-manifest',
                    'wikilink': '[[projects/second-brain/manifest-pointer#Atomic Swap|atomic pointer swap]]',
                },
                {
                    'query': 'permanent/engineering/atomic-writes.md',
                    'target_id': 'note-atomic',
                    'wikilink': '[[permanent/engineering/atomic-writes|Atomic Writes]]',
                },
            ],
        )
        skipped_reasons = {item['query'] + ('#' + item['heading'] if item.get('heading') else ''): item['reason']
                           for item in res['skipped']}
        self.assertEqual(skipped_reasons['Caching Strategy'], 'AMBIGUOUS_MATCH')
        self.assertEqual(skipped_reasons['Nonexistent Topic'], 'NO_MATCH')
        self.assertEqual(skipped_reasons['Manifest Pointer Architecture#Missing Heading'], 'MISSING_HEADING')

    def test_resolve_wikilinks_rejects_symlink_or_out_of_root_note(self):
        outside = self.root / 'outside'
        outside.mkdir()
        outside_file = outside / 'escaped.md'
        outside_file.write_bytes(b'---\ntitle: "Escaped"\n---\n# Escaped\n')
        link_path = self.vault / 'projects' / 'escaped.md'
        link_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            link_path.symlink_to(outside_file)
        except OSError:
            self.skipTest('Windows symlink creation privilege unavailable')

        allowed_notes = [
            {
                'id': 'note-escaped',
                'path': 'projects/escaped.md',
                'title': 'Escaped',
                'headings': [],
                'privacy': 'synthetic',
            }
        ]
        with self.assertRaises(WikiMemoryError):
            resolve_wikilinks([{'query': 'Escaped'}], allowed_notes=allowed_notes, vault_root=self.vault)


class Slice2DeduplicationAndHistoryTests(unittest.TestCase):
    def test_repeated_normalized_claims_deduplicate_prose_and_preserve_provenance(self):
        claim_session_1 = {
            'subject_key': 'manifest-pointer',
            'kind': 'decision',
            'text': 'Use content-addressed manifest files with atomic pointer swap.',
            'status': 'reported-completed',
            'evidence': 'summary-derived',
            'date': '2026-11-01T10:00:00+00:00',
            'session_reference': 'sess-001',
            'role': 'planner',
            'locator': 'archive/sha1.json#/context_summary/items/0',
            'privacy': 'synthetic',
        }
        claim_session_2 = {
            'subject_key': 'manifest-pointer',
            'kind': 'decision',
            'text': '  use   content-addressed manifest files with atomic pointer swap. ',
            'status': 'reported-completed',
            'evidence': 'observed',
            'date': '2026-11-02T14:30:00+00:00',
            'session_reference': 'sess-002',
            'role': 'implementer',
            'locator': 'archive/sha2.json#/context_summary/items/1',
            'privacy': 'synthetic',
        }

        state = merge_session_claims([], [claim_session_1])
        state = merge_session_claims(state['claims'], [claim_session_2])

        self.assertEqual(len(state['claims']), 1)
        merged = state['claims'][0]
        self.assertEqual(merged['text'], 'Use content-addressed manifest files with atomic pointer swap.')
        self.assertEqual(len(merged['provenance']), 2)
        self.assertEqual(
            [(p['session_reference'], p['role'], p['locator']) for p in merged['provenance']],
            [
                ('sess-001', 'planner', 'archive/sha1.json#/context_summary/items/0'),
                ('sess-002', 'implementer', 'archive/sha2.json#/context_summary/items/1'),
            ],
        )

        rendered = render_wiki_knowledge_note(
            note_id='project-second-brain-manifest-pointer-123456789abc',
            title='Manifest Pointer',
            kind='project',
            privacy='synthetic',
            claims=state['claims'],
        ).decode('utf-8')
        self.assertEqual(
            rendered.count('Use content-addressed manifest files with atomic pointer swap.'),
            1,
        )
        self.assertIn('sess-001 (role=planner', rendered)
        self.assertIn('sess-002 (role=implementer', rendered)

    def test_superseding_and_contradictory_claims_preserve_earlier_history(self):
        early_claim = {
            'subject_key': 'storage-backend',
            'kind': 'decision',
            'text': 'Store local index in SQLite FTS5 table.',
            'status': 'proposed',
            'evidence': 'summary-derived',
            'date': '2026-10-30T09:00:00+00:00',
            'session_reference': 'sess-early',
            'role': 'planner',
            'locator': 'archive/sha_early.json#/context_summary/items/0',
            'privacy': 'synthetic',
        }
        early_id = deterministic_claim_id('storage-backend', early_claim['text'])

        superseding_claim = {
            'subject_key': 'storage-backend',
            'kind': 'decision',
            'text': 'Keep canonical knowledge in Markdown files without a separate database.',
            'status': 'reported-completed',
            'evidence': 'summary-derived',
            'date': '2026-11-02T11:00:00+00:00',
            'session_reference': 'sess-later',
            'role': 'implementer',
            'locator': 'archive/sha_later.json#/context_summary/items/0',
            'privacy': 'synthetic',
            'supersedes': [early_id],
        }

        contradictory_claim = {
            'subject_key': 'storage-backend',
            'kind': 'decision',
            'text': 'Use a hosted cloud vector database for all notes.',
            'status': 'reported-completed',
            'evidence': 'inferred',
            'date': '2026-11-03T12:00:00+00:00',
            'session_reference': 'sess-conflict',
            'role': 'reviewer',
            'locator': 'archive/sha_conflict.json#/context_summary/items/2',
            'privacy': 'synthetic',
        }

        state1 = merge_session_claims([], [early_claim])
        state2 = merge_session_claims(state1['claims'], [superseding_claim])
        self.assertEqual(len(state2['claims']), 2)
        by_id = {c['claim_id']: c for c in state2['claims']}
        self.assertEqual(by_id[early_id]['lifecycle'], 'superseded')
        self.assertEqual(by_id[early_id]['superseded_by'], [state2['claims'][1]['claim_id']])
        self.assertEqual(state2['claims'][1]['lifecycle'], 'active')

        # Now feed an unapproved contradictory claim on the same subject without explicit supersedes
        state3 = merge_session_claims(state2['claims'], [contradictory_claim])
        self.assertEqual(len(state3['quarantined']), 1)
        self.assertEqual(state3['quarantined'][0]['reason'], 'CONTRADICTORY_CLAIM_QUARANTINED')
        # Earlier claims remain intact and dated
        self.assertEqual(len(state3['claims']), 2)
        rendered = render_wiki_knowledge_note(
            note_id='project-second-brain-storage-backend-123456789abc',
            title='Storage Backend',
            kind='project',
            privacy='synthetic',
            claims=state3['claims'],
            quarantined=state3['quarantined'],
        ).decode('utf-8')
        self.assertIn('Store local index in SQLite FTS5 table.', rendered)
        self.assertIn('2026-10-30T09:00:00+00:00', rendered)
        self.assertIn('superseded', rendered)
        self.assertIn('Keep canonical knowledge in Markdown files without a separate database.', rendered)


class Slice3ManagedIndexAndLogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.vault = self.root / 'test-vault'
        self.private = self.root / 'private'
        self.vault.mkdir()
        self.private.mkdir()
        (self.private / '.private-staging.json').write_text(
            '{"live_writes": false, "external_exports": false}',
            encoding='utf-8',
        )

        self.initial_index = (
            '---\n'
            'title: Second Brain index\n'
            'tags:\n'
            '  - brain/navigation\n'
            '---\n\n'
            '# Second Brain index\n\n'
            'Start with [[system/brain|the operating guide]] and see [[log|the change log]].\n'
            'UNMANAGED_HEADER_CANARY_BYTES_12345\n\n'
            '## Knowledge routes\n\n'
            '<!-- brain-managed:start section="index-routes" -->\n'
            '| Existing folder | Purpose | Navigation |\n'
            '| --- | --- | --- |\n'
            '| `projects/` | Project context, decisions and current status | Add permitted project hubs when available |\n'
            '| `permanent/` | Reusable lessons with evidence | Add permitted topic hubs when available |\n'
            '| `references/` | Selected source summaries and citations | Add permitted references when available |\n'
            '| `logs/` | Dated session summaries | Add permitted summaries when available |\n'
            '<!-- brain-managed:end section="index-routes" -->\n\n'
            'Keep this index small. UNMANAGED_FOOTER_CANARY_BYTES_67890\n'
        ).encode('utf-8')
        (self.vault / 'index.md').write_bytes(self.initial_index)

        self.initial_log = (
            '---\n'
            'title: Second Brain change log\n'
            'tags:\n'
            '  - brain/navigation\n'
            '---\n\n'
            '# Second Brain change log\n\n'
            'See [[system/brain|the operating guide]] and [[index|knowledge routes]].\n\n'
            '<!-- brain-managed:start section="change-log" -->\n'
            '- No managed changes recorded yet.\n'
            '<!-- brain-managed:end section="change-log" -->\n\n'
            'Footer note that must survive unchanged.\n'
        ).encode('utf-8')
        (self.vault / 'log.md').write_bytes(self.initial_log)

    def test_update_index_and_log_preserves_unmanaged_bytes_and_replays_cleanly(self):
        import hashlib
        pre_hash = hashlib.sha256(self.initial_index).hexdigest()
        new_table = render_managed_index_routes({
            'projects/': [
                {'path': 'projects/second-brain/index.md', 'label': 'Second Brain hub'},
            ],
            'permanent/': [
                {'path': 'permanent/engineering/windows-file-locking.md', 'label': 'Windows File Locking'},
            ],
        })
        res = update_managed_section(
            private_dir=self.private,
            vault_dir=self.vault,
            relative_path='index.md',
            section='index-routes',
            expected_preimage_sha256=pre_hash,
            new_section_body=new_table,
        )
        self.assertEqual(res['status'], 'UPDATED')
        updated_text = (self.vault / 'index.md').read_bytes().decode('utf-8')
        self.assertIn('UNMANAGED_HEADER_CANARY_BYTES_12345', updated_text)
        self.assertIn('UNMANAGED_FOOTER_CANARY_BYTES_67890', updated_text)
        self.assertIn('[[projects/second-brain/index|Second Brain hub]]', updated_table := updated_text)
        self.assertIn('[[permanent/engineering/windows-file-locking|Windows File Locking]]', updated_table)

        # Replay of identical intent returns NO_CHANGE
        replay = update_managed_section(
            private_dir=self.private,
            vault_dir=self.vault,
            relative_path='index.md',
            section='index-routes',
            expected_preimage_sha256=pre_hash,
            new_section_body=new_table,
        )
        self.assertEqual(replay['status'], 'NO_CHANGE')

        # Log update check
        log_pre_hash = hashlib.sha256(self.initial_log).hexdigest()
        log_body = render_managed_log_entries([
            {
                'timestamp': '2026-11-06T09:15:00+00:00',
                'operation': 'SAVED',
                'note_links': ['[[projects/second-brain/manifest-pointer|Manifest Pointer]]'],
                'locator': 'publications/pol-1/transactions/tx-1/receipt.json',
                'verification': 'LOCAL_BYTES_VERIFIED',
            }
        ])
        log_res = update_managed_section(
            private_dir=self.private,
            vault_dir=self.vault,
            relative_path='log.md',
            section='change-log',
            expected_preimage_sha256=log_pre_hash,
            new_section_body=log_body,
        )
        self.assertEqual(log_res['status'], 'UPDATED')
        log_text = (self.vault / 'log.md').read_bytes().decode('utf-8')
        self.assertIn('Footer note that must survive unchanged.', log_text)
        self.assertIn('[[projects/second-brain/manifest-pointer|Manifest Pointer]]', log_text)

    def test_refuses_stale_hash_and_malformed_markers(self):
        with self.assertRaises(WikiMemoryError) as ctx:
            update_managed_section(
                private_dir=self.private,
                vault_dir=self.vault,
                relative_path='index.md',
                section='index-routes',
                expected_preimage_sha256='0' * 64,
                new_section_body='| Existing folder | Purpose | Navigation |\n',
            )
        self.assertEqual(ctx.exception.error_code, 'STALE_PREIMAGE_HASH')
        self.assertEqual((self.vault / 'index.md').read_bytes(), self.initial_index)

        # Missing/malformed section marker
        import hashlib
        pre_hash = hashlib.sha256(self.initial_index).hexdigest()
        with self.assertRaises(WikiMemoryError) as ctx2:
            update_managed_section(
                private_dir=self.private,
                vault_dir=self.vault,
                relative_path='index.md',
                section='nonexistent-section',
                expected_preimage_sha256=pre_hash,
                new_section_body='replacement',
            )
        self.assertEqual(ctx2.exception.error_code, 'MALFORMED_MANAGED_MARKERS')

    def test_interrupted_update_recovers_and_later_owner_edit_refuses_overwrite(self):
        import hashlib
        from unittest.mock import patch
        import wiki_memory as wm

        pre_hash = hashlib.sha256(self.initial_index).hexdigest()
        new_table = render_managed_index_routes({
            'projects/': [{'path': 'projects/second-brain/index.md', 'label': 'Second Brain hub'}],
        })

        # Simulate interruption right when replace_pointer is called (after journal write, before target replace)
        with patch.object(wm, 'replace_pointer', side_effect=OSError('simulated crash before replace')):
            with self.assertRaises(WikiMemoryError) as ctx:
                update_managed_section(
                    private_dir=self.private,
                    vault_dir=self.vault,
                    relative_path='index.md',
                    section='index-routes',
                    expected_preimage_sha256=pre_hash,
                    new_section_body=new_table,
                )
            self.assertEqual(ctx.exception.error_code, 'MANAGED_UPDATE_INTERRUPTED')

        # Target is still preimage; retry recovers and completes the update
        recovered = update_managed_section(
            private_dir=self.private,
            vault_dir=self.vault,
            relative_path='index.md',
            section='index-routes',
            expected_preimage_sha256=pre_hash,
            new_section_body=new_table,
        )
        self.assertEqual(recovered['status'], 'RECOVERED')
        self.assertEqual(recovered['recovery_stage'], 'APPLIED_FROM_PREIMAGE')

        # If owner edits index.md later, conditional restore or replay refuses to clobber owner edit
        owner_bytes = (self.vault / 'index.md').read_bytes() + b'\nOwner manual note.\n'
        (self.vault / 'index.md').write_bytes(owner_bytes)
        with self.assertRaises(WikiMemoryError) as ctx_conflict:
            restore_managed_preimage(
                private_dir=self.private,
                vault_dir=self.vault,
                transaction_id=recovered['transaction_id'],
            )
        self.assertEqual(ctx_conflict.exception.error_code, 'LATER_EDIT_CONFLICT')
        self.assertEqual((self.vault / 'index.md').read_bytes(), owner_bytes)


class Slice4DeniedNoteCanaryAndSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.vault = self.root / 'test-vault'
        self.private = self.root / 'private'
        self.vault.mkdir()
        self.private.mkdir()
        (self.private / '.private-staging.json').write_text(
            '{"live_writes": false, "external_exports": false}',
            encoding='utf-8',
        )

    def _create_vault_note(self, relpath, note_id, title, body, privacy='synthetic', external_processing=False):
        import hashlib
        import json
        path = self.vault.joinpath(*relpath.split('/'))
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = (
            '---\n'
            f'id: {json.dumps(note_id)}\n'
            f'title: {json.dumps(title)}\n'
            f'privacy: {json.dumps(privacy)}\n'
            f'external_processing: {json.dumps(external_processing)}\n'
            '---\n\n'
            f'# {title}\n\n'
            f'{body}\n'
        ).encode('utf-8')
        path.write_bytes(raw)
        return {
            'id': note_id,
            'path': relpath,
            'sha256': hashlib.sha256(raw).hexdigest(),
            'size': len(raw),
            'privacy': privacy,
            'external_processing': external_processing,
        }

    def test_denied_content_canary_never_read_linked_or_leaked(self):
        import json

        allowed_meta = self._create_vault_note(
            'projects/alpha/architecture.md',
            'note-allowed-arch',
            'Alpha Architecture',
            '## Overview\nApproved synthetic architecture note.',
            privacy='synthetic',
            external_processing=False,
        )
        denied_personal = self._create_vault_note(
            'projects/alpha/personal-diary.md',
            'note-denied-personal',
            'DENIED_CONTENT_CANARY_TITLE_PERSONAL',
            '## Secret Section\nDENIED_CONTENT_CANARY_BODY_PERSONAL_999',
            privacy='personal',
            external_processing=False,
        )
        denied_unselected = self._create_vault_note(
            'projects/other-secret/unselected.md',
            'note-denied-unselected',
            'DENIED_CONTENT_CANARY_TITLE_UNSELECTED',
            '## Hidden\nDENIED_CONTENT_CANARY_BODY_UNSELECTED_888',
            privacy='synthetic',
            external_processing=False,
        )
        denied_restricted = self._create_vault_note(
            'projects/alpha/restricted-keys.md',
            'note-denied-restricted',
            'DENIED_CONTENT_CANARY_TITLE_RESTRICTED',
            '## Keys\nDENIED_CONTENT_CANARY_BODY_RESTRICTED_777',
            privacy='restricted',
            external_processing=False,
        )
        # Also place an unenrolled file on disk in projects/alpha/
        self._create_vault_note(
            'projects/alpha/unenrolled.md',
            'note-unenrolled',
            'DENIED_CONTENT_CANARY_TITLE_UNENROLLED',
            'DENIED_CONTENT_CANARY_BODY_UNENROLLED_666',
            privacy='synthetic',
            external_processing=False,
        )

        # Corrupt the unselected note on disk to prove load_local_read_corpus never even opens it
        (self.vault / 'projects' / 'other-secret' / 'unselected.md').write_bytes(
            b'DENIED_CONTENT_CANARY_BODY_UNSELECTED_888_TAMPERED'
        )

        manifest_notes = [allowed_meta, denied_personal, denied_unselected, denied_restricted]
        local_read_scope = {
            'prefixes': ['projects/alpha/'],
            'notes': [],
        }

        # With allow_personal=False, personal note is excluded alongside restricted and unselected notes
        corpus = load_local_read_corpus(
            vault_dir=self.vault,
            manifest_notes=manifest_notes,
            local_read_scope=local_read_scope,
            allow_personal=False,
        )
        self.assertEqual([n['id'] for n in corpus], ['note-allowed-arch'])

        # Attempt to resolve wikilinks against all canary titles and allowed note
        link_res = resolve_wikilinks(
            candidates=[
                {'query': 'Alpha Architecture', 'heading': 'Overview', 'label': 'Alpha Arch'},
                {'query': 'DENIED_CONTENT_CANARY_TITLE_PERSONAL', 'label': 'personal'},
                {'query': 'DENIED_CONTENT_CANARY_TITLE_UNSELECTED', 'label': 'unselected'},
                {'query': 'DENIED_CONTENT_CANARY_TITLE_RESTRICTED', 'label': 'restricted'},
                {'query': 'DENIED_CONTENT_CANARY_TITLE_UNENROLLED', 'label': 'unenrolled'},
            ],
            allowed_notes=corpus,
            vault_root=self.vault,
        )
        self.assertEqual(len(link_res['linked']), 1)
        self.assertEqual(
            link_res['linked'][0]['wikilink'],
            '[[projects/alpha/architecture#Overview|Alpha Arch]]',
        )

        # Render index and model-facing output and verify zero canary leakage
        index_table = render_managed_index_routes({
            'projects/': [
                {'path': n['path'], 'title': n['title'], 'privacy': n['privacy']}
                for n in corpus
            ]
        })
        model_out = sanitize_model_output(
            {
                'status': 'SAVED',
                'transaction_id': 'a' * 64,
                'counts': {'saved': 1, 'updated': 1, 'linked': len(link_res['linked']), 'skipped': len(link_res['skipped']), 'quarantined': 0},
                'linked': link_res['linked'],
                'skipped': link_res['skipped'],
                'corpus': corpus,
            },
            model_output_policy={'paths': False, 'titles': False},
        )
        serialized = json.dumps(model_out) + '\n' + index_table
        for canary in (
            'DENIED_CONTENT_CANARY',
            'DENIED_CONTENT_CANARY_TITLE_PERSONAL',
            'DENIED_CONTENT_CANARY_BODY_PERSONAL_999',
            'DENIED_CONTENT_CANARY_TITLE_UNSELECTED',
            'DENIED_CONTENT_CANARY_BODY_UNSELECTED_888',
            'DENIED_CONTENT_CANARY_TITLE_RESTRICTED',
            'DENIED_CONTENT_CANARY_BODY_RESTRICTED_777',
            'DENIED_CONTENT_CANARY_TITLE_UNENROLLED',
            'DENIED_CONTENT_CANARY_BODY_UNENROLLED_666',
            'projects/alpha/architecture',
            'Alpha Architecture',
        ):
            if canary in ('projects/alpha/architecture', 'Alpha Architecture'):
                # Model output with paths=False, titles=False must not leak even allowed paths/titles!
                self.assertNotIn(canary, json.dumps(model_out))
            else:
                self.assertNotIn(canary, serialized)

    def test_reparse_tag_and_junction_refused_without_admin_privileges(self):
        from unittest.mock import patch
        note = self._create_vault_note(
            'projects/alpha/reparse.md',
            'note-reparse',
            'Reparse Test',
            '## Section\nBody',
            privacy='synthetic',
        )
        with patch.object(Path, 'is_junction', return_value=True):
            with self.assertRaises(WikiMemoryError) as ctx:
                resolve_wikilinks(
                    [{'query': 'Reparse Test'}],
                    allowed_notes=[{'id': note['id'], 'path': note['path'], 'title': 'Reparse Test', 'headings': ['Section'], 'privacy': 'synthetic'}],
                    vault_root=self.vault,
                )
            self.assertIn(ctx.exception.error_code, ('REDIRECTED_WIKI_PATH', 'REDIRECTED_VAULT_ROOT'))

    def test_end_to_end_repeated_cross_session_capture_and_privacy_isolation(self):
        import hashlib
        import json

        # Seed index.md and log.md with unmanaged canary bytes and managed blocks
        index_initial = (
            '---\ntitle: Second Brain index\n---\n# Second Brain index\n'
            'UNMANAGED_INDEX_TOP_CANARY\n'
            '<!-- brain-managed:start section="index-routes" -->\n'
            '| Existing folder | Purpose | Navigation |\n'
            '| --- | --- | --- |\n'
            '| `projects/` | Project context, decisions and current status | Add permitted project hubs when available |\n'
            '| `permanent/` | Reusable lessons with evidence | Add permitted topic hubs when available |\n'
            '| `references/` | Selected source summaries and citations | Add permitted references when available |\n'
            '| `logs/` | Dated session summaries | Add permitted summaries when available |\n'
            '<!-- brain-managed:end section="index-routes" -->\n'
            'UNMANAGED_INDEX_BOTTOM_CANARY\n'
        ).encode('utf-8')
        log_initial = (
            '---\ntitle: Second Brain change log\n---\n# Second Brain change log\n'
            'UNMANAGED_LOG_TOP_CANARY\n'
            '<!-- brain-managed:start section="change-log" -->\n'
            '- Initial empty state.\n'
            '<!-- brain-managed:end section="change-log" -->\n'
            'UNMANAGED_LOG_BOTTOM_CANARY\n'
        ).encode('utf-8')
        (self.vault / 'index.md').write_bytes(index_initial)
        (self.vault / 'log.md').write_bytes(log_initial)

        # Seed an approved reference note and a denied personal note
        allowed_ref = self._create_vault_note(
            'references/atomic-rename-spec.md',
            'ref-atomic-rename',
            'Atomic Rename Spec',
            '## Windows Semantics\nWindows os.rename refuses existing targets.',
            privacy='synthetic',
        )
        denied_note = self._create_vault_note(
            'projects/second-brain/secret-roadmap.md',
            'note-secret-roadmap',
            'DENIED_CONTENT_CANARY_ROADMAP_TITLE',
            '## Private Plans\nDENIED_CONTENT_CANARY_ROADMAP_PROSE',
            privacy='personal',
            external_processing=False,
        )

        manifest_notes = [allowed_ref, denied_note]
        local_read_scope = {'prefixes': ['references/', 'projects/second-brain/'], 'notes': []}

        session_1 = {
            'project_slug': 'second-brain',
            'project_id': 'c' * 64,
            'session_reference': 'sess-101',
            'role': 'planner',
            'date': '2026-11-05T10:00:00+00:00',
            'privacy': 'synthetic',
            'claims': [
                {
                    'kind': 'decision',
                    'topic': 'Commit Protocol',
                    'text': 'Write immutable journal before replacing target pointer.',
                    'status': 'reported-completed',
                    'evidence': 'summary-derived',
                    'locator': 'archive/s101.json#/items/0',
                    'link_queries': [
                        {'query': 'Atomic Rename Spec', 'heading': 'Windows Semantics', 'label': 'Windows Rename'},
                        {'query': 'DENIED_CONTENT_CANARY_ROADMAP_TITLE', 'label': 'Secret Roadmap'},
                    ],
                }
            ],
        }
        session_2 = {
            'project_slug': 'second-brain',
            'project_id': 'c' * 64,
            'session_reference': 'sess-102',
            'role': 'implementer',
            'date': '2026-11-06T10:00:00+00:00',
            'privacy': 'synthetic',
            'claims': [
                {
                    'kind': 'decision',
                    'topic': 'Commit Protocol',
                    'text': '  write immutable journal   before replacing target pointer. ',
                    'status': 'reported-passed',
                    'evidence': 'observed',
                    'locator': 'archive/s102.json#/items/0',
                    'link_queries': [
                        {'query': 'Atomic Rename Spec', 'heading': 'Windows Semantics', 'label': 'Windows Rename'},
                    ],
                }
            ],
        }

        res1 = integrate_cross_session_knowledge(
            private_dir=self.private,
            vault_dir=self.vault,
            manifest_notes=manifest_notes,
            local_read_scope=local_read_scope,
            sessions=[session_1, session_2],
            index_preimage_sha256=hashlib.sha256(index_initial).hexdigest(),
            log_preimage_sha256=hashlib.sha256(log_initial).hexdigest(),
            allow_personal=False,
        )
        self.assertEqual(res1['model_output']['status'], 'SAVED')
        self.assertEqual(res1['model_output']['counts']['linked'], 1)

        note_path = self.vault / 'projects' / 'second-brain' / 'commit-protocol.md'
        self.assertTrue(note_path.exists())
        note_text = note_path.read_bytes().decode('utf-8')
        # Deduplicated prose appears once, both sessions' provenance preserved
        self.assertEqual(note_text.count('Write immutable journal before replacing target pointer.'), 1)
        self.assertIn('sess-101', note_text)
        self.assertIn('sess-102', note_text)
        self.assertIn('[[references/atomic-rename-spec#Windows Semantics|Windows Rename]]', note_text)

        # Unmanaged bytes in index.md and log.md preserved, and zero canary leak anywhere
        index_after = (self.vault / 'index.md').read_bytes().decode('utf-8')
        log_after = (self.vault / 'log.md').read_bytes().decode('utf-8')
        self.assertIn('UNMANAGED_INDEX_TOP_CANARY', index_after)
        self.assertIn('UNMANAGED_INDEX_BOTTOM_CANARY', index_after)
        self.assertIn('UNMANAGED_LOG_TOP_CANARY', log_after)
        self.assertIn('UNMANAGED_LOG_BOTTOM_CANARY', log_after)
        self.assertIn('[[projects/second-brain/commit-protocol|Commit Protocol]]', index_after)
        self.assertIn('[[projects/second-brain/commit-protocol|Commit Protocol]]', log_after)

        combined_outputs = note_text + index_after + log_after + json.dumps(res1['model_output'])
        self.assertNotIn('DENIED_CONTENT_CANARY', combined_outputs)

    def test_unmanaged_existing_note_is_never_adopted_or_overwritten(self):
        unmanaged_path = self.vault / 'projects' / 'second-brain' / 'commit-protocol.md'
        unmanaged_path.parent.mkdir(parents=True, exist_ok=True)
        unmanaged_bytes = b'---\ntitle: "Owner Unmanaged Note"\n---\n# Owner Unmanaged Note\nDo not touch.\n'
        unmanaged_path.write_bytes(unmanaged_bytes)

        session = {
            'project_slug': 'second-brain',
            'project_id': 'c' * 64,
            'session_reference': 'sess-201',
            'role': 'implementer',
            'date': '2026-11-06T12:00:00+00:00',
            'privacy': 'synthetic',
            'claims': [
                {
                    'kind': 'decision',
                    'topic': 'Commit Protocol',
                    'text': 'Attempt to write to a path that already has an unmanaged file.',
                    'status': 'reported-completed',
                    'evidence': 'summary-derived',
                    'locator': 'archive/s201.json#/items/0',
                }
            ],
        }
        with self.assertRaises(WikiMemoryError) as ctx:
            integrate_cross_session_knowledge(
                private_dir=self.private,
                vault_dir=self.vault,
                manifest_notes=[],
                local_read_scope={'prefixes': ['projects/second-brain/'], 'notes': []},
                sessions=[session],
                allow_personal=False,
            )
        self.assertEqual(ctx.exception.error_code, 'UNMANAGED_TARGET_COLLISION')
        self.assertEqual(unmanaged_path.read_bytes(), unmanaged_bytes)

    def test_cross_privacy_claim_merge_refused(self):
        c1 = {
            'subject_key': 'auth-flow',
            'kind': 'decision',
            'text': 'Use OAuth PKCE.',
            'status': 'reported-completed',
            'evidence': 'summary-derived',
            'date': '2026-11-05T10:00:00+00:00',
            'session_reference': 's1',
            'role': 'planner',
            'locator': 'archive/1.json#/0',
            'privacy': 'synthetic',
        }
        c2 = dict(c1, privacy='personal', session_reference='s2')
        state = merge_session_claims([], [c1])
        with self.assertRaises(WikiMemoryError) as ctx:
            merge_session_claims(state['claims'], [c2])
        self.assertEqual(ctx.exception.error_code, 'PRIVACY_BOUNDARY_MISMATCH')


if __name__ == '__main__':
    unittest.main()
