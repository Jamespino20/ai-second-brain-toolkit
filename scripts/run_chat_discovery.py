"""Reviewed-profile launcher for discovery-only metadata; not an activation."""
import socket
import sys
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time
import datetime
import threading
import uuid
import types
import ctypes
from ctypes import wintypes


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate key')
        result[key] = value
    return result


def _path(value, *, directory=False, absent=False):
    if not isinstance(value, str) or not value:
        raise ValueError('invalid path')
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts or any(p.lower() == '.git' for p in path.parts):
        raise ValueError('invalid path')
    for part in reversed((path if not absent else path.parent, *path.parents)):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('redirected path')
        if stat.S_ISDIR(info.st_mode) and (part / '.git').exists():
            raise ValueError('git ancestor')
    if absent:
        if path.exists():
            raise ValueError('record exists')
    else:
        info = path.lstat()
        if directory:
            if not stat.S_ISDIR(info.st_mode):
                raise ValueError('not a directory')
        elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError('not a private regular file')
    return path


def _digest(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _pin(path, digest):
    if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest) or _digest(path) != digest:
        raise ValueError('pin mismatch')


def load_profile(filename, digest):
    manifest = _path(filename)
    with manifest.open('rb') as stream:
        raw = stream.read(65537)
    if len(raw) > 65536 or not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest) or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('manifest refused')
    profile = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs)
    keys = {'schema', 'state', 'scope', 'owner_reference', 'additional_spend_usd', 'lifetime_seconds', 'startup_timeout_seconds', 'recipients', 'private_root', 'runtime_dir', 'runtime_files', 'helper', 'config', 'temp_dir', 'intent_path', 'receipt_path'}
    if not isinstance(profile, dict) or set(profile) != keys or profile['schema'] != 'brain-chat-discovery-launch-v1' or profile['state'] != 'approved' or profile['scope'] != 'metadata-discovery-only':
        raise ValueError('profile refused')
    if not isinstance(profile['owner_reference'], str) or not profile['owner_reference'].strip() or type(profile['additional_spend_usd']) is not int or profile['additional_spend_usd'] != 0:
        raise ValueError('profile refused')
    if type(profile['lifetime_seconds']) is not int or not 1 <= profile['lifetime_seconds'] <= 900 or type(profile['startup_timeout_seconds']) is not int or not 1 <= profile['startup_timeout_seconds'] <= 60 or profile['recipients'] != ['Cloudflare', 'OpenAI', 'Sentry']:
        raise ValueError('profile refused')
    root = _path(profile['private_root'], directory=True)
    runtime = _path(profile['runtime_dir'], directory=True)
    temp = _path(profile['temp_dir'], directory=True)
    intent = _path(profile['intent_path'], absent=True)
    receipt = _path(profile['receipt_path'], absent=True)
    hold = _path(str(intent) + '.hold.json', absent=True)
    if len({intent, receipt, hold}) != 3:
        raise ValueError('record collision')
    if not isinstance(profile['runtime_files'], dict) or set(profile['runtime_files']) != {'run_chat_discovery.py', 'chat_recall_discovery.py'}:
        raise ValueError('invalid source pins')
    sources = [_path(str(runtime / name)) for name in profile['runtime_files']]
    for name in ('helper', 'config'):
        record = profile[name]
        if not isinstance(record, dict) or set(record) != {'path', 'sha256'}:
            raise ValueError('invalid pin')
        _path(record['path'])
    config = Path(profile['config']['path'])
    paths = [manifest, runtime, temp, intent, receipt, hold, *sources, Path(profile['helper']['path']), config]
    if any(not p.is_relative_to(root) or p == root for p in paths):
        raise ValueError('outside private root')
    for source in sources:
        _pin(source, profile['runtime_files'][source.name])
    if Path(__file__).resolve() != (runtime / 'run_chat_discovery.py').resolve():
        raise ValueError('wrong launcher')
    for name in ('helper', 'config'):
        record = profile[name]
        path = Path(record['path'])
        _pin(path, record['sha256'])
    with config.open('rb') as stream:
        if stream.read(4) != b'{}\n':
            raise ValueError('config refused')
    return profile


