"""Capture fictional launcher readiness; process ownership and cleanup stay with caller.

This component neither starts a process nor runs the discovery checker. The caller
must hold and clean up its own launcher/helper and must not use a result as proof
of continuous availability or authorization. Same-account path races are not
prevented by these checks.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import stat
import time

class CaptureError(Exception):
    """A ready record was missing or refused; no raw output is included."""

_ORIGIN = re.compile(r'https://[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.trycloudflare\.com', re.ASCII)

def _check_directory(path):
    if not path.is_absolute() or not path.is_dir():
        raise ValueError('private directory required')
    for entry in (path, *path.parents):
        info = entry.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('redirected directory refused')

def _identity(file):
    s = os.fstat(file.fileno())
    return s.st_dev, s.st_ino

@contextmanager
def reserve(private_directory, name):
    """Create and hold an exclusive output file and a separate bounded reader.

    Caller must use writer only as subprocess stdout; stderr is separate. This
    routine leaves the create-only file in place, even on failure or collision.
    """
    root = Path(private_directory)
    _check_directory(root)
    if not isinstance(name, str) or not name or name in ('.', '..') or Path(name).name != name or any(c in name for c in '/\\:'):
        raise ValueError('invalid filename')
    path = root / name
    with path.open('x+b', buffering=0) as writer:
        with path.open('rb', buffering=0) as reader:
            if _identity(writer) != _identity(reader):
                raise CaptureError('capture identity refused')
            yield writer, reader

def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise CaptureError('duplicate key')
        result[key] = value
    return result

def _parse(data):
    if len(data) > 512 or not data.endswith(b'\n') or data.count(b'\n') != 1:
        raise CaptureError('ready record refused')
    try:
        obj = json.loads(data.decode('utf-8'), object_pairs_hook=_pairs,
                         parse_constant=lambda _: (_ for _ in ()).throw(CaptureError('constant refused')))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise CaptureError('ready record refused') from exc
    if not isinstance(obj, dict) or set(obj) != {'status','origin','mcp_url'} or obj['status'] != 'synthetic-only':
        raise CaptureError('ready record refused')
    origin = obj['origin']
    if not isinstance(origin, str) or not _ORIGIN.fullmatch(origin) or obj['mcp_url'] != origin + '/mcp':
        raise CaptureError('ready record refused')
    return obj

def wait_ready(reader, owned_process, timeout):
    """Return validated ready JSON before timeout while the owned process is alive.

    Reads bounded bytes from an already-open handle; on any error the caller is
    responsible for stopping its owned helper and waiting for launcher cleanup.
    """
    if isinstance(timeout, bool) or not isinstance(timeout, (float, int)) or not 0 < timeout <= 60:
        raise ValueError('invalid timeout')
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if owned_process.poll() is not None:
            raise CaptureError('launcher exited')
        reader.seek(0)
        data = reader.read(513)
        if len(data) > 512: raise CaptureError('ready record too large')
        if b'\n' in data:
            result = _parse(data)
            if owned_process.poll() is not None: raise CaptureError('launcher exited')
            return result
        time.sleep(min(.02, max(0, deadline - time.monotonic())))
    raise CaptureError('ready timeout')
