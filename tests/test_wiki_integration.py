"""End-to-end integration tests for Wiki Memory Integration (Track B Continuation).

Verifies:
1. Multi-turn cross-session ingestion of mixed claims (decision, work, lesson, blocker)
   updating both topic notes and managed sections of index.md / log.md.
2. Byte-for-byte preservation of unmanaged bytes in index.md and log.md.
3. Recoverable recovery after simulated interruption before pointer swap, after pointer
   swap, and conflict handling on intervening external edits.
4. Strict privacy isolation: canary strings in unselected, personal, or restricted notes
   are never loaded, linked, or leaked into generated notes, hubs, or model output.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from migrate import digest, json_bytes
from publish_memory import publication_lock, read_bytes, replace_pointer, write_immutable
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


class WikiMemoryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.private = self.root / 'private'
        self.vault = self.root / 'vault'
        self.private.mkdir(parents=True, exist_ok=True)
        self.vault.mkdir(parents=True, exist_ok=True)
        (self.private / '.private-staging.json').write_bytes(
            json_bytes({'live_writes': False, 'external_exports': False})
        )

    def _setup_vault_hubs(self, top_canary_index='', bottom_canary_index='',
                           top_canary_log='', bottom_canary_log=''):
        index_content = (
            '---\n'
            'title: Second Brain Hub\n'
            'unmanaged_prop: "stay_intact"\n'
            '---\n'
            '# Second Brain Hub\n\n'
            f'{top_canary_index}\n'
            'Introductory unmanaged notes for knowledge navigation.\n\n'
            '<!-- brain-managed:start section="index-routes" -->\n'
            '| Existing folder | Purpose | Navigation |\n'
            '| --- | --- | --- |\n'
            '| `projects/` | Project context, decisions and current status | Add permitted project hubs when available |\n'
            '| `permanent/` | Reusable lessons with evidence | Add permitted topic hubs when available |\n'
            '| `references/` | Selected source summaries and citations | Add permitted references when available |\n'
            '| `logs/` | Dated session summaries | Add permitted summaries when available |\n'
            '<!-- brain-managed:end section="index-routes" -->\n\n'
            f'{bottom_canary_index}\n'
            'Unmanaged footer notes: maintain manual links here.\n'
        ).encode('utf-8')

        log_content = (
            '---\n'
            'title: Vault Change Log\n'
            'unmanaged_log_prop: 42\n'
            '---\n'
            '# Vault Change Log\n\n'
            f'{top_canary_log}\n'
            'This log tracks verified local publications.\n\n'
            '<!-- brain-managed:start section="change-log" -->\n'
            '- Initial baseline log entry.\n'
            '<!-- brain-managed:end section="change-log" -->\n\n'
            f'{bottom_canary_log}\n'
            'Unmanaged appendix for manual audit signs.\n'
        ).encode('utf-8')

        (self.vault / 'index.md').write_bytes(index_content)
        (self.vault / 'log.md').write_bytes(log_content)
        return index_content, log_content

    def _create_enrolled_note(self, relpath, note_id, title, content_body, privacy='synthetic', external_processing=False):
        full_path = self.vault.joinpath(*relpath.split('/'))
        full_path.parent.mkdir(parents=True, exist_ok=True)
        raw_bytes = (
            '---\n'
            f'schema_version: "1.0"\n'
            f'id: "{note_id}"\n'
            f'title: "{title}"\n'
            'kind: "topic"\n'
            'review_state: "policy-validated"\n'
            'created: "2026-11-01T00:00:00+00:00"\n'
            'updated: "2026-11-01T00:00:00+00:00"\n'
            f'privacy: "{privacy}"\n'
            f'external_processing: {json.dumps(external_processing)}\n'
            'sources: ["archive/seed.json"]\n'
            '---\n\n'
            f'# {title}\n\n'
            f'{content_body}\n'
        ).encode('utf-8')
        full_path.write_bytes(raw_bytes)
        return {
            'id': note_id,
            'path': relpath,
            'sha256': hashlib.sha256(raw_bytes).hexdigest(),
            'size': len(raw_bytes),
            'privacy': privacy,
            'external_processing': external_processing,
        }

    def test_01_multiturn_cross_session_mixed_claims_ingestion(self):
        """Test multi-turn cross-session ingestion of mixed claims (decision, work, lesson, blocker).

        Verifies topic notes creation/updates, cross-session deduplication, superseding,
        quarantine, and proper updates to index.md and log.md managed sections.
        """
        index_bytes_0, log_bytes_0 = self._setup_vault_hubs(
            top_canary_index='INDEX_CUSTOM_PROSE_TOP',
            bottom_canary_index='INDEX_CUSTOM_PROSE_BOTTOM',
            top_canary_log='LOG_CUSTOM_PROSE_TOP',
            bottom_canary_log='LOG_CUSTOM_PROSE_BOTTOM',
        )

        ref_note = self._create_enrolled_note(
            'references/posix-conformance.md',
            'ref-posix-conformance',
            'POSIX Conformance Guide',
            '## Hard Links\nos.link creates hard links on same filesystem.\n',
            privacy='synthetic',
        )

        manifest_notes = [ref_note]
        local_read_scope = {
            'prefixes': ['references/', 'projects/data-engine/', 'permanent/engineering/'],
            'notes': [],
        }

        # Turn 1: Session 1 (Planner) with 4 mixed claims across 4 distinct topics
        session_1 = {
            'project_slug': 'data-engine',
            'project_id': '1111111111111111111111111111111111111111111111111111111111111111',
            'session_reference': 'session-turn-1',
            'role': 'planner',
            'date': '2026-11-06T10:00:00+00:00',
            'privacy': 'synthetic',
            'claims': [
                {
                    'kind': 'decision',
                    'topic': 'Journal Design',
                    'text': 'Write immutable journal before replacing target pointer.',
                    'status': 'reported-completed',
                    'evidence': 'summary-derived',
                    'locator': 'archive/s1.json#/items/0',
                    'link_queries': [
                        {'query': 'POSIX Conformance Guide', 'heading': 'Hard Links', 'label': 'Hard Links Guide'}
                    ],
                },
                {
                    'kind': 'work',
                    'topic': 'Pipeline Architecture',
                    'text': 'Implement deterministic content addressing for all artifacts.',
                    'status': 'reported-completed',
                    'evidence': 'summary-derived',
                    'locator': 'archive/s1.json#/items/1',
                },
                {
                    'kind': 'lesson',
                    'topic': 'Atomic Pointer Swap',
                    'text': 'Windows os.replace provides atomic pointer swap on NTFS.',
                    'status': 'reported-completed',
                    'evidence': 'observed',
                    'locator': 'archive/s1.json#/items/2',
                },
                {
                    'kind': 'blocker',
                    'topic': 'File Lock Contention',
                    'text': 'Concurrent processes collide on publication lock file.',
                    'status': 'reported-failed',
                    'evidence': 'observed',
                    'locator': 'archive/s1.json#/items/3',
                },
            ],
        }

        turn1_result = integrate_cross_session_knowledge(
            private_dir=self.private,
            vault_dir=self.vault,
            manifest_notes=manifest_notes,
            local_read_scope=local_read_scope,
            sessions=[session_1],
            index_preimage_sha256=hashlib.sha256(index_bytes_0).hexdigest(),
            log_preimage_sha256=hashlib.sha256(log_bytes_0).hexdigest(),
            allow_personal=False,
        )

        model_out_1 = turn1_result['model_output']
        self.assertEqual(model_out_1['status'], 'SAVED')
        # 4 distinct note files created: 3 under projects/data-engine/, 1 under permanent/engineering/
        self.assertEqual(model_out_1['counts']['saved'], 4)
        self.assertEqual(model_out_1['counts']['linked'], 1)

        # Check created files on disk
        wal_path = self.vault / 'projects' / 'data-engine' / 'journal-design.md'
        pipe_path = self.vault / 'projects' / 'data-engine' / 'pipeline-architecture.md'
        atomic_path = self.vault / 'permanent' / 'engineering' / 'atomic-pointer-swap.md'
        lock_path = self.vault / 'projects' / 'data-engine' / 'file-lock-contention.md'

        self.assertTrue(wal_path.exists())
        self.assertTrue(pipe_path.exists())
        self.assertTrue(atomic_path.exists())
        self.assertTrue(lock_path.exists())

        wal_text = wal_path.read_bytes().decode('utf-8')
        self.assertIn('kind: "project"', wal_text)
        self.assertIn('privacy: "synthetic"', wal_text)
        self.assertIn('Write immutable journal before replacing target pointer.', wal_text)
        self.assertIn('[[references/posix-conformance#Hard Links|Hard Links Guide]]', wal_text)

        pipe_text = pipe_path.read_bytes().decode('utf-8')
        self.assertIn('kind: "project"', pipe_text)
        self.assertIn('Implement deterministic content addressing for all artifacts.', pipe_text)

        atomic_text = atomic_path.read_bytes().decode('utf-8')
        self.assertIn('kind: "lesson"', atomic_text)
        self.assertIn('Windows os.replace provides atomic pointer swap on NTFS.', atomic_text)

        lock_text = lock_path.read_bytes().decode('utf-8')
        self.assertIn('kind: "project"', lock_text)
        self.assertIn('Concurrent processes collide on publication lock file.', lock_text)

        # Check index.md and log.md updates
        index_bytes_1 = (self.vault / 'index.md').read_bytes()
        log_bytes_1 = (self.vault / 'log.md').read_bytes()
        index_text_1 = index_bytes_1.decode('utf-8')
        log_text_1 = log_bytes_1.decode('utf-8')

        self.assertIn('INDEX_CUSTOM_PROSE_TOP', index_text_1)
        self.assertIn('INDEX_CUSTOM_PROSE_BOTTOM', index_text_1)
        self.assertIn('LOG_CUSTOM_PROSE_TOP', log_text_1)
        self.assertIn('LOG_CUSTOM_PROSE_BOTTOM', log_text_1)

        self.assertIn('[[projects/data-engine/journal-design|Journal Design]]', index_text_1)
        self.assertIn('[[projects/data-engine/pipeline-architecture|Pipeline Architecture]]', index_text_1)
        self.assertIn('[[permanent/engineering/atomic-pointer-swap|Atomic Pointer Swap]]', index_text_1)
        self.assertIn('[[projects/data-engine/file-lock-contention|File Lock Contention]]', index_text_1)

        # Find the claim ID of the blocker claim in lock_path to supersede it in Turn 2
        blocker_claim_id = deterministic_claim_id(
            'file-lock-contention',
            'Concurrent processes collide on publication lock file.'
        )
        self.assertIn(blocker_claim_id, lock_text)

        # Update manifest_notes with Turn 1 notes so Turn 2 can update them
        enrolled_wal = {
            'id': deterministic_note_id('project', 'data-engine', 'journal-design'),
            'path': 'projects/data-engine/journal-design.md',
            'sha256': hashlib.sha256(wal_path.read_bytes()).hexdigest(),
            'size': wal_path.stat().st_size,
            'privacy': 'synthetic',
        }
        enrolled_pipe = {
            'id': deterministic_note_id('project', 'data-engine', 'pipeline-architecture'),
            'path': 'projects/data-engine/pipeline-architecture.md',
            'sha256': hashlib.sha256(pipe_path.read_bytes()).hexdigest(),
            'size': pipe_path.stat().st_size,
            'privacy': 'synthetic',
        }
        enrolled_atomic = {
            'id': deterministic_note_id('lesson', 'engineering', 'atomic-pointer-swap'),
            'path': 'permanent/engineering/atomic-pointer-swap.md',
            'sha256': hashlib.sha256(atomic_path.read_bytes()).hexdigest(),
            'size': atomic_path.stat().st_size,
            'privacy': 'synthetic',
        }
        enrolled_lock = {
            'id': deterministic_note_id('project', 'data-engine', 'file-lock-contention'),
            'path': 'projects/data-engine/file-lock-contention.md',
            'sha256': hashlib.sha256(lock_path.read_bytes()).hexdigest(),
            'size': lock_path.stat().st_size,
            'privacy': 'synthetic',
        }
        manifest_turn2 = [ref_note, enrolled_wal, enrolled_pipe, enrolled_atomic, enrolled_lock]

        # Turn 2: Session 2 (Implementer)
        # - Duplicate normalized claim on Journal Design: different spacing & casing -> prose deduplicated, provenance added
        # - Superseding claim on File Lock Contention: resolves blocker -> blocker moves to Historical & Superseded
        # - Contradictory claim on Pipeline Architecture without supersedes -> quarantined into Unresolved Contradictions
        # - New lesson claim on Atomic Pointer Swap with supersedes -> earlier claim superseded
        lesson_claim_id = deterministic_claim_id(
            'atomic-pointer-swap',
            'Windows os.replace provides atomic pointer swap on NTFS.'
        )
        session_2 = {
            'project_slug': 'data-engine',
            'project_id': '1111111111111111111111111111111111111111111111111111111111111111',
            'session_reference': 'session-turn-2',
            'role': 'implementer',
            'date': '2026-11-06T12:00:00+00:00',
            'privacy': 'synthetic',
            'claims': [
                {
                    'kind': 'decision',
                    'topic': 'Journal Design',
                    'text': '  write immutable journal   before replacing target pointer.  ',
                    'status': 'reported-passed',
                    'evidence': 'observed',
                    'locator': 'archive/s2.json#/items/0',
                },
                {
                    'kind': 'work',
                    'topic': 'Pipeline Architecture',
                    'text': 'Contradictory claim: bypass content addressing and use random IDs.',
                    'status': 'proposed',
                    'evidence': 'summary-derived',
                    'locator': 'archive/s2.json#/items/1',
                },
                {
                    'kind': 'work',
                    'topic': 'File Lock Contention',
                    'text': 'Resolved lock contention via cooperative backoff and retry loop.',
                    'status': 'reported-completed',
                    'evidence': 'observed',
                    'locator': 'archive/s2.json#/items/2',
                    'supersedes': [blocker_claim_id],
                },
                {
                    'kind': 'lesson',
                    'topic': 'Atomic Pointer Swap',
                    'text': 'Handle directory junctions and reparse tags with lstat checks.',
                    'status': 'reported-completed',
                    'evidence': 'observed',
                    'locator': 'archive/s2.json#/items/3',
                    'supersedes': [lesson_claim_id],
                },
            ],
        }

        turn2_result = integrate_cross_session_knowledge(
            private_dir=self.private,
            vault_dir=self.vault,
            manifest_notes=manifest_turn2,
            local_read_scope=local_read_scope,
            sessions=[session_1, session_2],
            index_preimage_sha256=hashlib.sha256(index_bytes_1).hexdigest(),
            log_preimage_sha256=hashlib.sha256(log_bytes_1).hexdigest(),
            allow_personal=False,
        )

        model_out_2 = turn2_result['model_output']
        self.assertEqual(model_out_2['status'], 'SAVED')
        # All 4 topic notes updated + index.md + log.md = 6 updated
        self.assertEqual(model_out_2['counts']['saved'], 0)
        self.assertEqual(model_out_2['counts']['updated'], 6)
        self.assertEqual(model_out_2['counts']['quarantined'], 1)

        # Inspect updated Journal Design note
        wal_text_2 = wal_path.read_bytes().decode('utf-8')
        # Deduplicated claim appears exactly ONCE in prose
        self.assertEqual(
            wal_text_2.count('Write immutable journal before replacing target pointer.'), 1
        )
        # But has provenance records from both sessions
        self.assertIn('session-turn-1', wal_text_2)
        self.assertIn('session-turn-2', wal_text_2)

        # Inspect updated Pipeline Architecture note (contradictory claim quarantined)
        pipe_text_2 = pipe_path.read_bytes().decode('utf-8')
        self.assertIn('Implement deterministic content addressing for all artifacts.', pipe_text_2)
        self.assertIn('## Unresolved Contradictions (Quarantined)', pipe_text_2)
        self.assertIn('CONTRADICTORY_CLAIM_QUARANTINED', pipe_text_2)
        contradictory_cid = deterministic_claim_id(
            'pipeline-architecture',
            'Contradictory claim: bypass content addressing and use random IDs.'
        )
        self.assertIn(contradictory_cid, pipe_text_2)

        # Inspect updated Lock Contention note
        lock_text_2 = lock_path.read_bytes().decode('utf-8')
        # Active knowledge has new claim
        self.assertIn('Resolved lock contention via cooperative backoff and retry loop.', lock_text_2)
        # Historical & Superseded claims section holds the earlier blocker
        self.assertIn('## Historical & Superseded Claims', lock_text_2)
        self.assertIn('Concurrent processes collide on publication lock file.', lock_text_2)
        self.assertIn('superseded; superseded by', lock_text_2)

        # Inspect updated Atomic Pointer Swap lesson note
        atomic_text_2 = atomic_path.read_bytes().decode('utf-8')
        self.assertIn('Handle directory junctions and reparse tags with lstat checks.', atomic_text_2)
        self.assertIn('## Historical & Superseded Claims', atomic_text_2)
        self.assertIn('Windows os.replace provides atomic pointer swap on NTFS.', atomic_text_2)

        # Verify index.md and log.md still preserve unmanaged text
        index_text_2 = (self.vault / 'index.md').read_bytes().decode('utf-8')
        log_text_2 = (self.vault / 'log.md').read_bytes().decode('utf-8')
        self.assertIn('INDEX_CUSTOM_PROSE_TOP', index_text_2)
        self.assertIn('INDEX_CUSTOM_PROSE_BOTTOM', index_text_2)
        self.assertIn('LOG_CUSTOM_PROSE_TOP', log_text_2)
        self.assertIn('LOG_CUSTOM_PROSE_BOTTOM', log_text_2)

    def test_02_preservation_of_unmanaged_bytes_in_index_and_log(self):
        """Test byte-for-byte preservation of unmanaged bytes in index.md and log.md."""
        top_index = (
            '---\n'
            'title: "Index with Complex Unmanaged Content"\n'
            'custom_metadata:\n'
            '  nested: true\n'
            '  owner: "Alice"\n'
            '---\n\n'
            '# Unmanaged Header with Special Chars: \u26a0\ufe0f & \u00a9 2026\n\n'
            '> Blockquote that must never be altered.\n\n'
            '```python\n'
            'def unmanaged_code_block():\n'
            '    return "stay unchanged"\n'
            '```\n\n'
        )
        bottom_index = (
            '\n\n## Unmanaged Trailing Section\n'
            '- Item 1\n'
            '- Item 2 with [[Manual Wikilink|Custom Label]]\n'
            '<!-- custom unmanaged comment -->\n'
        )

        top_log = (
            '---\ntitle: "Change Log with Unmanaged Preamble"\n---\n\n'
            '# Audit Log Preamble\n'
            'Confidential internal audit notes. Do not remove.\n\n'
        )
        bottom_log = (
            '\n\n## Operator Sign-off\n'
            'Signed-off-by: Security Lead <sec@example.internal>\n'
        )

        index_initial = (
            top_index +
            '<!-- brain-managed:start section="index-routes" -->\n'
            '| Existing folder | Purpose | Navigation |\n'
            '| --- | --- | --- |\n'
            '| `projects/` | Project context, decisions and current status | Add permitted project hubs when available |\n'
            '| `permanent/` | Reusable lessons with evidence | Add permitted topic hubs when available |\n'
            '| `references/` | Selected source summaries and citations | Add permitted references when available |\n'
            '| `logs/` | Dated session summaries | Add permitted summaries when available |\n'
            '<!-- brain-managed:end section="index-routes" -->' +
            bottom_index
        ).encode('utf-8')

        log_initial = (
            top_log +
            '<!-- brain-managed:start section="change-log" -->\n'
            '- Initial log.\n'
            '<!-- brain-managed:end section="change-log" -->' +
            bottom_log
        ).encode('utf-8')

        (self.vault / 'index.md').write_bytes(index_initial)
        (self.vault / 'log.md').write_bytes(log_initial)

        # Update index.md
        routes = {
            'projects/': [{'path': 'projects/data-engine/core.md', 'title': 'Core Engine'}],
            'permanent/': [{'path': 'permanent/engineering/patterns.md', 'title': 'Engineering Patterns'}],
        }
        new_index_routes = render_managed_index_routes(routes)

        res_index = update_managed_section(
            private_dir=self.private,
            vault_dir=self.vault,
            relative_path='index.md',
            section='index-routes',
            expected_preimage_sha256=hashlib.sha256(index_initial).hexdigest(),
            new_section_body=new_index_routes,
        )
        self.assertEqual(res_index['status'], 'UPDATED')

        index_after = (self.vault / 'index.md').read_bytes().decode('utf-8')
        start_marker_idx = index_after.index('<!-- brain-managed:start section="index-routes" -->\n')
        end_marker_str = '<!-- brain-managed:end section="index-routes" -->'
        end_marker_idx = index_after.index(end_marker_str) + len(end_marker_str)

        prefix_after = index_after[:start_marker_idx]
        suffix_after = index_after[end_marker_idx:]

        # Exact byte-for-byte comparison of unmanaged content
        self.assertEqual(prefix_after, top_index)
        self.assertEqual(suffix_after, bottom_index)

        # Update log.md
        log_entries = [
            {
                'timestamp': '2026-11-06T15:30:00+00:00',
                'operation': 'SAVED',
                'note_links': ['[[projects/data-engine/core|Core Engine]]'],
                'locator': 'wiki-updates/receipt-001.json',
                'verification': 'HASH_MATCH_OK',
            }
        ]
        new_log_entries = render_managed_log_entries(log_entries)

        res_log = update_managed_section(
            private_dir=self.private,
            vault_dir=self.vault,
            relative_path='log.md',
            section='change-log',
            expected_preimage_sha256=hashlib.sha256(log_initial).hexdigest(),
            new_section_body=new_log_entries,
        )
        self.assertEqual(res_log['status'], 'UPDATED')

        log_after = (self.vault / 'log.md').read_bytes().decode('utf-8')
        log_start_idx = log_after.index('<!-- brain-managed:start section="change-log" -->\n')
        log_end_marker = '<!-- brain-managed:end section="change-log" -->'
        log_end_idx = log_after.index(log_end_marker) + len(log_end_marker)

        self.assertEqual(log_after[:log_start_idx], top_log)
        self.assertEqual(log_after[log_end_idx:], bottom_log)

    def test_03_recoverable_recovery_after_simulated_interruption(self):
        """Test write-ahead log recovery after simulated interruption before and after pointer swap."""
        initial_text = (
            '# Heading\n\n'
            'Unmanaged top.\n\n'
            '<!-- brain-managed:start section="test-sec" -->\n'
            'Initial body.\n'
            '<!-- brain-managed:end section="test-sec" -->\n\n'
            'Unmanaged bottom.\n'
        )
        initial_bytes = initial_text.encode('utf-8')
        (self.vault / 'managed-test.md').write_bytes(initial_bytes)
        preimage_sha = hashlib.sha256(initial_bytes).hexdigest()

        new_body = 'Committed body line 1.\nCommitted body line 2.\n'
        intended_text = (
            '# Heading\n\n'
            'Unmanaged top.\n\n'
            '<!-- brain-managed:start section="test-sec" -->\n'
            'Committed body line 1.\nCommitted body line 2.\n'
            '<!-- brain-managed:end section="test-sec" -->\n\n'
            'Unmanaged bottom.\n'
        )
        intended_bytes = intended_text.encode('utf-8')
        intended_sha = hashlib.sha256(intended_bytes).hexdigest()

        # Compute deterministic transaction_id matching update_managed_section
        tx_seed = json_bytes({
            'vault': str(self.vault),
            'relative_path': 'managed-test.md',
            'section': 'test-sec',
            'expected_preimage_sha256': preimage_sha,
            'new_section_body_sha256': hashlib.sha256(new_body.encode('utf-8')).hexdigest(),
        })
        tx_id = hashlib.sha256(tx_seed).hexdigest()
        tx_dir = self.private / 'wiki-updates' / tx_id
        tx_dir.mkdir(parents=True, exist_ok=True)
        journal_path = tx_dir / 'journal.json'
        receipt_path = tx_dir / 'receipt.json'

        # Stage 1: Simulate interruption BEFORE pointer swap
        # Write journal to private directory, but leave target file untouched in vault
        journal_data = {
            'schema': 'brain-wiki-section-journal-v1',
            'transaction_id': tx_id,
            'relative_path': 'managed-test.md',
            'section': 'test-sec',
            'preimage_sha256': preimage_sha,
            'preimage_utf8': initial_text,
            'intended_sha256': intended_sha,
            'intended_utf8': intended_text,
        }
        write_immutable(journal_path, json_bytes(journal_data))
        self.assertTrue(journal_path.exists())
        self.assertFalse(receipt_path.exists())
        self.assertEqual((self.vault / 'managed-test.md').read_bytes(), initial_bytes)

        # Invoke update_managed_section: should detect journal and recover by applying pointer swap
        res_recov1 = update_managed_section(
            private_dir=self.private,
            vault_dir=self.vault,
            relative_path='managed-test.md',
            section='test-sec',
            expected_preimage_sha256=preimage_sha,
            new_section_body=new_body,
        )
        self.assertEqual(res_recov1['status'], 'RECOVERED')
        self.assertEqual(res_recov1['recovery_stage'], 'APPLIED_FROM_PREIMAGE')
        self.assertEqual(res_recov1['committed_sha256'], intended_sha)
        self.assertEqual((self.vault / 'managed-test.md').read_bytes(), intended_bytes)
        self.assertTrue(receipt_path.exists())

        # Stage 2: Simulate interruption AFTER pointer swap before receipt write
        # Remove receipt to simulate crash before receipt was written
        receipt_path.unlink()
        self.assertFalse(receipt_path.exists())
        self.assertEqual((self.vault / 'managed-test.md').read_bytes(), intended_bytes)

        # Invoke update_managed_section: should detect target already matches intended_sha and finalize receipt
        res_recov2 = update_managed_section(
            private_dir=self.private,
            vault_dir=self.vault,
            relative_path='managed-test.md',
            section='test-sec',
            expected_preimage_sha256=preimage_sha,
            new_section_body=new_body,
        )
        self.assertEqual(res_recov2['status'], 'RECOVERED')
        self.assertEqual(res_recov2['recovery_stage'], 'FINALIZED_RECEIPT')
        self.assertTrue(receipt_path.exists())

        # Stage 3: Idempotent replay with receipt present
        res_replay = update_managed_section(
            private_dir=self.private,
            vault_dir=self.vault,
            relative_path='managed-test.md',
            section='test-sec',
            expected_preimage_sha256=preimage_sha,
            new_section_body=new_body,
        )
        self.assertEqual(res_replay['status'], 'NO_CHANGE')

        # Stage 4: Test safe preimage restoration via restore_managed_preimage
        res_restore = restore_managed_preimage(
            private_dir=self.private,
            vault_dir=self.vault,
            transaction_id=tx_id,
        )
        self.assertEqual(res_restore['status'], 'RESTORED')
        self.assertEqual((self.vault / 'managed-test.md').read_bytes(), initial_bytes)

        # Stage 5: Intervening external edit conflict
        # External editor changes file to something else
        (self.vault / 'managed-test.md').write_bytes(b'External manual edit.\n')
        with self.assertRaises(WikiMemoryError) as ctx:
            restore_managed_preimage(
                private_dir=self.private,
                vault_dir=self.vault,
                transaction_id=tx_id,
            )
        self.assertEqual(ctx.exception.error_code, 'LATER_EDIT_CONFLICT')
        self.assertEqual((self.vault / 'managed-test.md').read_bytes(), b'External manual edit.\n')

    def test_04_strict_canary_isolation_and_privacy_boundaries(self):
        """Test strict isolation: canary text in unselected or personal notes is never loaded, linked, or leaked."""
        index_bytes, log_bytes = self._setup_vault_hubs()

        # Approved synthetic reference note
        approved_ref = self._create_enrolled_note(
            'references/storage-specs.md',
            'ref-storage-specs',
            'Public Storage Spec',
            '## Concurrency\nUse write locks to prevent data races.\n',
            privacy='synthetic',
            external_processing=True,
        )

        # Enrolled personal note with sensitive canary content
        denied_personal = self._create_enrolled_note(
            'projects/secret/personal-plan.md',
            'note-personal-plan',
            'DENIED_CONTENT_CANARY_PERSONAL_TITLE',
            '## Secret Section\nDENIED_CONTENT_CANARY_PERSONAL_PROSE\n',
            privacy='personal',
            external_processing=False,
        )

        # Restricted note with canary content
        denied_restricted = self._create_enrolled_note(
            'permanent/restricted/security-keys.md',
            'note-restricted-keys',
            'DENIED_CONTENT_CANARY_RESTRICTED_TITLE',
            '## Keys\nDENIED_CONTENT_CANARY_RESTRICTED_KEY_MATERIAL\n',
            privacy='restricted',
            external_processing=False,
        )

        # Unmanaged, un-enrolled note sitting in vault with canary
        unmanaged_secret_path = self.vault / 'projects' / 'unmanaged-secret.md'
        unmanaged_secret_path.parent.mkdir(parents=True, exist_ok=True)
        unmanaged_secret_path.write_bytes(b'DENIED_CONTENT_CANARY_UNMANAGED_PROSE\n')

        # Test load_local_read_corpus directly: verify personal and restricted are filtered out
        manifest = [approved_ref, denied_personal, denied_restricted]
        read_scope = {
            'prefixes': ['references/', 'projects/', 'permanent/'],
            'notes': [],
        }

        corpus_synthetic_only = load_local_read_corpus(
            vault_dir=self.vault,
            manifest_notes=manifest,
            local_read_scope=read_scope,
            allow_personal=False,
        )
        loaded_ids = [n['id'] for n in corpus_synthetic_only]
        self.assertIn('ref-storage-specs', loaded_ids)
        self.assertNotIn('note-personal-plan', loaded_ids)
        self.assertNotIn('note-restricted-keys', loaded_ids)

        # Run integrate_cross_session_knowledge with link queries targeting canary items
        session = {
            'project_slug': 'data-engine',
            'project_id': '2222222222222222222222222222222222222222222222222222222222222222',
            'session_reference': 'session-canary-test',
            'role': 'implementer',
            'date': '2026-11-06T14:00:00+00:00',
            'privacy': 'synthetic',
            'claims': [
                {
                    'kind': 'decision',
                    'topic': 'Concurrency Architecture',
                    'text': 'Enforce single-writer lock for all metadata updates.',
                    'status': 'reported-completed',
                    'evidence': 'observed',
                    'locator': 'archive/s_canary.json#/items/0',
                    'link_queries': [
                        {'query': 'Public Storage Spec', 'heading': 'Concurrency', 'label': 'Storage Concurrency'},
                        {'query': 'DENIED_CONTENT_CANARY_PERSONAL_TITLE', 'label': 'Personal Link'},
                        {'query': 'projects/secret/personal-plan.md', 'label': 'Path Link'},
                        {'query': 'DENIED_CONTENT_CANARY_RESTRICTED_TITLE', 'label': 'Restricted Link'},
                        {'query': 'projects/unmanaged-secret.md', 'label': 'Unmanaged Link'},
                    ],
                }
            ],
        }

        result = integrate_cross_session_knowledge(
            private_dir=self.private,
            vault_dir=self.vault,
            manifest_notes=manifest,
            local_read_scope=read_scope,
            sessions=[session],
            index_preimage_sha256=hashlib.sha256(index_bytes).hexdigest(),
            log_preimage_sha256=hashlib.sha256(log_bytes).hexdigest(),
            allow_personal=False,
            model_output_policy={'paths': True, 'titles': True},
        )

        self.assertEqual(result['model_output']['status'], 'SAVED')
        self.assertEqual(result['model_output']['counts']['linked'], 1)
        self.assertEqual(result['model_output']['counts']['skipped'], 4)

        # Verify created note
        note_path = self.vault / 'projects' / 'data-engine' / 'concurrency-architecture.md'
        self.assertTrue(note_path.exists())
        created_note_text = note_path.read_bytes().decode('utf-8')

        # Legitimate link succeeded
        self.assertIn('[[references/storage-specs#Concurrency|Storage Concurrency]]', created_note_text)

        # Read all created/updated notes, hubs, and model outputs in the vault
        all_vault_outputs = [
            created_note_text,
            (self.vault / 'index.md').read_bytes().decode('utf-8'),
            (self.vault / 'log.md').read_bytes().decode('utf-8'),
            json.dumps(result['model_output']),
        ]
        combined = '\n'.join(all_vault_outputs)

        # STRICT ASSERTION: ZERO CANARY LEAKAGE ANYWHERE
        canaries = [
            'DENIED_CONTENT_CANARY_PERSONAL_TITLE',
            'DENIED_CONTENT_CANARY_PERSONAL_PROSE',
            'DENIED_CONTENT_CANARY_RESTRICTED_TITLE',
            'DENIED_CONTENT_CANARY_RESTRICTED_KEY_MATERIAL',
            'DENIED_CONTENT_CANARY_UNMANAGED_PROSE',
            'projects/secret/personal-plan.md',
            'permanent/restricted/security-keys.md',
            'projects/unmanaged-secret.md',
        ]
        for canary in canaries:
            with self.subTest(canary=canary):
                self.assertNotIn(canary, combined)

    def test_05_concurrency_lock_and_conflict_resolution(self):
        """Test lock mutual exclusion, stale hash refusal, and intervening edit conflict resolution."""
        initial_text = (
            '# Heading\n\n'
            '<!-- brain-managed:start section="concurrency-sec" -->\n'
            'Initial body.\n'
            '<!-- brain-managed:end section="concurrency-sec" -->\n'
        )
        initial_bytes = initial_text.encode('utf-8')
        (self.vault / 'concurrency-test.md').write_bytes(initial_bytes)
        preimage_sha = hashlib.sha256(initial_bytes).hexdigest()

        # 1. Lock acquisition: when another process holds the publication lock, update is refused
        with publication_lock(self.private, self.vault) as acquired:
            self.assertTrue(acquired)
            with self.assertRaises(WikiMemoryError) as ctx:
                update_managed_section(
                    private_dir=self.private,
                    vault_dir=self.vault,
                    relative_path='concurrency-test.md',
                    section='concurrency-sec',
                    expected_preimage_sha256=preimage_sha,
                    new_section_body='Concurrent body.\n',
                )
            self.assertEqual(ctx.exception.error_code, 'PUBLICATION_LOCK_BUSY')

        # 2. Stale preimage refusal: when file has drifted, update is refused
        wrong_hash = hashlib.sha256(b'wrong-hash').hexdigest()
        with self.assertRaises(WikiMemoryError) as ctx:
            update_managed_section(
                private_dir=self.private,
                vault_dir=self.vault,
                relative_path='concurrency-test.md',
                section='concurrency-sec',
                expected_preimage_sha256=wrong_hash,
                new_section_body='Drift body.\n',
            )
        self.assertEqual(ctx.exception.error_code, 'STALE_PREIMAGE_HASH')

        # 3. Intervening edit conflict during journaled update
        new_body = 'Intended body.\n'
        tx_seed = json_bytes({
            'vault': str(self.vault),
            'relative_path': 'concurrency-test.md',
            'section': 'concurrency-sec',
            'expected_preimage_sha256': preimage_sha,
            'new_section_body_sha256': hashlib.sha256(new_body.encode('utf-8')).hexdigest(),
        })
        tx_id = hashlib.sha256(tx_seed).hexdigest()
        tx_dir = self.private / 'wiki-updates' / tx_id
        tx_dir.mkdir(parents=True, exist_ok=True)
        journal_path = tx_dir / 'journal.json'

        intended_text = 'intended text\n'
        intended_sha = hashlib.sha256(intended_text.encode('utf-8')).hexdigest()
        journal_data = {
            'schema': 'brain-wiki-section-journal-v1',
            'transaction_id': tx_id,
            'relative_path': 'concurrency-test.md',
            'section': 'concurrency-sec',
            'preimage_sha256': preimage_sha,
            'preimage_utf8': initial_text,
            'intended_sha256': intended_sha,
            'intended_utf8': intended_text,
        }
        write_immutable(journal_path, json_bytes(journal_data))

        # External editor modified the file so current_sha matches neither preimage nor intended
        (self.vault / 'concurrency-test.md').write_bytes(b'External drift after journal.\n')

        with self.assertRaises(WikiMemoryError) as ctx:
            update_managed_section(
                private_dir=self.private,
                vault_dir=self.vault,
                relative_path='concurrency-test.md',
                section='concurrency-sec',
                expected_preimage_sha256=preimage_sha,
                new_section_body=new_body,
            )
        self.assertEqual(ctx.exception.error_code, 'LATER_EDIT_CONFLICT')
        # The external modification is preserved untouched
        self.assertEqual((self.vault / 'concurrency-test.md').read_bytes(), b'External drift after journal.\n')


if __name__ == '__main__':
    unittest.main()
