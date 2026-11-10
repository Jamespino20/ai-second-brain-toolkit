"""Explicit offline export intake into private staging; no model or publication."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

from migrate import digest, intake, json_bytes, normalize, private_root, write_new
from selected_memory import checked_path

MAX_JSON_BYTES = 256 * 1024 * 1024
MAX_TOTAL_JSON_BYTES = 512 * 1024 * 1024
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024


def file_hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def selected_json(archive, prefix='', nested=False):
    members = archive.infolist()
    if len(members) > 20000:
        raise ValueError('ARCHIVE_MEMBER_LIMIT')
    seen = set()
    nested_count = nested_bytes = 0
    for member in members:
        name = member.filename
        is_json = re.fullmatch(r'conversations(?:[-_]?\d+)?\.json', PurePosixPath(name).name, re.I)
        is_zip = name.lower().endswith('.zip') and not nested
        if not is_json and not is_zip:
            continue
        if (name.startswith('/') or '\\' in name or ':' in name
                or any(part in ('', '.', '..') for part in name.split('/'))
                or name.casefold() in seen or member.flag_bits & 1):
            raise ValueError('UNSAFE_OR_DUPLICATE_MEMBER')
        seen.add(name.casefold())
        limit = MAX_JSON_BYTES if is_json else MAX_ARCHIVE_BYTES
        if is_zip:
            nested_count += 1
            nested_bytes += member.file_size
            if nested_count > 16 or nested_bytes > MAX_ARCHIVE_BYTES:
                raise ValueError('NESTED_ARCHIVE_LIMIT')
        if member.file_size > limit:
            raise ValueError('ARCHIVE_MEMBER_TOO_LARGE')
        with archive.open(member) as stream:
            locator = prefix + name
            if is_zip:
                with zipfile.ZipFile(stream) as child:
                    yield from selected_json(child, locator + '!/', nested=True)
            else:
                raw = stream.read(MAX_JSON_BYTES + 1)
                if len(raw) > MAX_JSON_BYTES:
                    raise ValueError('JSON_TOO_LARGE')
                yield locator, raw


def import_archive(source, workspace):
    root = private_root(workspace)
    source = checked_path(Path(source).absolute())
    if source.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError('ARCHIVE_TOO_LARGE')
    archive_sha = file_hash(source)
    sources, identities = [], set()
    total = conversations = messages = attachments = 0
    with zipfile.ZipFile(source) as archive:
        for locator, raw in selected_json(archive):
            total += len(raw)
            if total > MAX_TOTAL_JSON_BYTES:
                raise ValueError('TOTAL_JSON_LIMIT')
            records = list(normalize(json.loads(raw)))
            sha = digest(raw)
            source_file = root / 'archive' / (sha + '.json')
            write_new(source_file, raw)
            intake(source_file, root)
            for record in records:
                target = root / 'normalized' / record['id'] / (sha + '.v1_2.json')
                actual = checked_path(target).read_bytes()
                stored = json.loads(actual)
                expected = {**record, 'capture_date': stored['capture_date'],
                            'normalization_version': '1.2', 'source_sha256': sha,
                            'privacy': 'personal', 'external_processing': False}
                if actual != json_bytes(expected):
                    raise ValueError('NORMALIZED_CACHE_MISMATCH')
                identities.add(record['id'])
                messages += len(record['messages'])
                attachments += len(record['attachments'])
            conversations += len(records)
            sources.append({'member': locator, 'sha256': sha, 'size': len(raw), 'conversations': len(records)})
    if not sources or not conversations:
        raise ValueError('NO_CONVERSATIONS')
    if file_hash(source) != archive_sha:
        raise ValueError('SOURCE_CHANGED_DURING_INTAKE')
    receipt = {'schema': 'export-intake-v1', 'archive_sha256': archive_sha,
               'normalization_version': '1.2', 'sources': sources,
               'conversations': conversations, 'unique_conversations': len(identities),
               'messages': messages, 'attachments': attachments, 'published': 0}
    write_new(root / 'staging/export-intake' / archive_sha / 'receipt.json', json_bytes(receipt))
    return {key: value for key, value in receipt.items() if key != 'sources'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--root', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(import_archive(args.source, args.root)))
        return 0
    except (ValueError, OSError, KeyError, TypeError, AttributeError, zipfile.BadZipFile, RuntimeError):
        print(json.dumps({'status': 'REFUSED', 'error_code': 'EXPORT_INTAKE_REFUSED', 'published': 0}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
