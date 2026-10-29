"""Stage an explicit current-context summary locally. No model or transcript reader."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import sys
import uuid

from capture_outcomes import privacy_check
from migrate import digest, json_bytes, private_root, render, validate_candidate, write_new
from selected_memory import checked_path

ROLES = {'planner', 'implementer', 'reviewer', 'mixed', 'unknown'}
KINDS = {'decision', 'work', 'test', 'lesson', 'blocker', 'next-action', 'review'}
STATUSES = {'reported-completed', 'reported-passed', 'reported-failed', 'proposed', 'blocked', 'unknown'}
SUPPORT = {'visible-tool-output', 'visible-user-message', 'artifact', 'inference', 'unsupported'}


def require(value, code):
    if not value:
        raise ValueError(code)


def inspect_strings(value):
    if isinstance(value, str):
        privacy_check(value)
    elif isinstance(value, list):
        for child in value:
            inspect_strings(child)
    elif isinstance(value, dict):
        for key, child in value.items():
            privacy_check(key)
            inspect_strings(child)


def validate_packet(value):
    require(isinstance(value, dict) and set(value) == {'schema', 'role', 'coverage', 'items', 'artifacts'}, 'INVALID_PACKET')
    require(value['schema'] == 'brain-save-context-v1' and value['role'] in ROLES, 'INVALID_IDENTITY')
    require(value['coverage'] in {'visible-context', 'compacted-context'}, 'INVALID_COVERAGE')
    require(isinstance(value['items'], list) and len(value['items']) <= 8, 'INVALID_ITEMS')
    require(isinstance(value['artifacts'], list) and len(value['artifacts']) <= 8, 'INVALID_ARTIFACTS')
    for item in value['items']:
        require(isinstance(item, dict) and set(item) == {'kind', 'text', 'status', 'actor', 'support', 'references'}, 'INVALID_ITEM')
        require(item['kind'] in KINDS and item['status'] in STATUSES and item['support'] in SUPPORT, 'INVALID_CLASSIFICATION')
        require(item['actor'] in {'this-session', 'other-session', 'unknown'}, 'INVALID_ACTOR')
        require(isinstance(item['text'], str) and 1 <= len(item['text'].strip()) <= 1200, 'INVALID_TEXT')
        require(isinstance(item['references'], list) and 1 <= len(item['references']) <= 4
                and all(isinstance(x, str) and 1 <= len(x) <= 400 for x in item['references']), 'SOURCE_REFERENCE_REQUIRED')
        if item['status'].startswith('reported-'):
            require(item['support'] in {'visible-tool-output', 'artifact', 'visible-user-message'}, 'RESULT_NEEDS_SUPPORT')
        if item['kind'] == 'next-action':
            require(item['status'] == 'proposed', 'NEXT_ACTION_NOT_COMPLETED')
        if item['kind'] == 'test':
            require(item['status'] in {'reported-passed', 'reported-failed', 'proposed', 'unknown'}, 'INVALID_TEST_STATUS')
        if value['role'] in {'planner', 'reviewer'} and item['kind'] == 'work' and item['actor'] == 'this-session':
            require(item['status'] != 'reported-completed', 'ROLE_CANNOT_CLAIM_IMPLEMENTER_WORK')
    inspect_strings(value)
    require(len({json.dumps(x, sort_keys=True) for x in value['items']}) == len(value['items']), 'DUPLICATE_ITEMS')
    return value


def artifact_records(project, paths):
    records = []
    for name in paths:
        require(isinstance(name, str), 'INVALID_ARTIFACT_PATH')
        path = PurePosixPath(name)
        require(not path.is_absolute() and str(path) == name and path.parts and path.suffix.lower() in {'.py', '.md', '.txt', '.json', '.toml', '.yaml', '.yml', '.js', '.ts', '.tsx', '.html', '.css'}, 'INVALID_ARTIFACT_PATH')
        require(not any(x in {'.', '..', '.git', '.codex', '.obsidian'} or x.lower().startswith('.env')
                        or x.lower() in {'auth.json', 'credentials.json', 'secrets.json'} for x in path.parts)
                and not any(x in name for x in '\\:*?"<>|'), 'ARTIFACT_NOT_AUTHORIZED')
        actual = checked_path(project.joinpath(*path.parts))
        require(actual.resolve().is_relative_to(project), 'ARTIFACT_OUTSIDE_PROJECT')
        require(actual.stat().st_size <= 2 * 1024 * 1024, 'ARTIFACT_TOO_LARGE')
        records.append({'path': name, 'sha256': digest(actual.read_bytes()),
                        'verification': 'file-bytes-only; not authorship, execution or semantic correctness'})
    require(len({x['path'].casefold() for x in records}) == len(records), 'DUPLICATE_ARTIFACT')
    return records


def make_note(envelope, sha, timestamp):
    packet = envelope['context_summary']
    source = 'archive/' + sha + '.brain-save-context.json'
    identity = envelope['identity']
    return {'schema_version': '1.0', 'id': 'brain-save-' + sha[:32],
            'title': 'Session memory proposal (' + packet['role'] + ')', 'kind': 'session',
            'review_state': 'candidate', 'created': timestamp, 'updated': timestamp,
            'as_of': None, 'privacy': 'personal', 'scopes': ['engineering'],
            'sources': [source], 'supersedes': [], 'external_processing': False,
            'interactive_capture': {'method': 'current-context-summary', 'project': identity['project_name'],
                                    'project_id': identity['project_id'], 'session_reference': identity['session_reference'],
                                    'session_reference_kind': identity['session_reference_kind'],
                                    'role': packet['role'], 'coverage': packet['coverage'],
                                    'full_transcript': False, 'artifacts': envelope['artifacts']},
            'body': 'Explicit current-session context summary, not a full transcript or CLI completion receipt. '
                    'Claims below are model-derived reports or interpretations, including descriptions of visible tool results; '
                    'the adapter does not independently attest conversation quotes or test execution. '
                    'Only the listed artifact hashes were checked locally, without proving authorship or implementation success.',
            'claims': [{'text': item['kind'] + ' [' + item['status'] + '; actor=' + item['actor'] +
                        '; support=' + item['support'] + ']: ' + item['text'] +
                        '\nSupporting references (session-supplied): ' + '; '.join(item['references']),
                        'evidence': 'inferred' if item['support'] == 'inference' else 'summary-derived',
                        'locator': source + '#/context_summary/items/' + str(i)}
                       for i, item in enumerate(packet['items'])]}


@contextmanager
def locked(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError('SAVE_BUSY_RETRY_ONCE') from None
    os.close(fd)
    try:
        yield
    finally:
        path.unlink()


def stage(root, project, value, environment=None):
    environment = os.environ if environment is None else environment
    root = private_root(root)
    checked_path(root, directory=True)
    project = checked_path(Path(project).absolute(), directory=True).resolve()
    project = next((parent for parent in (project, *project.parents) if (parent / '.git').exists()), project)
    require(not any(x.casefold().startswith('onedrive') or x in {'.codex', '.obsidian'} for x in project.parts), 'PROJECT_NOT_AUTHORIZED')
    packet = validate_packet(value)
    # These host variables are opportunistic identifiers, not a documented transcript API.
    session = environment.get('CODEX_THREAD_ID') or environment.get('CODEX_SESSION_ID')
    if session:
        require(isinstance(session, str) and 1 <= len(session) <= 120 and all(x.isalnum() or x in '_-' for x in session), 'INVALID_HOST_SESSION_ID')
        kind = 'host-environment-unattested'
    else:
        session, kind = 'unknown-' + str(uuid.uuid4()), 'invocation-id-not-a-session-id'
    privacy_check(session)
    privacy_check(project.name)
    identity = {'project_id': digest(str(project).casefold().encode()), 'project_name': project.name,
                'project_root': str(project), 'session_reference': session, 'session_reference_kind': kind}
    envelope = {'schema': 'brain-save-archive-v1', 'identity': identity, 'context_summary': packet,
                'artifacts': artifact_records(project, packet['artifacts'])}
    data = json_bytes(envelope)
    sha = digest(data)
    scope = identity['project_id'][:16] + '/' + digest((session + ':' + packet['role']).encode())[:24]
    folder = root / 'staging/brain-save' / scope / sha
    # Check existing namespace before creating a directory or lock.
    for part in (folder, *folder.parents):
        if part.exists():
            require(not part.is_symlink() and not part.is_junction(), 'REDIRECTED_OUTPUT')
    receipt_path = folder / 'receipt.json'
    archive = root / 'archive' / (sha + '.brain-save-context.json')
    candidate_path = folder / 'candidate.json'
    relative = 'logs/brain-save/' + scope + '/' + sha + '.md'
    markdown = root / 'test-vault' / relative
    with locked(folder / '.lock'):
        if receipt_path.exists():
            receipt = json.loads(checked_path(receipt_path).read_bytes())
            require(checked_path(archive).read_bytes() == data, 'CACHED_SOURCE_MISMATCH')
            expected = {'schema': 'brain-save-receipt-v1', 'source_sha256': sha,
                        'source': str(archive.relative_to(root)), 'scope': scope,
                        'status': 'STAGED' if packet['items'] else 'NO_MEANINGFUL_OUTCOMES',
                        'proposals': 1 if packet['items'] else 0}
            if packet['items']:
                old = json.loads(checked_path(candidate_path).read_bytes())
                timestamp = old['created']
                require(datetime.fromisoformat(timestamp).utcoffset() == timezone.utc.utcoffset(None), 'CACHED_TIMESTAMP_INVALID')
                reconstructed = make_note(envelope, sha, timestamp)
                require(checked_path(candidate_path).read_bytes() == json_bytes(reconstructed), 'CACHED_CANDIDATE_MISMATCH')
                checked_path(markdown)  # Never recreate a deleted proposal on replay.
                render(reconstructed, root, relative)
                expected.update(candidate=str(candidate_path.relative_to(root)), candidate_sha256=digest(candidate_path.read_bytes()),
                                proposal='test-vault/' + relative, proposal_sha256=digest(markdown.read_bytes()))
            require(receipt == expected, 'CACHED_RECEIPT_MISMATCH')
            return {**receipt, 'status': 'DUPLICATE_SOURCE', 'proposals': 0, 'private_root': str(root)}
        require(not candidate_path.exists() and not markdown.exists() and not archive.exists(), 'INCOMPLETE_PRIOR_SAVE')
        write_new(archive, data)
        receipt = {'schema': 'brain-save-receipt-v1', 'source_sha256': sha,
                   'source': str(archive.relative_to(root)), 'scope': scope,
                   'status': 'STAGED' if packet['items'] else 'NO_MEANINGFUL_OUTCOMES',
                   'proposals': 1 if packet['items'] else 0}
        if packet['items']:
            note = make_note(envelope, sha, datetime.now(timezone.utc).isoformat())
            validate_candidate(note)
            write_new(candidate_path, json_bytes(note))
            render(note, root, relative)
            receipt.update(candidate=str(candidate_path.relative_to(root)), candidate_sha256=digest(candidate_path.read_bytes()),
                           proposal='test-vault/' + relative, proposal_sha256=digest(markdown.read_bytes()))
        write_new(receipt_path, json_bytes(receipt))
        return {**receipt, 'private_root': str(root)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(32001)
        require(len(raw) <= 32000, 'INPUT_TOO_LARGE')
        text = raw.decode('utf-8-sig')
        privacy_check(text)
        value = json.loads(text)
        result = stage(args.root, Path.cwd(), value)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as error:
        # Never echo source content, paths from exceptions, or credential-bearing input.
        code = str(error) if isinstance(error, ValueError) and str(error).replace('_', '').isalnum() else 'SAVE_REFUSED_IO_OR_FORMAT'
        print(json.dumps({'status': 'REFUSED', 'error_code': code, 'proposals': 0}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
