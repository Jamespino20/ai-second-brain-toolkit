"""Local validation and candidate staging for supported `codex exec --json` output.

No model/network calls, transcript discovery, canonical writes, or memory database.
Raw input is restricted evidence. Assistant assertions never become observed facts.
"""
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from migrate import digest, json_bytes, private_root, render, safe_id, validate_candidate, write_new
from selected_memory import checked_path

MAX_BYTES = 8 * 1024 * 1024
KINDS = {'outcome', 'decision', 'lesson', 'milestone'}
BASES = {'user-stated', 'assistant-reported', 'inferred'}
PROVENANCE_TEXT = 'The originating capture receipt records this proposal\'s source provenance.'
LEGACY_PROVENANCE_TEXT = 'Additional identical-session provenance is recorded in private capture receipts.'
RISK_PATTERNS = {
    'credential': r'(?i)(?:gh[pousr]_[a-z0-9_]{20,}|github_pat_[a-z0-9_]{20,}|sk-(?:proj-|ant-)?[a-z0-9_-]{24,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)',
    'secret_assignment': r'(?i)\b(?:api[_-]?key|access[_-]?token|password|secret)\b["\']?\s*[:=]\s*(?:["\'][^"\'\r\n]+["\']|[^\s"\',;{}\[\]]+)',
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
    'user_path': r'(?i)(?:[a-z]:[\\/]+Users[\\/]+|/Users/|/home/)',
    'jwt': r'\beyJ[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',
}


class CaptureError(ValueError):
    """Safe error code only; raw source values must never enter console errors."""


def privacy_check(text):
    # Also recognize ASCII JSON escapes and escaped quotes in serialized fields.
    # This remains a heuristic guard, not a general secret/PII classifier.
    text = re.sub(r'\\u00([0-9a-fA-F]{2})', lambda match: chr(int(match[1], 16)), text)
    text = text.replace('\\"', '"').replace("\\'", "'")
    for category, pattern in RISK_PATTERNS.items():
        if re.search(pattern, text):
            raise CaptureError('PRIVACY_' + category.upper())


def content_digest(report, privacy):
    return digest(json.dumps({'report': report, 'source_privacy': privacy},
                             sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))


def load_config(path):
    try:
        path = checked_path(path).resolve()
        data = path.read_bytes()
        config = json.loads(data)
        if (set(config) != {'schema', 'enabled', 'workspace', 'allowed_cwds', 'profile', 'profile_sha256', 'source_privacy'}
                or config['schema'] != 'codex-capture-config-v1' or type(config['enabled']) is not bool
                or config['source_privacy'] not in ('synthetic', 'personal')
                or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', config['profile'])
                or not re.fullmatch(r'[0-9a-f]{64}', config['profile_sha256'])):
            raise CaptureError('INVALID_CONFIG')
        root = private_root(config['workspace'])
        checked_path(root, directory=True)
        checked_path(root / '.private-staging.json')
        if not path.is_relative_to(root):
            raise CaptureError('CONFIG_OUTSIDE_PRIVATE_WORKSPACE')
        cwds = config['allowed_cwds']
        if not isinstance(cwds, list) or not 1 <= len(cwds) <= 16:
            raise CaptureError('INVALID_CWD_ALLOWLIST')
        for entry in cwds:
            cwd = checked_path(entry, directory=True)
            if any(part.casefold().startswith('onedrive') for part in cwd.parts):
                raise CaptureError('SYNCED_CWD_REFUSED')
        return config, root, digest(data)
    except CaptureError:
        raise
    except (OSError, ValueError, KeyError, TypeError):
        raise CaptureError('UNSAFE_OR_INVALID_CONFIG') from None


def verify_profile(config):
    # CLI 0.164 silently falls back if a selected profile file does not exist.
    # Refuse before model launch, and recheck before staging. Never trust a name alone.
    home = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex'))
    try:
        profile = checked_path(home / (config['profile'] + '.config.toml'))
        if digest(profile.read_bytes()) != config['profile_sha256']:
            raise CaptureError('PROFILE_CHANGED')
    except (OSError, ValueError) as error:
        if isinstance(error, CaptureError):
            raise
        raise CaptureError('PROFILE_MISSING_OR_UNSAFE') from None


