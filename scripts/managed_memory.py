"""Scoped managed Markdown recall. No writes, network, discovery or grant creation."""
import json
from functools import wraps
from pathlib import Path, PurePosixPath
import re
import threading

from migrate import private_root
from selected_memory import checked_path, citation, digest, is_safe_source_reference

_HIGH_WATER = {}
_LOCK = threading.Lock()
_CLIENTS = {'codex-openai', 'chatgpt-openai', 'claude-anthropic', 'antigravity-google-anthropic'}


def _input_errors(function):
    @wraps(function)
    def checked(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except (OSError, KeyError, TypeError, AttributeError, OverflowError) as error:
            raise ValueError('Managed recall configuration or evidence invalid') from error
    return checked


def _require(condition):
    if not condition:
        raise ValueError('Managed recall configuration or evidence invalid')


def _string(value):
    return isinstance(value, str) and bool(value.strip())


def _hash(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _identifier(value):
    return isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}', value) is not None


def _bytes(path, limit):
    path = checked_path(path)
    _require(path.stat().st_size <= limit)
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    _require(len(data) <= limit)
    return data


def _json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result)
            result[key] = value
        return result
    try:
        value = json.loads(data, object_pairs_hook=unique)
        _require(isinstance(value, dict))
        return value
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError('Managed recall JSON invalid') from error


def _approved(value, purpose=False):
    _require(isinstance(value, dict) and value.get('state') == 'approved'
             and _string(value.get('reference')))
    if purpose:
        _require(_string(value.get('purpose')))


_DEVICE_PATTERN = re.compile(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]|CONIN\$|CONOUT\$|CLOCK\$)(\..*)?$', re.I)


def _relative(value, markdown=True):
    _require(_string(value))
    path = PurePosixPath(value)
    _require(not path.is_absolute() and str(path) == value
             and not any(c in value for c in '\\:*?"<>|\x00')
             and not any(ord(c) < 32 for c in value)
             and all(part.casefold() not in ('.', '..', '.git', '.obsidian')
                     and not part.endswith((' ', '.'))
                     and _DEVICE_PATTERN.fullmatch(part.strip()) is None for part in path.parts))
    if markdown:
        _require(path.suffix == '.md')
    return path


def _load(grant_path, grant_sha256, client):
    _require(isinstance(client, str) and client in _CLIENTS and _hash(grant_sha256))
    grant_bytes = _bytes(grant_path, 65536)
    _require(digest(grant_bytes) == grant_sha256)
    grant = _json(grant_bytes)
    _require(grant.get('schema') == 'brain-managed-read-grant-v1' and grant.get('client') == client)
    _approved(grant.get('owner_authorization'), purpose=True)
    kind = grant.get('source_kind')
    _require(kind in ('synthetic', 'canonical'))
    if kind == 'canonical':
        _require(grant['owner_authorization'].get('personal_content_external_model_approved') is True)
    root = checked_path(grant['root'], directory=True)
    if kind == 'synthetic':
        _require('test-vault' in [part.casefold() for part in root.parts])
    private = checked_path(grant['private_root'], directory=True)
    private_root(private)
    policy_bytes = _bytes(grant['policy_path'], 131072)
    _require(_hash(grant.get('policy_sha256')) and digest(policy_bytes) == grant['policy_sha256'])
    policy = _json(policy_bytes)
    _require(policy.get('schema') == 'brain-publication-policy-v1' and policy.get('enabled') is True)
    _approved(policy.get('owner_authorization'))
    _require(_identifier(policy.get('policy_id')) and Path(policy['vault_root']) == root)
    limits = policy.get('limits', {})
    note_limit, byte_limit = limits.get('max_managed_notes'), limits.get('max_note_bytes')
    _require(type(note_limit) is int and 1 <= note_limit <= 256
             and type(byte_limit) is int and 1 <= byte_limit <= 128000)
    directory = private / 'publications' / policy['policy_id'] / 'managed'
    pointer_path = directory / 'latest.json'
    _require(Path(grant['manifest_pointer']) == pointer_path)
    pointer_bytes = _bytes(pointer_path, 4096)
    pointer = _json(pointer_bytes)
    rel = _relative(pointer['manifest'], markdown=False)
    _require(rel.suffix == '.json' and str(rel) != 'latest.json' and _hash(pointer.get('sha256')))
    manifest_path = directory.joinpath(*rel.parts)
    manifest_bytes = _bytes(manifest_path, 1048576)
    _require(digest(manifest_bytes) == pointer['sha256'])
    manifest = _json(manifest_bytes)
    _require(manifest.get('schema') == 'brain-managed-manifest-v1'
             and manifest.get('policy_id') == policy['policy_id']
             and manifest.get('policy_sha256') == grant['policy_sha256']
             and type(manifest.get('generation')) is int and manifest['generation'] >= 1
             and _string(manifest.get('transaction_id')))
    prefixes, ids = grant.get('prefixes'), grant.get('note_ids')
    _require(isinstance(prefixes, list) and isinstance(ids, list) and (prefixes or ids)
             and len(prefixes) <= 256 and len(ids) <= 256)
    for prefix in prefixes:
        _require(isinstance(prefix, str) and prefix.endswith('/'))
        _relative(prefix + 'scope.md')
    _require(all(_identifier(value) for value in ids))
    notes = manifest.get('notes')
    _require(isinstance(notes, list) and len(notes) <= note_limit)
    seen_ids, seen_paths, selected = set(), set(), []
    for note in notes:
        _require(isinstance(note, dict) and _identifier(note.get('id')))
        relative = note['path']
        rel = _relative(relative)
        _require(note['id'] not in seen_ids and relative.casefold() not in seen_paths
                 and _hash(note.get('sha256')) and type(note.get('size')) is int
                 and 0 <= note['size'] <= byte_limit
                 and note.get('privacy') in ('personal', 'synthetic')
                 and note.get('external_processing') is False
                 and isinstance(note.get('source_references'), list)
                 and len(note['source_references']) <= 8
                 and all(_string(value) and len(value) <= 512 and is_safe_source_reference(value) for value in note['source_references'])
                 and sum(len(value) for value in note['source_references']) <= 2048)
        seen_ids.add(note['id'])
        seen_paths.add(relative.casefold())
        if note['id'] not in ids and not any(relative.startswith(prefix) for prefix in prefixes):
            continue
        path = root.joinpath(*rel.parts)
        data = _bytes(path, byte_limit)
        _require(len(data) == note['size'] and digest(data) == note['sha256'])
        text = data.decode('utf-8')
        if kind == 'synthetic':
            front = re.match(r'\A---\n(.*?)\n---(?:\n|$)', text, re.S)
            _require(note['privacy'] == 'synthetic' and front is not None
                     and re.findall(r'^privacy:\s*(.*?)\s*$', front[1], re.M) == ['"synthetic"'])
        selected.append((note, path, text.splitlines()))
    state = (grant_path, grant_sha256, grant_bytes, policy_bytes, pointer_path,
             pointer_bytes, manifest_path, pointer['sha256'], manifest['generation'])
    return grant, selected, state


