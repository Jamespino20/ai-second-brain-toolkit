"""Explicitly invoked read-only wiki health checker over a hash-pinned manifest.

Operates strictly over an owner-approved, hash-verified subset of Markdown notes.
Performs structural lint only (no semantic AI validation, no full-vault scan,
no background watcher, and zero canonical or staging writes).
"""
import argparse
import json
from pathlib import Path, PurePosixPath
import re
import sys

from selected_memory import checked_path, citation, digest, is_safe_source_reference

_CLIENTS = ('codex-openai', 'claude-anthropic', 'chatgpt-openai')
_MAX_MANIFEST_BYTES = 1048576
_MAX_NOTE_BYTES = 128000
_MAX_NOTES = 256
_DEFAULT_ENTRY_POINTS = frozenset({
    'agents.md',
    'claude.md',
    'index.md',
    'log.md',
    'system/brain.md',
})
_WIKILINK_RE = re.compile(r'\[\[([^\[\]\n]+)\]\]')
_MDLINK_RE = re.compile(r'(?<!!)\[([^\[\]\n]+)\]\(([^()\s]+)(?:\s+"[^"]*")?\)')
_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+?)\s*#*\s*$')
_ISO_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
_KV_TOKEN_RE = re.compile(
    r'\b(claim|subject|topic|status|state|value|decision|date|as_of|basis|claim_basis|'
    r'evidence_kind|actor|role|stale_after|stale-after|superseded_by|superseded-by)'
    r'\s*[:=]\s*([^|,;\n]+)',
    re.I,
)