def validate_report(value, prompt):
    if (not isinstance(value, dict) or set(value) != {'schema_version', 'items'}
            or value['schema_version'] != '1.0' or not isinstance(value['items'], list)
            or len(value['items']) > 8):
        raise CaptureError('INVALID_REPORT')
    seen = set()
    for item in value['items']:
        if (not isinstance(item, dict) or set(item) != {'kind', 'text', 'basis', 'source_quote'}
                or not isinstance(item['kind'], str) or item['kind'] not in KINDS
                or not isinstance(item['basis'], str) or item['basis'] not in BASES
                or not isinstance(item['text'], str) or not 1 <= len(item['text'].strip()) <= 800
                or not isinstance(item['source_quote'], str) or len(item['source_quote']) > 800):
            raise CaptureError('INVALID_ITEM')
        if item['basis'] == 'user-stated' and (not item['source_quote']
                or item['source_quote'] not in prompt or item['text'] != item['source_quote']):
            raise CaptureError('UNSUPPORTED_USER_CLAIM')
        for field in item.values():
            privacy_check(field)
        identity = json.dumps(item, sort_keys=True)
        if identity in seen:
            raise CaptureError('DUPLICATE_ITEM')
        seen.add(identity)
    return value


def completed_report(events_raw, final_raw, prompt, exit_code):
    if exit_code != 0:
        raise CaptureError('CODEX_PROCESS_FAILED')
    if (not events_raw or len(events_raw) > MAX_BYTES or not final_raw or len(final_raw) > 16000
            or len(prompt.encode('utf-8')) > 32000):
        raise CaptureError('MISSING_OR_OVERSIZED_OUTPUT')
    try:
        privacy_check(prompt)
        lines = events_raw.decode('utf-8').splitlines()
        if any(not line.strip() for line in lines):
            raise CaptureError('BLANK_EVENT_LINE')
        events = [json.loads(line) for line in lines]
        if any(not isinstance(event, dict) or not isinstance(event.get('item', {}), dict) for event in events):
            raise CaptureError('INVALID_EVENT_SHAPE')
        value = validate_report(json.loads(final_raw), prompt)
        if any(event.get('type') in ('error', 'turn.failed') for event in events):
            raise CaptureError('CODEX_EVENT_FAILURE')
        sessions = [event['thread_id'] for event in events if event.get('type') == 'thread.started']
        starts = [i for i, event in enumerate(events) if event.get('type') == 'turn.started']
        completions = [i for i, event in enumerate(events) if event.get('type') == 'turn.completed']
        if len(sessions) != 1 or len(starts) != 1 or len(completions) != 1:
            raise CaptureError('INCOMPLETE_OR_MULTITURN_STREAM')
        # CLI 0.164 emits startup configuration warnings as item errors before
        # turn.started. Preserve their count; never ignore errors after start.
        diagnostics = [i for i, event in enumerate(events) if event.get('item', {}).get('type') == 'error']
        if any(i >= starts[0] for i in diagnostics):
            raise CaptureError('CODEX_EVENT_FAILURE')
        privacy_check(sessions[0])
        session_id = safe_id(sessions[0])
        matches = []
        for i, event in enumerate(events):
            item = event.get('item', {})
            if (event.get('type') == 'item.completed' and item.get('type') == 'agent_message'
                    and starts[0] < i < completions[0]):
                try:
                    if json.loads(item.get('text', '')) == value:
                        privacy_check(item['id'])
                        matches.append((i + 1, safe_id(item['id'])))
                except CaptureError:
                    raise
                except (ValueError, TypeError):
                    continue
        if not matches:
            raise CaptureError('FINAL_OUTPUT_NOT_IN_EVENT_STREAM')
        line, item_id = matches[-1]
        return value, session_id, line, item_id, len(diagnostics)
    except CaptureError:
        raise
    except (ValueError, KeyError, TypeError, UnicodeError):
        raise CaptureError('INVALID_CODEX_OUTPUT') from None


def receipt_path(root, session, events_sha):
    key = digest(json_bytes({'session': session, 'events_sha256': events_sha}))
    return root / 'staging/codex-capture/receipts' / (key + '.json')


def report_receipt(value, session, line, item, diagnostics, events, final, prompt, privacy):
    raw_sha = digest(events)
    result = {'session_id': session, 'events_sha256': raw_sha,
              'final_sha256': digest(final), 'prompt_sha256': digest(prompt.encode('utf-8')),
              'startup_diagnostic_count': diagnostics,
              'source': f'archive/{raw_sha}.codex-events.jsonl#L{line}/item/{item}',
              'source_privacy': privacy, 'external_processing': False,
              'observed_runner_facts': {'process_exit_code': 0, 'turn_completed': True},
              'domain_claims_independently_verified': False, 'proposals': 0}
    if value['items']:
        content_sha = content_digest(value, privacy)
        result.update(content_sha256=content_sha,
                      candidate='staging/codex-capture/candidates/' + content_sha + '.json',
                      proposal='test-vault/logs/codex-capture/' + content_sha + '.md')
    return result