class OutputGuard:
    _url = re.compile(rb'https://[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.trycloudflare\.com')
    TOTAL_LIMIT = 1
    LINE_LIMIT = 2
    INVALID_CANDIDATE = 4
    CANDIDATE_BOUNDARY = 8
    CHANGED_ORIGIN = 16

    def __init__(self):
        self.origin = None
        self.failed = False
        self.failure_mask = 0
        self.line = bytearray()
        self.total = 0
        self.started = False

    def feed(self, data):
        for byte in data:
            if not self.started:
                self.total += 1
                if self.total > 65536:
                    self.failed = True
                    self.failure_mask |= self.TOTAL_LIMIT
            if byte == 10:
                line = bytes(self.line)
                self.line.clear()
                for match in re.finditer(rb'[a-z][a-z0-9+.-]*://[^\s|"\']+', line, re.IGNORECASE):
                    candidate = match.group()
                    authority = re.split(rb'[/#?]', candidate.split(b'://', 1)[1], maxsplit=1)[0]
                    if b'trycloudflare' in authority.lower() and not self._url.fullmatch(candidate):
                        self.failed = True
                        self.failure_mask |= self.INVALID_CANDIDATE
                    if not self._url.fullmatch(candidate):
                        continue
                    before = line[match.start()-1:match.start()] if match.start() else b' '
                    after = line[match.end():match.end()+1] or b' '
                    if before not in b' \t|"\'' or after not in b' \t|"\'\r':
                        self.failed = True
                        self.failure_mask |= self.CANDIDATE_BOUNDARY
                        continue
                    found = candidate.decode('ascii')
                    if self.origin is not None and self.origin != found:
                        self.failed = True
                        self.failure_mask |= self.CHANGED_ORIGIN
                    self.origin = found
            elif len(self.line) < 4096:
                self.line.append(byte)
            else:
                self.failed = True
                self.failure_mask |= self.LINE_LIMIT


def cleanup(child, server, thread, duplicate, root, on_hold=None):
    """Retain the root listener until the owned process and server are gone."""
    if server is not None:
        server.should_exit = True
    if child is not None:
        try:
            child.terminate()
        except (Exception, KeyboardInterrupt, SystemExit):
            pass
        try:
            child.wait(timeout=3)
        except (Exception, KeyboardInterrupt, SystemExit):
            try:
                child.kill()
            except (Exception, KeyboardInterrupt, SystemExit):
                pass
    reported = False
    while child is not None:
        try:
            child.wait(timeout=1)
            break
        except (Exception, KeyboardInterrupt, SystemExit):
            if not reported:
                if on_hold is not None:
                    on_hold('child')
                print('cleanup blocked; holding listener for owned child', file=sys.stderr)
                reported = True
    if thread is not None:
        while True:
            try:
                thread.join(timeout=1)
                if not thread.is_alive():
                    break
                if not reported:
                    if on_hold is not None:
                        on_hold('server')
                    print('cleanup blocked; holding listener for server', file=sys.stderr)
                    reported = True
            except (Exception, KeyboardInterrupt, SystemExit):
                continue
    if duplicate is not None:
        duplicate.close()
    if root is not None:
        root.close()


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _creation_filetime(child):
    """Read creation FILETIME from the exact owned process handle."""
    if sys.platform != 'win32':
        raise ValueError('unsupported platform')
    api = ctypes.WinDLL('kernel32', use_last_error=True).GetProcessTimes
    api.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    api.restype = wintypes.BOOL
    creation, exit_time, kernel, user = (wintypes.FILETIME() for _ in range(4))
    if not api(int(child._handle), ctypes.byref(creation), ctypes.byref(exit_time), ctypes.byref(kernel), ctypes.byref(user)):
        raise ctypes.WinError(ctypes.get_last_error())
    return (creation.dwHighDateTime << 32) | creation.dwLowDateTime