def _unique_json_loads(raw_bytes):
    def _unique_pairs(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError('Duplicate JSON key refused')
            obj[key] = value
        return obj

    try:
        parsed = json.loads(raw_bytes.decode('utf-8'), object_pairs_hook=_unique_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError('Invalid manifest JSON') from error
    if not isinstance(parsed, dict):
        raise ValueError('Invalid manifest structure')
    return parsed


def _validate_relative_md_path(relative):
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError('Invalid or duplicate selected-note identity/path')
    rel = PurePosixPath(relative)
    if (rel.is_absolute()
            or rel.suffix != '.md'
            or str(rel) != relative
            or any(c in relative for c in '\\:*?"<>|\x00')
            or any(ord(c) < 32 for c in relative)
            or any(part.casefold() in ('..', '.', '.git', '.obsidian')
                   or part.endswith((' ', '.')) for part in rel.parts)):
        raise ValueError('Invalid or duplicate selected-note identity/path')
    return rel


def _validate_prefix(prefix):
    if not isinstance(prefix, str) or not prefix.endswith('/') or prefix.startswith('/'):
        raise ValueError('Invalid subset prefix')
    _validate_relative_md_path(prefix + 'probe.md')
    return prefix


def _strip_inline_code(line):
    return re.sub(r'`[^`]*`', lambda m: ' ' * len(m.group(0)), line)


def _heading_keys(heading_text):
    cleaned = re.sub(r'[`*_~]', '', heading_text).strip()
    collapsed = re.sub(r'\s+', ' ', cleaned).casefold()
    slug = re.sub(r'[^\w\s-]', '', collapsed)
    slug = re.sub(r'[\s]+', '-', slug).strip('-')
    keys = {collapsed}
    if slug:
        keys.add(slug)
    return keys


def _iter_body_lines(lines):
    """Yield (line_number_1_based, line_text) outside YAML frontmatter and fenced code blocks."""
    idx = 0
    total = len(lines)
    if total > 0 and lines[0].strip() == '---':
        idx = 1
        while idx < total and lines[idx].strip() != '---':
            idx += 1
        if idx < total:
            idx += 1

    in_fence = False
    fence_marker = ''
    while idx < total:
        line = lines[idx]
        line_no = idx + 1
        idx += 1
        stripped = line.lstrip()
        fence_match = re.match(r'^(`{3,}|~{3,})', stripped)
        if fence_match:
            marker = fence_match.group(1)[0]
            if not in_fence:
                in_fence = True
                fence_marker = marker
                continue
            if marker == fence_marker:
                in_fence = False
                fence_marker = ''
                continue
        if not in_fence:
            yield line_no, line


def _parse_claim_line(line_no, raw_line):
    scannable = _strip_inline_code(raw_line)
    fields = {}
    for match in _KV_TOKEN_RE.finditer(scannable):
        key = match.group(1).casefold().replace('-', '_')
        val = match.group(2).strip().strip('"\'[]()')
        fields[key] = val

    subject = fields.get('claim') or fields.get('subject') or fields.get('topic')
    value = fields.get('status') or fields.get('state') or fields.get('value') or fields.get('decision')
    if not subject or not value:
        return None

    raw_date = (fields.get('date') or fields.get('as_of') or 'unknown').strip()
    date_val = raw_date if _ISO_DATE_RE.match(raw_date) else 'unknown'
    basis = (fields.get('basis') or fields.get('claim_basis') or fields.get('evidence_kind') or 'unspecified').strip().casefold()
    actor = (fields.get('actor') or fields.get('role') or 'unspecified').strip().casefold()
    stale_after = fields.get('stale_after')
    if stale_after and not _ISO_DATE_RE.match(stale_after):
        stale_after = None
    superseded_by = fields.get('superseded_by')

    return {
        'line': line_no,
        'subject': subject.strip().casefold(),
        'value': value.strip().casefold(),
        'date': date_val,
        'claim_basis': basis,
        'actor': actor,
        'stale_after': stale_after,
        'superseded_by': superseded_by.strip() if superseded_by else None,
        'excerpt': raw_line.strip()[:500],
    }


def _extract_frontmatter_claim(lines):
    if not lines or lines[0].strip() != '---':
        return None
    fm_fields = {}
    subject_line = 1
    for idx in range(1, len(lines)):
        stripped = lines[idx].strip()
        if stripped == '---':
            break
        kv = re.match(r'^([A-Za-z0-9_-]+)\s*:\s*(.+?)\s*$', stripped)
        if kv:
            key = kv.group(1).casefold().replace('-', '_')
            val = kv.group(2).strip().strip('"\'')
            fm_fields[key] = val
            if key in ('claim_subject', 'subject', 'topic'):
                subject_line = idx + 1
    subject = fm_fields.get('claim_subject') or fm_fields.get('subject') or fm_fields.get('topic')
    value = fm_fields.get('claim_status') or fm_fields.get('status') or fm_fields.get('state') or fm_fields.get('decision')
    if not subject or not value:
        return None
    raw_date = (fm_fields.get('claim_date') or fm_fields.get('date') or fm_fields.get('as_of') or 'unknown').strip()
    date_val = raw_date if _ISO_DATE_RE.match(raw_date) else 'unknown'
    basis = (fm_fields.get('claim_basis') or fm_fields.get('basis') or fm_fields.get('evidence_kind') or 'unspecified').strip().casefold()
    actor = (fm_fields.get('actor') or fm_fields.get('role') or 'unspecified').strip().casefold()
    stale_after = fm_fields.get('stale_after')
    if stale_after and not _ISO_DATE_RE.match(stale_after):
        stale_after = None
    superseded_by = fm_fields.get('superseded_by')
    return {
        'line': subject_line,
        'subject': subject.strip().casefold(),
        'value': value.strip().casefold(),
        'date': date_val,
        'claim_basis': basis,
        'actor': actor,
        'stale_after': stale_after,
        'superseded_by': superseded_by.strip() if superseded_by else None,
        'excerpt': f'frontmatter:{subject}={value} ({date_val})',
    }


def _extract_headings_links_and_claims(lines):
    headings = set()
    links = []
    claims = []
    fm_claim = _extract_frontmatter_claim(lines)
    if fm_claim is not None:
        claims.append(fm_claim)
    for line_no, raw_line in _iter_body_lines(lines):
        heading_match = _HEADING_RE.match(raw_line)
        if heading_match:
            headings.update(_heading_keys(heading_match.group(2)))
        scannable = _strip_inline_code(raw_line)
        for match in _WIKILINK_RE.finditer(scannable):
            inner = match.group(1).strip()
            target_part = inner.split('|', 1)[0].strip()
            if '#' in target_part:
                target_note, anchor = target_part.split('#', 1)
            else:
                target_note, anchor = target_part, ''
            links.append({
                'line': line_no,
                'syntax': 'wikilink',
                'raw': match.group(0),
                'target': target_note.strip(),
                'anchor': anchor.strip(),
            })
        for match in _MDLINK_RE.finditer(scannable):
            href = match.group(2).strip()
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', href):
                continue
            if '#' in href:
                target_note, anchor = href.split('#', 1)
            else:
                target_note, anchor = href, ''
            links.append({
                'line': line_no,
                'syntax': 'markdown',
                'raw': match.group(0),
                'target': target_note.strip(),
                'anchor': anchor.strip(),
            })
        claim = _parse_claim_line(line_no, raw_line)
        if claim is not None:
            claims.append(claim)
    return headings, links, claims


def _normalize_target_candidates(source_rel_path, raw_target, syntax):
    """Return (escaped_root, normalized_posix_target, candidate_md_paths_casefold)."""
    if not raw_target:
        return False, '', [source_rel_path.casefold()]

    cleaned = raw_target.replace('\\', '/').strip()
    source_parent = PurePosixPath(source_rel_path).parent

    def _collapse_posix(parts):
        stack = []
        for part in parts:
            if part in ('', '.'):
                continue
            if part == '..':
                if not stack:
                    return None
                stack.pop()
            else:
                stack.append(part)
        return '/'.join(stack)

    if cleaned.startswith('./') or cleaned.startswith('../'):
        base_parts = [] if str(source_parent) == '.' else list(source_parent.parts)
        collapsed = _collapse_posix(base_parts + cleaned.split('/'))
        if collapsed is None:
            return True, cleaned, []
        norm = collapsed
    else:
        collapsed = _collapse_posix(cleaned.split('/'))
        if collapsed is None:
            return True, cleaned, []
        norm = collapsed

    md_norm = norm if norm.casefold().endswith('.md') else f'{norm}.md'
    candidates = [md_norm.casefold()]

    if str(source_parent) != '.' and not cleaned.startswith(('./', '../')) and '/' not in cleaned:
        rel_in_parent = f'{source_parent}/{md_norm}'.casefold()
        if rel_in_parent not in candidates:
            candidates.append(rel_in_parent)

    return False, norm, candidates


def _is_entry_point(item):
    rel_fold = item['relative_path'].casefold()
    if rel_fold in _DEFAULT_ENTRY_POINTS:
        return True
    if PurePosixPath(rel_fold).name == 'index.md':
        return True
    if item['note'].get('entry_point') is True:
        return True
    return False


def _is_within_authoritative_subset(norm_target, candidates, subset_prefixes, active_dirs):
    check_paths = candidates or [norm_target.casefold()]
    if subset_prefixes is not None:
        folded_prefixes = [p.casefold() for p in subset_prefixes]
        for cand in check_paths:
            if any(cand.startswith(pfx) for pfx in folded_prefixes):
                return True
        return False
    for cand in check_paths:
        parent = str(PurePosixPath(cand).parent).casefold()
        if parent in active_dirs:
            return True
    return False


def _analyze_claims(loaded, as_of_date=None):
    if as_of_date is not None and (not isinstance(as_of_date, str) or not _ISO_DATE_RE.match(as_of_date)):
        raise ValueError('as_of_date must be YYYY-MM-DD')

    all_claims = []
    by_subject = {}
    for item in loaded:
        cite = item['citation']
        for claim in item['claims']:
            enriched = {
                **cite,
                'line': claim['line'],
                'subject': claim['subject'],
                'value': claim['value'],
                'date': claim['date'],
                'claim_basis': claim['claim_basis'],
                'actor': claim['actor'],
                'stale_after': claim['stale_after'],
                'superseded_by': claim['superseded_by'],
                'excerpt': claim['excerpt'],
            }
            all_claims.append(enriched)
            by_subject.setdefault(claim['subject'], []).append(enriched)

    known_dates = [c['date'] for c in all_claims if _ISO_DATE_RE.match(c['date'])]
    reference_date = as_of_date or (max(known_dates) if known_dates else None)

    contradiction_candidates = []
    stale_claim_candidates = []

    for subject in sorted(by_subject):
        subject_claims = sorted(
            by_subject[subject],
            key=lambda c: (c['date'] if _ISO_DATE_RE.match(c['date']) else '0000-00-00', c['note_id'], c['line']),
        )
        distinct_values = sorted({c['value'] for c in subject_claims})
        if len(distinct_values) > 1:
            bases_present = sorted({c['claim_basis'] for c in subject_claims})
            actors_present = sorted({c['actor'] for c in subject_claims})
            summary_parts = [
                f"{c['actor']} ({c['claim_basis']}: {c['value']} @ {c['date']})"
                for c in subject_claims
            ]
            contradiction_candidates.append({
                'subject': subject,
                'analysis_kind': 'structural-lint',
                'semantic_validation': False,
                'values': distinct_values,
                'bases_present': bases_present,
                'actors_present': actors_present,
                'distinction_summary': ' vs '.join(summary_parts),
                'claims': subject_claims,
            })

        dated_claims = [c for c in subject_claims if _ISO_DATE_RE.match(c['date'])]
        newest_dated = max(dated_claims, key=lambda c: c['date']) if dated_claims else None

        for claim in subject_claims:
            if claim['superseded_by']:
                stale_claim_candidates.append({
                    'subject': subject,
                    'analysis_kind': 'structural-lint',
                    'semantic_validation': False,
                    'reason': 'explicitly_superseded',
                    'superseded_by': claim['superseded_by'],
                    'stale_claim': claim,
                    'newer_evidence': newest_dated if newest_dated and newest_dated is not claim else None,
                })
            elif (newest_dated is not None
                  and _ISO_DATE_RE.match(claim['date'])
                  and claim['date'] < newest_dated['date']
                  and claim['value'] != newest_dated['value']):
                stale_claim_candidates.append({
                    'subject': subject,
                    'analysis_kind': 'structural-lint',
                    'semantic_validation': False,
                    'reason': 'older_dated_claim_superseded',
                    'stale_claim': claim,
                    'newer_evidence': newest_dated,
                })
            elif claim['stale_after'] and reference_date and reference_date > claim['stale_after']:
                stale_claim_candidates.append({
                    'subject': subject,
                    'analysis_kind': 'structural-lint',
                    'semantic_validation': False,
                    'reason': 'stale_after_exceeded',
                    'reference_date': reference_date,
                    'stale_claim': claim,
                    'newer_evidence': None,
                })

    return contradiction_candidates, stale_claim_candidates


def load_health_subset(manifest_path, manifest_sha256, client):
    """Validate and load the exact hash-pinned note subset without scanning directories."""
    if not isinstance(manifest_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', manifest_sha256):
        raise ValueError('Manifest SHA-256 pin must be 64 lowercase hex characters')
    mpath = checked_path(manifest_path)
    if mpath.stat().st_size > _MAX_MANIFEST_BYTES:
        raise ValueError('Manifest too large')
    raw_manifest = mpath.read_bytes()
    if len(raw_manifest) > _MAX_MANIFEST_BYTES:
        raise ValueError('Manifest too large')
    if digest(raw_manifest) != manifest_sha256:
        raise ValueError('Manifest changed; explicit review and repin required')

    manifest = _unique_json_loads(raw_manifest)
    if manifest.get('schema') != 'wiki-health-manifest-v1':
        raise ValueError('Unsupported manifest schema')
    if client not in _CLIENTS or manifest.get('client') != client:
        raise ValueError('Client not authorized')

    auth = manifest.get('owner_authorization', {})
    if not isinstance(auth, dict) or auth.get('state') != 'approved' or not str(auth.get('reference', '')).strip():
        raise ValueError('Explicit owner authorization required')

    kind = manifest.get('source_kind')
    root = checked_path(manifest.get('root', ''), directory=True)
    if kind == 'synthetic':
        if 'test-vault' not in [part.casefold() for part in root.parts]:
            raise ValueError('Synthetic corpus must be in the disposable test vault')
    elif kind == 'canonical':
        if auth.get('personal_content_external_model_approved') is not True:
            raise ValueError('Separate personal-content external-model approval required')
    else:
        raise ValueError('Unsupported corpus kind')

    subset_prefixes = manifest.get('subset_prefixes')
    if subset_prefixes is not None:
        if not isinstance(subset_prefixes, list) or len(subset_prefixes) > _MAX_NOTES:
            raise ValueError('Invalid subset_prefixes')
        for pfx in subset_prefixes:
            _validate_prefix(pfx)

    notes = manifest.get('notes')
    if not isinstance(notes, list) or not 1 <= len(notes) <= _MAX_NOTES:
        raise ValueError('Manifest must select 1 to 256 exact notes')

    seen_ids = set()
    seen_paths = set()
    loaded = []
    for note in notes:
        if not isinstance(note, dict):
            raise ValueError('Invalid note entry')
        note_id = note.get('id')
        relative = note.get('path')
        if not isinstance(note_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', note_id) or note_id in seen_ids:
            raise ValueError('Invalid or duplicate selected-note identity/path')
        rel = _validate_relative_md_path(relative)
        folded = relative.casefold()
        if folded in seen_paths:
            raise ValueError('Invalid or duplicate selected-note identity/path')
        seen_ids.add(note_id)
        seen_paths.add(folded)

        expected_size = note.get('size')
        expected_sha = note.get('sha256')
        if type(expected_size) is not int or expected_size < 0 or not isinstance(expected_sha, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_sha):
            raise ValueError('Invalid note size or sha256 pin')
        if expected_size > _MAX_NOTE_BYTES:
            raise ValueError('Selected note too large')

        refs = note.get('source_references', [])
        if not isinstance(refs, list) or len(refs) > 16 or not all(isinstance(r, str) and r.strip() and len(r) <= 512 and is_safe_source_reference(r) for r in refs):
            raise ValueError('Invalid source_references')

        full_path = checked_path(root.joinpath(*rel.parts))
        if not full_path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Selected note escapes configured corpus')
        if full_path.stat().st_size > _MAX_NOTE_BYTES:
            raise ValueError('Selected note too large')
        data = full_path.read_bytes()
        if len(data) > _MAX_NOTE_BYTES:
            raise ValueError('Selected note too large')
        if len(data) != expected_size or digest(data) != expected_sha:
            raise ValueError('Selected note changed; stale health check refused')

        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError as error:
            raise ValueError('Selected note is not valid UTF-8') from error

        if kind == 'synthetic':
            front = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, re.S)
            if front is None or re.findall(r'^privacy:\s*(.*?)\s*$', front.group(1), re.M) != ['"synthetic"']:
                raise ValueError('Synthetic-only configuration refuses personal material')

        lines = text.splitlines()
        headings, links, claims = _extract_headings_links_and_claims(lines)
        loaded.append({
            'note': note,
            'path': full_path,
            'relative_path': relative,
            'raw_bytes': data,
            'text': text,
            'lines': lines,
            'headings': headings,
            'links': links,
            'claims': claims,
            'citation': citation(manifest, note, full_path),
        })

    return manifest, mpath, raw_manifest, loaded


def _verify_unchanged(mpath, raw_manifest, loaded):
    if checked_path(mpath).read_bytes() != raw_manifest:
        raise ValueError('Manifest changed during health check; refused')
    for item in loaded:
        current = checked_path(item['path']).read_bytes()
        if current != item['raw_bytes']:
            raise ValueError('Selected note changed during health check; refused')


def check_wiki_health(manifest_path, manifest_sha256, client, as_of_date=None):
    """Run read-only structural health checks over the hash-pinned note subset."""
    manifest, mpath, raw_manifest, loaded = load_health_subset(manifest_path, manifest_sha256, client)

    by_rel_path = {item['relative_path'].casefold(): item for item in loaded}
    by_basename = {}
    for item in loaded:
        bname = PurePosixPath(item['relative_path']).name.casefold()
        by_basename.setdefault(bname, []).append(item)

    active_dirs = {str(PurePosixPath(item['relative_path']).parent).casefold() for item in loaded}
    subset_prefixes = manifest.get('subset_prefixes')
    incoming_counts = {item['note']['id']: 0 for item in loaded}

    broken_links = []
    missing_anchors = []
    external_links = []

    for item in loaded:
        src_cite = item['citation']
        src_id = item['note']['id']
        for link in item['links']:
            raw_target = link['target']
            anchor = link['anchor']
            escaped, norm_target, candidates = _normalize_target_candidates(
                item['relative_path'], raw_target, link['syntax']
            )

            target_item = None
            if not escaped:
                for cand in candidates:
                    if cand in by_rel_path:
                        target_item = by_rel_path[cand]
                        break
                if target_item is None and raw_target and '/' not in raw_target.replace('\\', '/'):
                    bname = (raw_target if raw_target.casefold().endswith('.md') else f'{raw_target}.md').casefold()
                    matches = by_basename.get(bname, [])
                    if len(matches) == 1:
                        target_item = matches[0]

            if target_item is not None:
                target_id = target_item['note']['id']
                if target_id != src_id:
                    incoming_counts[target_id] += 1
                if anchor:
                    anchor_keys = _heading_keys(anchor)
                    if not (anchor_keys & target_item['headings']):
                        anchor_record = {
                            **src_cite,
                            'line': link['line'],
                            'kind': 'missing_anchor',
                            'status': 'missing_anchor',
                            'raw_link': link['raw'],
                            'target': raw_target or item['relative_path'],
                            'target_note_id': target_id,
                            'target_relative_path': target_item['relative_path'],
                            'anchor': anchor,
                        }
                        missing_anchors.append(anchor_record)
                        broken_links.append(anchor_record)
            else:
                if not escaped and _is_within_authoritative_subset(
                    norm_target, candidates, subset_prefixes, active_dirs
                ):
                    broken_links.append({
                        **src_cite,
                        'line': link['line'],
                        'kind': 'missing_target',
                        'status': 'broken_within_subset',
                        'raw_link': link['raw'],
                        'target': raw_target,
                        'anchor': anchor or None,
                    })
                else:
                    external_links.append({
                        **src_cite,
                        'line': link['line'],
                        'raw_link': link['raw'],
                        'target': raw_target,
                        'anchor': anchor or None,
                        'status': 'external_to_subset',
                        'qualification': 'unverified_outside_subset',
                    })

    entry_points = []
    orphan_candidates = []
    for item in loaded:
        nid = item['note']['id']
        inc = incoming_counts[nid]
        if _is_entry_point(item):
            entry_points.append({
                **item['citation'],
                'incoming_link_count': inc,
                'qualification': 'intentional_entry_point',
            })
        elif inc == 0:
            orphan_candidates.append({
                **item['citation'],
                'incoming_link_count': 0,
                'qualification': 'unlinked_within_authorized_subset',
            })

    contradiction_candidates, stale_claim_candidates = _analyze_claims(loaded, as_of_date=as_of_date)
    _verify_unchanged(mpath, raw_manifest, loaded)

    return {
        'schema': 'wiki-health-report-v1',
        'mode': 'read-only-wiki-health',
        'analysis_kind': 'structural-lint',
        'semantic_validation': False,
        'canonical_side_effects': 'none',
        'repairs_applied': 0,
        'repair_routing': 'T05/T07 reviewed workflows required',
        'source_kind': manifest['source_kind'],
        'client': manifest['client'],
        'authorized_note_count': len(loaded),
        'notes': [item['citation'] for item in loaded],
        'broken_links': broken_links,
        'missing_anchors': missing_anchors,
        'orphan_candidates': orphan_candidates,
        'entry_points': entry_points,
        'external_links': external_links,
        'contradiction_candidates': contradiction_candidates,
        'stale_claim_candidates': stale_claim_candidates,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Run an explicitly invoked read-only wiki health report over a hash-pinned manifest.'
    )
    parser.add_argument('--manifest', required=True, help='Absolute path to wiki-health-manifest-v1 JSON')
    parser.add_argument('--manifest-sha256', required=True, help='Independently recorded SHA-256 of the manifest')
    parser.add_argument('--client', required=True, choices=_CLIENTS, help='Authorized client identifier')
    parser.add_argument('--as-of-date', default=None, help='Optional YYYY-MM-DD reference date for stale-after checks')
    args = parser.parse_args(argv)
    try:
        report = check_wiki_health(
            args.manifest,
            args.manifest_sha256,
            args.client,
            as_of_date=args.as_of_date,
        )
    except (ValueError, OSError) as error:
        print(json.dumps({'status': 'refused', 'error': str(error)}), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