def read_record(path, limit, code):
    try:
        path = checked_path(path)
        if path.stat().st_size > limit:
            raise CaptureError(code)
        return path.read_bytes()
    except (OSError, ValueError):
        raise CaptureError(code) from None


def read_archive(root, sha, suffix, limit):
    if not isinstance(sha, str) or not re.fullmatch('[0-9a-f]{64}', sha):
        raise CaptureError('ARCHIVE_REFERENCE_INVALID')
    data = read_record(root / 'archive' / (sha + '.' + suffix), limit, 'ARCHIVE_MISSING_OR_UNSAFE')
    if digest(data) != sha:
        raise CaptureError('ARCHIVE_HASH_MISMATCH')
    return data


def verify_receipt(root, path):
    """Recompute the entire receipt identity from its hash-verified evidence."""
    try:
        receipt = json.loads(read_record(path, 16000, 'RECEIPT_MISSING_OR_UNSAFE'))
        events = read_archive(root, receipt['events_sha256'], 'codex-events.jsonl', MAX_BYTES)
        final = read_archive(root, receipt['final_sha256'], 'codex-final.json', 16000)
        prompt = read_archive(root, receipt['prompt_sha256'], 'codex-prompt.txt', 32000).decode('utf-8')
        value, session, line, item, diagnostics = completed_report(events, final, prompt, 0)
        privacy = receipt['source_privacy']
        if privacy not in ('synthetic', 'personal'):
            raise CaptureError('RECEIPT_MISMATCH')
        expected = report_receipt(value, session, line, item, diagnostics, events, final, prompt, privacy)
        if value['items']:
            status = receipt['status']
            if status not in ('STAGED', 'CONTENT_REUSED'):
                raise CaptureError('RECEIPT_MISMATCH')
            candidate_sha = receipt['candidate_sha256']
            if not isinstance(candidate_sha, str) or not re.fullmatch('[0-9a-f]{64}', candidate_sha):
                raise CaptureError('RECEIPT_MISMATCH')
            expected.update(status=status, proposals=1 if status == 'STAGED' else 0,
                            candidate_sha256=candidate_sha)
        else:
            expected['status'] = 'NO_MEANINGFUL_OUTCOMES'
        if (path != receipt_path(root, session, digest(events))
                or json.dumps(receipt, sort_keys=True) != json.dumps(expected, sort_keys=True)):
            raise CaptureError('RECEIPT_MISMATCH')
        return receipt, value
    except CaptureError:
        raise
    except (ValueError, KeyError, TypeError, UnicodeError):
        raise CaptureError('RECEIPT_MISMATCH') from None


def make_candidate(value, source, privacy, timestamp):
    content_sha = content_digest(value, privacy)
    basis = {'user-stated': 'user-stated', 'assistant-reported': 'summary-derived', 'inferred': 'inferred'}
    return {'schema_version': '1.0', 'id': 'codex-capture-' + content_sha[:32],
            'title': 'Codex session outcome proposal', 'kind': 'session',
            'review_state': 'candidate', 'created': timestamp, 'updated': timestamp, 'as_of': None,
            'privacy': 'personal', 'scopes': ['engineering'], 'sources': [source],
            'supersedes': [], 'external_processing': False,
            'capture_content_sha256': content_sha, 'capture_report': value,
            'capture_source_privacy': privacy,
            'body': ('The runner observed a completed CLI turn and exit code 0. This is not proof '
                     'that reported project work succeeded. Dates above describe capture, not an '
                     'unknown event date. Assistant reports and interpretations require review. '
                     + PROVENANCE_TEXT),
            'claims': [{'text': item['kind'] + ': ' + item['text'], 'evidence': basis[item['basis']],
                        'locator': source + '/report/items/' + str(i)} for i, item in enumerate(value['items'])]}