def _record(path, data):
    with open(path, 'xb') as stream:
        stream.write(json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8'))


def run_profile(profile, manifest_digest):
    root = duplicate = child = server = thread = None
    guard = OutputGuard()
    origin = None
    pid = None
    port = None
    creation_filetime = None
    spawn_attempted_at = None
    started = _now()
    run_id = uuid.uuid4().hex
    status = 'error'
    intent = {'schema': 'brain-chat-discovery-intent-v1', 'run_id': run_id,
              'manifest_sha256': manifest_digest, 'runtime_files': profile['runtime_files'],
              'helper_sha256': profile['helper']['sha256'], 'config_sha256': profile['config']['sha256'],
              'started_at': started}
    _record(profile['intent_path'], intent)
    try:
        root = open_exclusive_listener()
        port = root.getsockname()[1]
        environment = {key: os.environ[key] for key in ('SystemRoot', 'WINDIR') if key in os.environ}
        environment.update({'TEMP': profile['temp_dir'], 'TMP': profile['temp_dir']})
        argv = [profile['helper']['path'], 'tunnel', '--no-autoupdate', '--no-prechecks',
                '--config', profile['config']['path'], '--metrics', '127.0.0.1:0',
                '--management-diagnostics=false', '--loglevel', 'info', '--protocol', 'http2',
                '--url', f'http://127.0.0.1:{port}']
        spawn_attempted_at = _now()
        child = subprocess.Popen(argv, shell=False, env=environment, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        pid = child.pid
        creation_filetime = _creation_filetime(child)
        lock = threading.Lock()
        def drain():
            try:
                while True:
                    chunk = child.stdout.read(1)
                    if not chunk:
                        return
                    with lock:
                        guard.feed(chunk)
            except Exception:
                with lock:
                    guard.failed = True
        pump = threading.Thread(target=drain, daemon=True)
        pump.start()
        deadline = time.monotonic() + profile['startup_timeout_seconds']
        end = time.monotonic() + profile['lifetime_seconds']
        while time.monotonic() < deadline and time.monotonic() < end:
            with lock:
                failed, origin = guard.failed, guard.origin
            if failed or child.poll() is not None:
                raise ValueError('startup refused')
            if origin:
                break
            time.sleep(0.02)
        if not origin:
            raise ValueError('startup timeout')
        with lock:
            guard.started = True
        path = Path(profile['runtime_dir']) / 'chat_recall_discovery.py'
        _pin(path, profile['runtime_files']['chat_recall_discovery.py'])
        source = path.read_bytes()
        if hashlib.sha256(source).hexdigest() != profile['runtime_files']['chat_recall_discovery.py']:
            raise ValueError('source changed')
        module = types.ModuleType('_reviewed_discovery')
        exec(compile(source, str(path), 'exec'), module.__dict__)
        app = module.create_app(origin, port)
        import uvicorn
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port,
                                access_log=False, proxy_headers=False, log_config=None, log_level='critical'))
        duplicate = root.dup()
        def serve():
            try:
                server.run(sockets=[duplicate])
            except BaseException:
                pass
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        ready = False
        while time.monotonic() < end:
            with lock:
                if guard.failed or guard.origin != origin or child.poll() is not None or not thread.is_alive():
                    raise ValueError('session stopped')
                if server.started and not ready:
                    message = json.dumps({'status': 'metadata-only', 'origin': origin,
                                          'mcp_url': origin + '/mcp'}, separators=(',', ':'))
                    if len(message.encode('utf-8')) > 511:
                        raise ValueError('ready output too large')
                    print(message, flush=True)
                    ready = True
            time.sleep(0.02)
        if not ready:
            raise ValueError('ready was not emitted')
        status = 'lifetime_elapsed'
    except (Exception, KeyboardInterrupt, SystemExit) as exc:
        import traceback; traceback.print_exc()
        status = 'error'
    finally:
        def report_hold(reason):
            record = {'schema': 'brain-chat-discovery-hold-v1', 'run_id': run_id,
                      'reason': reason, 'port': port if root is not None else None,
                      'child_pid': pid, 'child_creation_filetime': creation_filetime,
                      'server_thread_id': thread.ident if thread is not None else None,
                      'server_native_id': thread.native_id if thread is not None else None}
            try:
                if len(json.dumps(record).encode('utf-8')) > 2048:
                    raise ValueError('hold record too large')
                _record(profile['intent_path'] + '.hold.json', record)
            except (Exception, KeyboardInterrupt, SystemExit):
                print('private hold report unavailable', file=sys.stderr)
        cleanup(child, server, thread, duplicate, root, report_hold)
    receipt = {'schema': 'brain-chat-discovery-receipt-v1', 'run_id': run_id,
               'origin': origin, 'port': port if root is not None else None, 'child_pid': pid,
               'spawn_attempted_at': spawn_attempted_at, 'child_creation_filetime': creation_filetime,
               'started_at': started, 'ended_at': _now(),
               'status': status, 'cleanup': 'complete'}
    _record(profile['receipt_path'], receipt)
    return 0 if status == 'lifetime_elapsed' else 1


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) != 2:
            raise ValueError('arguments refused')
        profile = load_profile(*args)
        return run_profile(profile, args[1])
    except (Exception, KeyboardInterrupt):
        return 1
    return 1


def open_exclusive_listener():
    """Hold an exclusive Windows loopback listener until its owner closes it."""
    if sys.platform != 'win32' or not hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
        raise ValueError('unsupported platform')
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.set_inheritable(False)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        listener.bind(('127.0.0.1', 0))
        listener.listen(socket.SOMAXCONN)
        return listener
    except BaseException:
        listener.close()
        raise


if __name__ == '__main__':
    raise SystemExit(main())
