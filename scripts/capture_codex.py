"""Explicit local Codex rollout snapshot; archives bytes, extracts dialogue only."""
import argparse
import json
from pathlib import Path
from migrate import digest, json_bytes, private_root, safe_id, write_new, intake


def capture(source, workspace, title):
    root = private_root(workspace)
    path = Path(source)
    raw = path.read_bytes()
    sha = digest(raw)
    events = [json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]
    meta = next(x for x in events if x.get('type') == 'session_meta')
    sid = safe_id(meta['payload']['id'])
    turns = []
    for n, event in enumerate(events, 1):
        item = event.get('payload', {})
        if event.get('type') != 'response_item' or item.get('type') != 'message' or item.get('role') not in ('user', 'assistant'):
            continue
        text = '\n'.join(x.get('text', '') for x in item.get('content', [])
                         if isinstance(x, dict) and x.get('type') in ('input_text', 'output_text', 'text'))
        if not text:
            continue
        mid = item.get('id') or 'rollout-line-' + str(n)
        turns.append({'id': 'rollout-line-' + str(n), 'startedAt': event.get('timestamp'),
            'items': [{'id': mid, 'type': 'userMessage' if item['role'] == 'user' else 'agentMessage',
                       'text': text, 'source_line': n}]})
    if path.read_bytes() != raw:
        raise ValueError('Rollout changed during capture; retry a stable snapshot')
    write_new(root / 'archive' / (sha + '.jsonl'), raw)
    record = {'thread': {'id': sid, 'kind': 'codex', 'title': title,
                        'createdAt': meta.get('timestamp'), 'updatedAt': events[-1].get('timestamp')},
        'turns': list(reversed(turns)), 'page': {'hasMore': False, 'nextCursor': None},
        'attachments': [], 'capture_method': 'local-rollout-dialogue-extraction',
        'source_rollout_sha256': sha, 'source_rollout_path': str(path),
        'coverage_notice': 'Stable local snapshot only; tool/reasoning/system items excluded; attachment bytes not interpreted'}
    output = root / 'raw' / ('thread-' + sid + '-rollout-' + sha + '.json')
    write_new(output, json_bytes(record))
    intake(output, root)
    return {'id': sid, 'messages': len(turns), 'source_sha256': sha, 'archive_bytes': len(raw),
            'published': 0, 'capture': str(output)}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source')
    p.add_argument('--workspace', required=True)
    p.add_argument('--title', required=True)
    a = p.parse_args()
    print(json.dumps(capture(a.source, a.workspace, a.title), indent=2))