def verify_cached_candidate(root, expected):
    """Verify original evidence and every derived field; never heal missing notes."""
    try:
        data = read_record(root / expected['candidate'], 64000, 'CANDIDATE_MISSING_OR_UNSAFE')
        candidate = json.loads(data)
        source = candidate['sources'][0]
        match = re.fullmatch(r'archive/([0-9a-f]{64})\.codex-events\.jsonl#L[1-9][0-9]*/item/[A-Za-z0-9_-]+', source)
        if not match:
            raise CaptureError('CANDIDATE_SOURCE_INVALID')
        events = read_archive(root, match[1], 'codex-events.jsonl', MAX_BYTES)
        sessions = [event['thread_id'] for event in map(json.loads, events.splitlines())
                    if event.get('type') == 'thread.started']
        if len(sessions) != 1:
            raise CaptureError('CANDIDATE_SOURCE_INVALID')
        original, report = verify_receipt(root, receipt_path(root, safe_id(sessions[0]), match[1]))
        if (original['status'] != 'STAGED' or original['source'] != source
                or any(original[key] != expected[key] for key in
                       ('content_sha256', 'candidate', 'proposal', 'source_privacy'))):
            raise CaptureError('CANDIDATE_MISMATCH')
        timestamp = candidate['created']
        if datetime.fromisoformat(timestamp).utcoffset() != timezone.utc.utcoffset(None):
            raise CaptureError('CANDIDATE_MISMATCH')
        reconstructed = make_candidate(report, source, original['source_privacy'], timestamp)
        # Preserve previously pinned proposals without rewriting historical evidence.
        # Only the exact old boilerplate is compatible; every other field, source,
        # candidate hash and Markdown byte must still match the original receipt.
        legacy_body = reconstructed['body'].removesuffix(PROVENANCE_TEXT) + LEGACY_PROVENANCE_TEXT
        if candidate.get('body') == legacy_body:
            reconstructed['body'] = legacy_body
        if (digest(data) != original['candidate_sha256']
                or ('candidate_sha256' in expected and digest(data) != expected['candidate_sha256'])
                or json.dumps(candidate, sort_keys=True) != json.dumps(reconstructed, sort_keys=True)):
            raise CaptureError('CANDIDATE_MISMATCH')
        validate_candidate(candidate)
        # The shared renderer would recreate a deleted note. Cached state must
        # instead remain complete before its exact-byte verification can run.
        read_record(root / expected['proposal'], 128000, 'CACHED_PROPOSAL_MISSING_OR_UNSAFE')
        render(reconstructed, root, expected['proposal'].removeprefix('test-vault/'))
        return digest(data)
    except CaptureError:
        raise
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        raise CaptureError('CANDIDATE_MISMATCH') from None


def stage_report(config, root, events_raw, final_raw, prompt, exit_code):
    """Caller holds the single-writer capture lock. All output paths are fixed here."""
    root = private_root(root)
    checked_path(root, directory=True)
    if root != Path(config['workspace']).resolve():
        raise CaptureError('WORKSPACE_MISMATCH')
    value, session, line, item, diagnostics = completed_report(events_raw, final_raw, prompt, exit_code)
    if not config['enabled']:
        return {'status': 'DISABLED', 'proposals': 0}
    expected = report_receipt(value, session, line, item, diagnostics, events_raw, final_raw,
                              prompt, config['source_privacy'])
    path = receipt_path(root, session, expected['events_sha256'])
    if path.exists():
        receipt, _ = verify_receipt(root, path)
        if any(receipt.get(key) != field for key, field in expected.items() if key != 'proposals'):
            raise CaptureError('RECEIPT_MISMATCH')
        if value['items']:
            verify_cached_candidate(root, receipt)
        return {**receipt, 'status': 'DUPLICATE_SOURCE', 'proposals': 0}
    reused = bool(value['items']) and (root / expected['candidate']).exists()
    if value['items'] and not reused and (root / expected['proposal']).exists():
        raise CaptureError('CANDIDATE_MISSING_OR_UNSAFE')
    if reused:
        # Check the original citation before writing any new session evidence.
        candidate_sha = verify_cached_candidate(root, expected)
    for data, suffix in ((events_raw, 'codex-events.jsonl'), (final_raw, 'codex-final.json'),
                         (prompt.encode('utf-8'), 'codex-prompt.txt')):
        write_new(root / 'archive' / (digest(data) + '.' + suffix), data)
        read_archive(root, digest(data), suffix, MAX_BYTES)
    if not value['items']:
        expected['status'] = 'NO_MEANINGFUL_OUTCOMES'
    else:
        if not reused:
            candidate = make_candidate(value, expected['source'], config['source_privacy'],
                                       datetime.now(timezone.utc).isoformat())
            validate_candidate(candidate)
            data = json_bytes(candidate)
            write_new(root / expected['candidate'], data)
            render(candidate, root, expected['proposal'].removeprefix('test-vault/'))
            candidate_sha = digest(data)
        expected.update(status='CONTENT_REUSED' if reused else 'STAGED',
                        proposals=0 if reused else 1, candidate_sha256=candidate_sha)
    write_new(path, json_bytes(expected))
    return expected