def _finish(grant, state, result):
    grant_path, grant_hash, grant_bytes, policy_bytes, pointer, pointer_bytes, manifest, manifest_hash, generation = state
    _require(_bytes(grant_path, 65536) == grant_bytes
             and _bytes(grant['policy_path'], 131072) == policy_bytes
             and _bytes(pointer, 4096) == pointer_bytes
             and digest(_bytes(manifest, 1048576)) == manifest_hash)
    # The pinned private pointer is trusted on first use, not persistent rollback protection.
    key = (str(Path(grant_path)), grant_hash, grant['policy_sha256'])
    identity = (pointer_bytes, manifest_hash)
    with _LOCK:
        previous = _HIGH_WATER.get(key)
        _require(previous is None or generation > previous[0]
                 or (generation == previous[0] and identity == previous[1]))
        _HIGH_WATER[key] = (generation, identity)
    return {**result, 'mode': 'managed-read-only-markdown', 'manifest_generation': generation}


@_input_errors
def search_managed(grant_path, grant_sha256, client, query, limit=4):
    """Search enrolled notes within the pinned client's scope, returning cited excerpts."""
    _require(isinstance(query, str) and 1 <= len(query) <= 300 and bool(query.strip())
             and type(limit) is int and 1 <= limit <= 4)
    terms = set(re.findall(r'[\w-]+', query.casefold()))
    _require(bool(terms))
    grant, notes, state = _load(grant_path, grant_sha256, client)
    matches = []
    for note, path, lines in notes:
        heading = next((i for i, line in enumerate(lines) if line.startswith('# ')), len(lines))
        scored = [(sum(term in line.casefold() for term in terms), i)
                  for i, line in enumerate(lines) if i >= heading and line.strip()]
        if not scored:
            continue
        score, index = max(scored, key=lambda item: (item[0], -item[1]))
        if score:
            _require(len(lines[index]) <= 2000)
            matches.append({**citation(grant, note, path), 'line': index + 1,
                            'excerpt': lines[index], 'score': score})
    matches.sort(key=lambda item: (-item['score'], item['note_id']))
    return _finish(grant, state, {'query': query, 'selected_note_count': len(notes), 'matches': matches[:limit]})


@_input_errors
def read_managed(grant_path, grant_sha256, client, note_id, start_line=1, line_count=20):
    """Read bounded numbered lines by enrolled ID; tool callers cannot choose paths."""
    _require(_identifier(note_id) and type(start_line) is int and start_line >= 1
             and type(line_count) is int and 1 <= line_count <= 40)
    grant, notes, state = _load(grant_path, grant_sha256, client)
    for note, path, lines in notes:
        if note['id'] != note_id:
            continue
        _require(start_line <= len(lines))
        selected = lines[start_line - 1:start_line - 1 + line_count]
        _require(sum(len(line) for line in selected) <= 8000)
        result = {**citation(grant, note, path), 'start_line': start_line,
                  'end_line': start_line + len(selected) - 1,
                  'lines': [{'line': start_line + index, 'text': text} for index, text in enumerate(selected)]}
        return _finish(grant, state, result)
    raise ValueError('Managed note is outside the approved scope')
