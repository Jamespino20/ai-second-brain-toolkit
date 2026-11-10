"""Synthetic tests for read-only bounded wiki health checks (T16)."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from selected_memory import digest
import wiki_health


class WikiHealthSlice1SecurityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.root = self.base / 'test-vault' / 'synthetic'
        self.root.mkdir(parents=True)
        self.manifest_path = self.base / 'health-manifest.json'

        self.note_a = self.root / 'index.md'
        self.note_a.write_bytes(
            b'---\nprivacy: "synthetic"\ntitle: Index\n---\n\n# Index\n\nSee [[projects/alpha/overview|Alpha Overview]].\n'
        )
        self.note_b = self.root / 'projects' / 'alpha' / 'overview.md'
        self.note_b.parent.mkdir(parents=True, exist_ok=True)
        self.note_b.write_bytes(
            b'---\nprivacy: "synthetic"\ntitle: Alpha Overview\n---\n\n# Alpha Overview\n\n## Status\n\nAll good.\n'
        )

        # Unselected and denied files with canary strings that must never be read or leaked.
        self.unselected = self.root / 'projects' / 'alpha' / 'unselected-secret.md'
        self.unselected.write_bytes(
            b'---\nprivacy: "personal"\n---\n\n# Secret\n\nDENIED_CONTENT_CANARY_UNSELECTED_991\n'
        )
        self.denied_dir = self.root / 'private-notes'
        self.denied_dir.mkdir(parents=True, exist_ok=True)
        self.denied_file = self.denied_dir / 'denied.md'
        self.denied_file.write_bytes(
            b'---\nprivacy: "personal"\n---\n\n# Denied\n\nDENIED_CONTENT_CANARY_PRIVATE_992\n'
        )

        self.manifest = {
            'schema': 'wiki-health-manifest-v1',
            'source_kind': 'synthetic',
            'client': 'codex-openai',
            'root': str(self.root),
            'owner_authorization': {
                'state': 'approved',
                'reference': 'synthetic-t16-fixture',
                'purpose': 'wiki-health-structural-lint',
                'personal_content_external_model_approved': False,
            },
            'subset_prefixes': ['projects/alpha/'],
            'notes': [
                self._note_entry('index', 'index.md', self.note_a, ['synthetic://fixture/index']),
                self._note_entry('alpha-overview', 'projects/alpha/overview.md', self.note_b, ['synthetic://fixture/alpha']),
            ],
        }
        self.pin = self.repin()

    def _note_entry(self, note_id, rel_path, file_path, refs):
        raw = file_path.read_bytes()
        return {
            'id': note_id,
            'path': rel_path,
            'size': len(raw),
            'sha256': digest(raw),
            'source_references': list(refs),
        }

    def repin(self):
        self.manifest_path.write_text(json.dumps(self.manifest, indent=2), encoding='utf-8')
        return digest(self.manifest_path.read_bytes())

    def snapshot_files(self):
        return {p: p.read_bytes() for p in self.base.rglob('*') if p.is_file()}

    def test_valid_manifest_runs_read_only_and_never_leaks_canaries(self):
        before = self.snapshot_files()
        report = wiki_health.check_wiki_health(self.manifest_path, self.pin, 'codex-openai')
        after = self.snapshot_files()
        self.assertEqual(before, after)
        self.assertEqual(report['schema'], 'wiki-health-report-v1')
        self.assertEqual(report['mode'], 'read-only-wiki-health')
        self.assertEqual(report['analysis_kind'], 'structural-lint')
        self.assertIs(report['semantic_validation'], False)
        self.assertEqual(report['repairs_applied'], 0)
        self.assertEqual(report['authorized_note_count'], 2)
        serialized = json.dumps(report)
        self.assertNotIn('DENIED_CONTENT_CANARY', serialized)
        self.assertNotIn('unselected-secret', serialized)

    def test_manifest_tamper_and_stale_note_fail_closed(self):
        self.manifest_path.write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Manifest changed'):
            wiki_health.check_wiki_health(self.manifest_path, self.pin, 'codex-openai')

        self.pin = self.repin()
        self.note_b.write_bytes(self.note_b.read_bytes() + b'\ndrift\n')
        with self.assertRaisesRegex(ValueError, 'changed|stale'):
            wiki_health.check_wiki_health(self.manifest_path, self.pin, 'codex-openai')

    def test_path_traversal_duplicate_and_invalid_ids_refused(self):
        bad_paths = [
            '../outside.md',
            '/outside.md',
            'C:/outside.md',
            'projects\\alpha\\overview.md',
            'projects/alpha/./overview.md',
            'projects/alpha/overview.md:ads.md',
            '.obsidian/workspace.md',
            '.git/config.md',
            'projects/alpha/overview.txt',
        ]
        for bad_path in bad_paths:
            with self.subTest(path=bad_path):
                manifest = copy.deepcopy(self.manifest)
                manifest['notes'][1]['path'] = bad_path
                self.manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
                pin = digest(self.manifest_path.read_bytes())
                with self.assertRaisesRegex(ValueError, 'Invalid'):
                    wiki_health.check_wiki_health(self.manifest_path, pin, 'codex-openai')

        # Duplicate case-insensitive path
        manifest = copy.deepcopy(self.manifest)
        manifest['notes'].append({
            **manifest['notes'][0],
            'id': 'index-dup',
            'path': 'INDEX.md',
        })
        self.manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        pin = digest(self.manifest_path.read_bytes())
        with self.assertRaisesRegex(ValueError, 'Invalid|duplicate'):
            wiki_health.check_wiki_health(self.manifest_path, pin, 'codex-openai')

    def test_hardlink_oversized_and_unauthorized_client_refused(self):
        with self.assertRaisesRegex(ValueError, 'Client not authorized'):
            wiki_health.check_wiki_health(self.manifest_path, self.pin, 'claude-anthropic')

        # Canonical without personal_content_external_model_approved
        self.manifest['source_kind'] = 'canonical'
        self.pin = self.repin()
        with self.assertRaisesRegex(ValueError, 'personal-content'):
            wiki_health.check_wiki_health(self.manifest_path, self.pin, 'codex-openai')

        # Restore synthetic, test hardlink refusal
        self.manifest['source_kind'] = 'synthetic'
        self.pin = self.repin()
        hardlinked = self.root / 'hardlinked.md'
        os.link(self.note_a, hardlinked)
        try:
            with self.assertRaisesRegex(ValueError, 'non-hardlinked'):
                wiki_health.check_wiki_health(self.manifest_path, self.pin, 'codex-openai')
        finally:
            hardlinked.unlink(missing_ok=True)

        # Oversized note refusal (>128000 bytes)
        big_payload = b'---\nprivacy: "synthetic"\n---\n\n# Big\n\n' + (b'a' * 128050)
        self.note_b.write_bytes(big_payload)
        self.manifest['notes'][1]['size'] = len(big_payload)
        self.manifest['notes'][1]['sha256'] = digest(big_payload)
        self.pin = self.repin()
        with self.assertRaisesRegex(ValueError, 'too large'):
            wiki_health.check_wiki_health(self.manifest_path, self.pin, 'codex-openai')


class WikiHealthSlice2LinksAnchorsOrphansTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.root = self.base / 'test-vault' / 'synthetic'
        self.root.mkdir(parents=True)
        self.manifest_path = self.base / 'health-manifest.json'

    def _write_synthetic(self, rel_path, body):
        path = self.root.joinpath(*rel_path.split('/'))
        path.parent.mkdir(parents=True, exist_ok=True)
        content = f'---\nprivacy: "synthetic"\n---\n\n{body}'
        path.write_bytes(content.encode('utf-8'))
        raw = path.read_bytes()
        return {
            'id': rel_path.replace('/', '-').replace('.md', '').lower(),
            'path': rel_path,
            'size': len(raw),
            'sha256': digest(raw),
            'source_references': [f'synthetic://fixture/{rel_path}'],
        }

    def _run_manifest(self, notes, subset_prefixes=None, source_kind='synthetic', personal_approved=False):
        manifest = {
            'schema': 'wiki-health-manifest-v1',
            'source_kind': source_kind,
            'client': 'codex-openai',
            'root': str(self.root),
            'owner_authorization': {
                'state': 'approved',
                'reference': 'synthetic-t16-slice2',
                'purpose': 'wiki-health-links-anchors-orphans',
                'personal_content_external_model_approved': personal_approved,
            },
            'notes': notes,
        }
        if subset_prefixes is not None:
            manifest['subset_prefixes'] = subset_prefixes
        self.manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        pin = digest(self.manifest_path.read_bytes())
        before = {p: p.read_bytes() for p in self.base.rglob('*') if p.is_file()}
        report = wiki_health.check_wiki_health(self.manifest_path, pin, 'codex-openai')
        after = {p: p.read_bytes() for p in self.base.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        return report

    def test_t02a_five_file_templates_pass_with_entry_points_qualified(self):
        repo_root = Path(__file__).resolve().parents[1] / 'templates' / 'vault'
        template_rels = ['AGENTS.md', 'CLAUDE.md', 'index.md', 'log.md', 'system/brain.md']
        notes = []
        for rel in template_rels:
            src_bytes = (repo_root / Path(*rel.split('/'))).read_bytes()
            dst = self.root.joinpath(*rel.split('/'))
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src_bytes)
            notes.append({
                'id': rel.replace('/', '-').replace('.md', '').lower(),
                'path': rel,
                'size': len(src_bytes),
                'sha256': digest(src_bytes),
                'source_references': [f'template://t02a/{rel}'],
            })

        report = self._run_manifest(notes, source_kind='canonical', personal_approved=True)
        self.assertEqual(report['broken_links'], [])
        self.assertEqual(report['missing_anchors'], [])
        self.assertEqual(report['orphan_candidates'], [])
        entry_paths = {item['relative_path'] for item in report['entry_points']}
        self.assertEqual(entry_paths, set(template_rels))
        for ep in report['entry_points']:
            self.assertEqual(ep['qualification'], 'intentional_entry_point')

    def test_broken_links_missing_anchors_orphans_and_external_links_distinguished(self):
        # Create an unselected file on disk with a canary; links to it must be qualified
        # as external_to_subset / unverified_outside_subset and NEVER opened or declared broken.
        ext_path = self.root / 'references' / 'external-spec.md'
        ext_path.parent.mkdir(parents=True, exist_ok=True)
        ext_path.write_text('---\nprivacy: "personal"\n---\n# Ext\nDENIED_CONTENT_CANARY_EXT_777\n', encoding='utf-8')

        notes = [
            self._write_synthetic(
                'index.md',
                '# Index\n\n'
                'Valid link: [[projects/alpha/design#Architecture|Alpha Design]]\n'
                'Valid md link: [Log](log.md#entries)\n'
                'Missing target in subset: [[projects/alpha/nonexistent-note]]\n'
                'Missing anchor in subset: [[projects/alpha/design#Missing Heading]]\n'
                'Outside subset wikilink: [[references/external-spec#Ext]]\n'
                'Outside subset md link: [Permanent](../permanent/lesson.md)\n'
                '```markdown\n'
                'Ignored code fence link: [[projects/alpha/ignored-in-code]]\n'
                '```\n'
                'Ignored inline code: `[[projects/alpha/ignored-inline]]`\n',
            ),
            self._write_synthetic(
                'log.md',
                '# Log\n\n## Entries\n\nRecorded [[projects/alpha/design]].\n',
            ),
            self._write_synthetic(
                'projects/alpha/design.md',
                '# Alpha Design\n\n## Architecture\n\nLocal self-anchor broken: [[#No Such Local Anchor]]\n',
            ),
            self._write_synthetic(
                'projects/alpha/orphan-note.md',
                '# Orphan Note\n\nThis note links to [[index]] but nothing links to it.\n',
            ),
        ]

        report = self._run_manifest(notes, subset_prefixes=['projects/alpha/'])
        serialized = json.dumps(report)
        self.assertNotIn('DENIED_CONTENT_CANARY', serialized)
        self.assertNotIn('ignored-in-code', serialized)
        self.assertNotIn('ignored-inline', serialized)

        # Broken target in subset: projects/alpha/nonexistent-note
        broken_targets = [b for b in report['broken_links'] if b['kind'] == 'missing_target']
        self.assertEqual(len(broken_targets), 1)
        self.assertEqual(broken_targets[0]['note_id'], 'index')
        self.assertEqual(broken_targets[0]['target'], 'projects/alpha/nonexistent-note')
        self.assertEqual(broken_targets[0]['source_references'], ['synthetic://fixture/index.md'])

        # Missing anchors: projects/alpha/design#Missing Heading and self-link #No Such Local Anchor
        self.assertEqual(len(report['missing_anchors']), 2)
        missing_anchor_names = {m['anchor'] for m in report['missing_anchors']}
        self.assertEqual(missing_anchor_names, {'Missing Heading', 'No Such Local Anchor'})

        # Orphans: projects/alpha/orphan-note.md is flagged; index.md and log.md are intentional entry points
        orphan_ids = [o['note_id'] for o in report['orphan_candidates']]
        self.assertEqual(orphan_ids, ['projects-alpha-orphan-note'])
        self.assertEqual(
            report['orphan_candidates'][0]['qualification'],
            'unlinked_within_authorized_subset',
        )

        # External links: references/external-spec and ../permanent/lesson.md are qualified, not broken
        ext_targets = {e['target'] for e in report['external_links']}
        self.assertIn('references/external-spec', ext_targets)
        self.assertIn('../permanent/lesson.md', ext_targets)
        for ext in report['external_links']:
            self.assertEqual(ext['status'], 'external_to_subset')
            self.assertEqual(ext['qualification'], 'unverified_outside_subset')


class WikiHealthSlice3ClaimsAndCliTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.root = self.base / 'test-vault' / 'synthetic'
        self.root.mkdir(parents=True)
        self.manifest_path = self.base / 'health-manifest.json'

    def _write_note(self, note_id, rel_path, content, refs):
        path = self.root.joinpath(*rel_path.split('/'))
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = content.encode('utf-8')
        path.write_bytes(raw)
        return {
            'id': note_id,
            'path': rel_path,
            'size': len(raw),
            'sha256': digest(raw),
            'source_references': list(refs),
        }

    def test_contradiction_and_stale_claim_candidates_preserve_provenance_and_roles(self):
        note_index = self._write_note(
            'index',
            'index.md',
            '---\nprivacy: "synthetic"\n---\n\n# Index\n\n'
            'Routes: [[projects/alpha/policy-a]] and [[projects/alpha/policy-b]].\n',
            ['synthetic://fixture/index'],
        )
        note_a = self._write_note(
            'policy-a',
            'projects/alpha/policy-a.md',
            '---\nprivacy: "synthetic"\n---\n\n# Policy A\n\n'
            'Claim: cloud-sync | Status: disabled | Date: 2026-10-01 | Basis: reported | Actor: owner\n'
            'Claim: legacy-import | Status: active | Date: 2026-09-15 | Basis: reported | Actor: owner | Stale-After: 2026-10-15\n',
            ['synthetic://fixture/policy-a'],
        )
        note_b = self._write_note(
            'policy-b',
            'projects/alpha/policy-b.md',
            '---\nprivacy: "synthetic"\n---\n\n# Policy B\n\n'
            'Claim: cloud-sync | Status: enabled | Date: 2026-11-01 | Basis: inferred | Actor: assistant\n'
            'Claim: audit-log | Status: pending | Date: unknown | Basis: reported | Actor: reviewer | Superseded-By: audit-v2\n',
            ['synthetic://fixture/policy-b'],
        )

        manifest = {
            'schema': 'wiki-health-manifest-v1',
            'source_kind': 'synthetic',
            'client': 'codex-openai',
            'root': str(self.root),
            'owner_authorization': {
                'state': 'approved',
                'reference': 'synthetic-t16-slice3',
                'purpose': 'wiki-health-claims',
                'personal_content_external_model_approved': False,
            },
            'subset_prefixes': ['projects/alpha/'],
            'notes': [note_index, note_a, note_b],
        }
        self.manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        pin = digest(self.manifest_path.read_bytes())

        before = {p: p.read_bytes() for p in self.base.rglob('*') if p.is_file()}
        report = wiki_health.check_wiki_health(
            self.manifest_path, pin, 'codex-openai', as_of_date='2026-11-05'
        )
        after = {p: p.read_bytes() for p in self.base.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

        # Verify contradiction candidate for cloud-sync
        self.assertEqual(len(report['contradiction_candidates']), 1)
        contradiction = report['contradiction_candidates'][0]
        self.assertEqual(contradiction['subject'], 'cloud-sync')
        self.assertEqual(contradiction['analysis_kind'], 'structural-lint')
        self.assertIs(contradiction['semantic_validation'], False)
        self.assertEqual(contradiction['values'], ['disabled', 'enabled'])
        self.assertEqual(contradiction['bases_present'], ['inferred', 'reported'])
        self.assertEqual(contradiction['actors_present'], ['assistant', 'owner'])
        self.assertIn('reported', contradiction['distinction_summary'])
        self.assertIn('inferred', contradiction['distinction_summary'])
        self.assertEqual(len(contradiction['claims']), 2)
        self.assertEqual(contradiction['claims'][0]['note_id'], 'policy-a')
        self.assertEqual(contradiction['claims'][0]['date'], '2026-10-01')
        self.assertEqual(contradiction['claims'][0]['claim_basis'], 'reported')
        self.assertEqual(contradiction['claims'][0]['actor'], 'owner')
        self.assertEqual(contradiction['claims'][1]['note_id'], 'policy-b')
        self.assertEqual(contradiction['claims'][1]['date'], '2026-11-01')
        self.assertEqual(contradiction['claims'][1]['claim_basis'], 'inferred')
        self.assertEqual(contradiction['claims'][1]['actor'], 'assistant')

        # Verify stale-claim candidates (superseded cloud-sync 2026-10-01, stale_after legacy-import, superseded_by audit-log)
        stale_by_subject = {item['subject']: item for item in report['stale_claim_candidates']}
        self.assertIn('cloud-sync', stale_by_subject)
        self.assertEqual(stale_by_subject['cloud-sync']['reason'], 'older_dated_claim_superseded')
        self.assertEqual(stale_by_subject['cloud-sync']['stale_claim']['date'], '2026-10-01')
        self.assertEqual(stale_by_subject['cloud-sync']['newer_evidence']['date'], '2026-11-01')
        self.assertIs(stale_by_subject['cloud-sync']['semantic_validation'], False)

        self.assertIn('legacy-import', stale_by_subject)
        self.assertEqual(stale_by_subject['legacy-import']['reason'], 'stale_after_exceeded')
        self.assertEqual(stale_by_subject['legacy-import']['reference_date'], '2026-11-05')

        self.assertIn('audit-log', stale_by_subject)
        self.assertEqual(stale_by_subject['audit-log']['reason'], 'explicitly_superseded')
        self.assertEqual(stale_by_subject['audit-log']['stale_claim']['date'], 'unknown')

    def test_cli_entrypoint_outputs_json_and_fails_closed_without_canary_leak(self):
        unselected_canary = self.root / 'canary.md'
        unselected_canary.write_text('DENIED_CONTENT_CANARY_CLI_888\n', encoding='utf-8')
        note = self._write_note(
            'index',
            'index.md',
            '---\nprivacy: "synthetic"\n---\n\n# Index\n\nClean index.\n',
            ['synthetic://fixture/index'],
        )
        manifest = {
            'schema': 'wiki-health-manifest-v1',
            'source_kind': 'synthetic',
            'client': 'codex-openai',
            'root': str(self.root),
            'owner_authorization': {
                'state': 'approved',
                'reference': 'synthetic-t16-cli',
                'purpose': 'wiki-health-cli',
                'personal_content_external_model_approved': False,
            },
            'notes': [note],
        }
        self.manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        pin = digest(self.manifest_path.read_bytes())

        import io
        from contextlib import redirect_stderr, redirect_stdout

        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = wiki_health.main([
                '--manifest', str(self.manifest_path),
                '--manifest-sha256', pin,
                '--client', 'codex-openai',
            ])
        self.assertEqual(code, 0)
        parsed = json.loads(out.getvalue())
        self.assertEqual(parsed['schema'], 'wiki-health-report-v1')
        self.assertNotIn('DENIED_CONTENT_CANARY', out.getvalue())
        self.assertNotIn('DENIED_CONTENT_CANARY', err.getvalue())

        # Bad sha256 fails closed with non-zero exit code
        out_bad = io.StringIO()
        err_bad = io.StringIO()
        with redirect_stdout(out_bad), redirect_stderr(err_bad):
            bad_code = wiki_health.main([
                '--manifest', str(self.manifest_path),
                '--manifest-sha256', '0' * 64,
                '--client', 'codex-openai',
            ])
        self.assertEqual(bad_code, 2)
        self.assertNotIn('DENIED_CONTENT_CANARY', err_bad.getvalue())

    def test_frontmatter_claims_duplicate_json_keys_and_reparse_refusal(self):
        note_fm = self._write_note(
            'fm-old',
            'projects/alpha/fm-old.md',
            '---\n'
            'privacy: "synthetic"\n'
            'claim_subject: "publisher-mode"\n'
            'claim_status: "create-only"\n'
            'claim_date: "2026-10-10"\n'
            'claim_basis: "reported"\n'
            'actor: "owner"\n'
            '---\n\n'
            '# Frontmatter Claim Old\n\nSee [[projects/alpha/fm-new]].\n',
            ['synthetic://fixture/fm-old'],
        )
        note_fm_new = self._write_note(
            'fm-new',
            'projects/alpha/fm-new.md',
            '---\n'
            'privacy: "synthetic"\n'
            'claim_subject: "publisher-mode"\n'
            'claim_status: "update-enabled"\n'
            'claim_date: "2026-11-02"\n'
            'claim_basis: "inferred"\n'
            'actor: "assistant"\n'
            '---\n\n'
            '# Frontmatter Claim New\n\nSee [[projects/alpha/fm-old]].\n',
            ['synthetic://fixture/fm-new'],
        )
        manifest = {
            'schema': 'wiki-health-manifest-v1',
            'source_kind': 'synthetic',
            'client': 'codex-openai',
            'root': str(self.root),
            'owner_authorization': {
                'state': 'approved',
                'reference': 'synthetic-t16-slice4',
                'purpose': 'wiki-health-frontmatter-claims',
                'personal_content_external_model_approved': False,
            },
            'subset_prefixes': ['projects/alpha/'],
            'notes': [note_fm, note_fm_new],
        }
        self.manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        pin = digest(self.manifest_path.read_bytes())

        report = wiki_health.check_wiki_health(self.manifest_path, pin, 'codex-openai')
        self.assertEqual(len(report['contradiction_candidates']), 1)
        self.assertEqual(report['contradiction_candidates'][0]['subject'], 'publisher-mode')
        self.assertEqual(report['contradiction_candidates'][0]['values'], ['create-only', 'update-enabled'])
        self.assertEqual(len(report['stale_claim_candidates']), 1)
        self.assertEqual(report['stale_claim_candidates'][0]['stale_claim']['note_id'], 'fm-old')

        # Duplicate JSON key refusal
        raw_dup = b'{"schema": "wiki-health-manifest-v1", "schema": "wiki-health-manifest-v1"}'
        self.manifest_path.write_bytes(raw_dup)
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            wiki_health.check_wiki_health(self.manifest_path, digest(raw_dup), 'codex-openai')


if __name__ == '__main__':
    unittest.main()



