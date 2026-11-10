"""Source-only synthetic authenticated launcher; no canonical recall."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import threading
import time
import datetime
import uuid
import types
from urllib.parse import urlsplit


RUNTIME_NAMES = frozenset({'run_chat_synthetic.py', 'run_chat_discovery.py',
    'chat_recall_http.py', 'chat_recall_oauth.py', 'managed_memory.py',
    'selected_memory.py', 'publish_memory.py', 'migrate.py',
    'save_interactive_memory.py', 'capture_outcomes.py'})
DIAGNOSTIC_PHASES = frozenset({'session_start', 'listener', 'helper_spawn', 'process_identity',
    'output_startup', 'closure_validation', 'owner_code', 'app_factory', 'server_startup', 'serving'})
DIAGNOSTIC_REASONS = frozenset({'stage_error', 'startup_timeout', 'stream_read_error',
    'guard_rejected', 'child_exited', 'origin_changed', 'server_stopped', 'ready_not_emitted',
    'lifetime_elapsed', 'interrupted', 'system_exit', 'stop_requested'})
_shared = None


def open_exclusive_listener():
    if _shared is None:
        raise ValueError('preflight required')
    return _shared.open_exclusive_listener()


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('duplicate')
        value[key] = item
    return value


def _read_json(data):
    value = json.loads(data.decode('utf-8'), object_pairs_hook=_unique)
    if not isinstance(value, dict):
        raise ValueError('invalid JSON')
    return value


def _checked(value, *, root=None, directory=False, absent=False):
    if not isinstance(value, str) or not value:
        raise ValueError('path refused')
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts or any(part.casefold() == '.git' for part in path.parts):
        raise ValueError('path refused')
    if root is not None and (not path.is_relative_to(root) or path == root):
        raise ValueError('outside private root')
    for component in reversed((path.parent if absent else path, *(path.parents))):
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('redirect refused')
        if stat.S_ISDIR(info.st_mode) and os.path.lexists(component / '.git'):
            raise ValueError('git refused')
    if absent:
        if os.path.lexists(path):
            raise ValueError('collision')
    else:
        info = path.lstat()
        if directory:
            if not stat.S_ISDIR(info.st_mode): raise ValueError('directory refused')
        elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError('file refused')
    return path


def _bounded(path, limit):
    if path.stat().st_size > limit:
        raise ValueError('oversized')
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError('oversized')
    return data


def _pin(path, pin, limit):
    if not isinstance(pin, dict) or set(pin) != {'size', 'sha256'} or type(pin['size']) is not int or not 0 <= pin['size'] <= limit or not isinstance(pin['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', pin['sha256']):
        raise ValueError('invalid pin')
    data = _bounded(path, limit)
    if len(data) != pin['size'] or hashlib.sha256(data).hexdigest() != pin['sha256']:
        raise ValueError('pin mismatch')
    return data


def _record_path(record, root, limit):
    if not isinstance(record, dict) or set(record) != {'path', 'size', 'sha256'}:
        raise ValueError('invalid record')
    path = _checked(record['path'], root=root)
    return path, {'size': record['size'], 'sha256': record['sha256']}


def _relative(value):
    if not isinstance(value, str) or not value or any(x in value for x in ('\\', ':', '*', '?', '"', '<', '>', '|')):
        raise ValueError('relative path refused')
    path = Path(value)
    if (path.is_absolute() or path.as_posix() != value or any(ord(c) < 32 for c in value) or
            any(part.casefold() in ('.', '..', '.git', '.obsidian') or part.endswith((' ', '.'))
                for part in value.split('/'))):
        raise ValueError('relative path refused')
    return path


def _approved(value, *, purpose=False):
    return (isinstance(value, dict) and value.get('state') == 'approved' and
            isinstance(value.get('reference'), str) and bool(value['reference'].strip()) and
            (not purpose or (isinstance(value.get('purpose'), str) and bool(value['purpose'].strip()))))


def validate_closure(profile):
    """Recheck every declared immutable reader input before and after each operation."""
    root = _checked(profile['private_root'], directory=True)
    closure = profile['closure']
    if not isinstance(closure, dict) or not 6 <= len(closure) <= 264:
        raise ValueError('invalid closure')
    paths = {str(_checked(name, root=root)): pin for name, pin in closure.items()}
    if len(paths) != len(closure): raise ValueError('duplicate paths')
    contents = {}
    def lookup(path, limit=1048576):
        name = str(_checked(str(path), root=root))
        if name not in paths: raise ValueError('uncovered reference')
        if name not in contents:
            contents[name] = _pin(Path(name), paths[name], limit)
        elif len(contents[name]) > limit:
            raise ValueError('oversized')
        return contents[name]
    grant_path = _checked(profile['grant'], root=root)
    grant = _read_json(lookup(grant_path, 65536))
    if (grant.get('schema') != 'brain-managed-read-grant-v1' or grant.get('source_kind') != 'synthetic' or
            grant.get('client') != 'chatgpt-openai' or not _approved(grant.get('owner_authorization'), purpose=True) or
            grant.get('prefixes') != [] or not isinstance(grant.get('note_ids'), list) or not grant['note_ids']):
        raise ValueError('grant refused')
    vault = _checked(grant.get('root'), root=root, directory=True)
    private = _checked(grant.get('private_root'), root=root, directory=True)
    if 'test-vault' not in [part.casefold() for part in vault.parts]: raise ValueError('vault refused')
    marker = private / '.private-staging.json'
    staging = _read_json(lookup(marker, 65536))
    if staging.get('live_writes') is not False or staging.get('external_exports') is not False:
        raise ValueError('staging refused')
    policy_path = _checked(grant.get('policy_path'), root=root)
    policy_data = lookup(policy_path, 131072)
    if hashlib.sha256(policy_data).hexdigest() != grant.get('policy_sha256'): raise ValueError('policy pin refused')
    policy = _read_json(policy_data)
    policy_id = policy.get('policy_id')
    if (policy.get('schema') != 'brain-publication-policy-v1' or policy.get('enabled') is not True or
            not _approved(policy.get('owner_authorization')) or not isinstance(policy_id, str) or
            not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', policy_id) or policy.get('vault_root') != str(vault)):
        raise ValueError('policy refused')
    directory = private / 'publications' / policy_id / 'managed'
    pointer_path = _checked(grant.get('manifest_pointer'), root=root)
    if pointer_path != directory / 'latest.json': raise ValueError('pointer refused')
    pointer = _read_json(lookup(pointer_path, 4096))
    relative = _relative(pointer.get('manifest'))
    if relative.suffix != '.json' or str(relative) == 'latest.json': raise ValueError('manifest refused')
    manifest_path = directory / relative
    manifest_data = lookup(manifest_path)
    if hashlib.sha256(manifest_data).hexdigest() != pointer.get('sha256'): raise ValueError('manifest pin refused')
    manifest = _read_json(manifest_data)
    notes = manifest.get('notes')
    if not isinstance(notes, list) or not 2 <= len(notes) <= 256: raise ValueError('notes refused')
    required = {str(grant_path), str(marker), str(policy_path), str(pointer_path), str(manifest_path)}
    ids = set()
    for note in notes:
        if not isinstance(note, dict) or not isinstance(note.get('id'), str) or note['id'] in ids or note.get('privacy') != 'synthetic' or note.get('external_processing') is not False:
            raise ValueError('note refused')
        ids.add(note['id'])
        item = vault / _relative(note.get('path'))
        data = lookup(item, 128000)
        if len(data) > 128000 or len(data) != note.get('size') or hashlib.sha256(data).hexdigest() != note.get('sha256'):
            raise ValueError('note pin refused')
        text = data.decode('utf-8')
        front = re.match(r'\A---\n(.*?)\n---(?:\n|$)', text, re.S)
        if front is None or re.findall(r'^privacy:\s*(.*?)\s*$', front[1], re.M) != ['"synthetic"']:
            raise ValueError('note privacy refused')
        required.add(str(item))
    selected = set(grant['note_ids'])
    if not selected.issubset(ids) or not (ids - selected) or set(paths) != required:
        raise ValueError('closure refused')


def load_profile(filename, digest):
    path = _checked(filename)
    raw = _bounded(path, 65536)
    if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest) or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('profile pin refused')
    profile = _read_json(raw)
    keys = {'schema', 'state', 'scope', 'owner_reference', 'additional_spend_usd',
            'lifetime_seconds', 'startup_timeout_seconds', 'recipients', 'private_root',
            'runtime_dir', 'runtime', 'helper', 'config', 'owner_code', 'grant',
            'closure', 'client_id', 'callback', 'intent_path', 'receipt_path', 'temp_dir'}
    if set(profile) != keys or profile['schema'] != 'brain-chat-synthetic-launch-v1' or profile['state'] != 'approved' or profile['scope'] != 'synthetic-only':
        raise ValueError('profile refused')
    if not isinstance(profile['owner_reference'], str) or not profile['owner_reference'].strip() or type(profile['additional_spend_usd']) is not int or profile['additional_spend_usd'] != 0:
        raise ValueError('profile refused')
    if type(profile['lifetime_seconds']) is not int or not 1 <= profile['lifetime_seconds'] <= 900 or type(profile['startup_timeout_seconds']) is not int or not 1 <= profile['startup_timeout_seconds'] <= 60 or profile['recipients'] != ['Cloudflare', 'OpenAI', 'Sentry']:
        raise ValueError('profile refused')
    if not isinstance(profile['client_id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', profile['client_id']): raise ValueError('client refused')
    callback = profile['callback']
    if not isinstance(callback, str) or len(callback) > 2048 or not callback.isascii() or re.search(r'[\s\\*]', callback):
        raise ValueError('callback refused')
    url = urlsplit(callback)
    if url.scheme != 'https' or not url.hostname or not url.path or url.username or url.password or url.query or url.fragment:
        raise ValueError('callback refused')
    _ = url.port
    root = _checked(profile['private_root'], directory=True)
    _checked(filename, root=root)
    runtime = _checked(profile['runtime_dir'], root=root, directory=True)
    _checked(profile['temp_dir'], root=root, directory=True)
    intent = _checked(profile['intent_path'], root=root, absent=True)
    receipt = _checked(profile['receipt_path'], root=root, absent=True)
    hold = _checked(str(intent) + '.hold.json', root=root, absent=True)
    stop = _checked(str(intent) + '.stop.json', root=root, absent=True)
    if len({intent, receipt, hold, stop}) != 4: raise ValueError('collision')
    pins = profile['runtime']
    if not isinstance(pins, dict) or set(pins) != RUNTIME_NAMES: raise ValueError('runtime refused')
    sources = {name: _checked(str(runtime / name), root=root) for name in RUNTIME_NAMES}
    records = {name: _record_path(profile[name], root, 1) for name in ('helper', 'config', 'owner_code')}
    if Path(__file__).resolve() != sources['run_chat_synthetic.py'].resolve(): raise ValueError('wrong launcher')
    for name, source in sources.items(): _pin(source, pins[name], 1048576)
    _pin(*records['helper'], 268435456)
    if _pin(*records['config'], 3) != b'{}\n': raise ValueError('config refused')
    validate_closure(profile)
    secret = _pin(*records['owner_code'], 128)
    if not re.fullmatch(rb'[A-Za-z0-9_-]{43,128}', secret): raise ValueError('owner code refused')
    return profile


def _load_runtime(profile):
    """Load only verified local modules; Python and installed dependencies are trusted."""
    root = _checked(profile['private_root'], directory=True)
    runtime = _checked(profile['runtime_dir'], root=root, directory=True)
    order = ('run_chat_discovery', 'selected_memory', 'migrate', 'capture_outcomes',
             'save_interactive_memory', 'publish_memory', 'managed_memory',
             'chat_recall_oauth', 'chat_recall_http')
    if any(name in sys.modules for name in order):
        raise ValueError('local module already loaded')
    sources = {}
    for filename in RUNTIME_NAMES:
        path = _checked(str(runtime / filename), root=root)
        sources[filename] = (path, _pin(path, profile['runtime'][filename], 1048576))
    compiled = {name: compile(sources[name + '.py'][1], str(sources[name + '.py'][0]), 'exec')
                for name in order}
    loaded = {}
    try:
        for name in order:
            module = types.ModuleType(name)
            module.__file__ = str(sources[name + '.py'][0])
            module.__package__ = ''
            sys.modules[name] = module
            loaded[name] = module
            exec(compiled[name], module.__dict__)
        return loaded['run_chat_discovery'], loaded['chat_recall_http']
    except BaseException:
        for name, module in loaded.items():
            if sys.modules.get(name) is module:
                del sys.modules[name]
        raise


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _child_observation(child):
    if child is None:
        return {'state': 'not_started', 'exit_code': None}
    try:
        code = child.poll()
    except Exception:
        return {'state': 'unknown', 'exit_code': None}
    if code is None:
        return {'state': 'running', 'exit_code': None}
    if type(code) is not int:
        return {'state': 'unknown', 'exit_code': None}
    return {'state': 'exited', 'exit_code': code if -(2**31) <= code <= 2**32 - 1 else None}


def _elapsed_ms(begin):
    if begin is None:
        return None
    try:
        return min(86400000, max(0, int((time.monotonic() - begin) * 1000)))
    except Exception:
        return None


def _snapshot_observations(lock, guard, observations):
    snapshot = {'guard_failed': None, 'recognized_origin': None,
                'stream_eof': None, 'stream_read_error': None, 'guard_failure_mask': None}
    if lock is None:
        return snapshot
    with lock:
        if observations['stream_eof'] is not None:
            if type(guard.failure_mask) is not int or not 0 <= guard.failure_mask <= 31:
                raise ValueError('guard classification refused')
            snapshot = {'guard_failed': bool(guard.failed),
                        'recognized_origin': guard.origin is not None,
                        'stream_eof': observations['stream_eof'],
                        'stream_read_error': observations['stream_read_error'],
                        'guard_failure_mask': guard.failure_mask}
    return snapshot


def run_profile(profile, profile_digest):
    shared, transport = _load_runtime(profile)
    root = duplicate = child = server = server_thread = app = None
    port = pid = origin = creation = None
    started, attempted, status = _now(), None, 'error'
    run_id = uuid.uuid4().hex
    ready = False
    guard = shared.OutputGuard()
    begin = lock = None
    phase, reason = 'session_start', 'stage_error'
    observations = {'guard_failed': None, 'recognized_origin': None,
                    'stream_eof': None, 'stream_read_error': None}
    pins = {'runtime': profile['runtime'], 'helper': profile['helper'], 'config': profile['config'],
            'owner_code': profile['owner_code'], 'closure': profile['closure']}
    intent = {'schema': 'brain-chat-synthetic-intent-v1', 'run_id': run_id,
              'profile_sha256': profile_digest, 'input_pins': pins, 'started_at': started}
    shared._record(profile['intent_path'], intent)
    def check_stop():
        nonlocal reason
        if os.path.lexists(profile['intent_path'] + '.stop.json'):
            reason = 'stop_requested'
            raise ValueError('stop requested')
    try:
        check_stop()
        begin = time.monotonic()
        deadline = begin + profile['startup_timeout_seconds']
        end = begin + profile['lifetime_seconds']
        phase = 'listener'
        root = shared.open_exclusive_listener()
        port = root.getsockname()[1]
        env = {key: os.environ[key] for key in ('SystemRoot', 'WINDIR') if key in os.environ}
        env.update({'TEMP': profile['temp_dir'], 'TMP': profile['temp_dir']})
        argv = [profile['helper']['path'], 'tunnel', '--no-autoupdate', '--no-prechecks',
                '--config', profile['config']['path'], '--metrics', '127.0.0.1:0',
                '--management-diagnostics=false', '--loglevel', 'info', '--protocol', 'http2',
                '--url', f'http://127.0.0.1:{port}']
        if time.monotonic() >= min(deadline, end):
            reason = 'startup_timeout'
            raise ValueError('startup timeout')
        check_stop()
        attempted = _now()
        phase = 'helper_spawn'
        child = subprocess.Popen(argv, shell=False, env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        pid = child.pid
        phase = 'process_identity'
        creation = shared._creation_filetime(child)
        lock = threading.Lock()
        phase = 'output_startup'
        def drain():
            try:
                with lock:
                    observations['stream_eof'] = False
                    observations['stream_read_error'] = False
                while True:
                    chunk = child.stdout.read(1)
                    if not chunk:
                        with lock: observations['stream_eof'] = True
                        return
                    with lock: guard.feed(chunk)
            except Exception:
                with lock:
                    observations['stream_read_error'] = True
                    guard.failed = True
        threading.Thread(target=drain, daemon=True).start()
        while time.monotonic() < deadline and time.monotonic() < end:
            check_stop()
            with lock:
                failed, origin = guard.failed, guard.origin
                read_error = observations['stream_read_error']
            if failed:
                reason = 'stream_read_error' if read_error is True else 'guard_rejected'
                raise ValueError('startup refused')
            if child.poll() is not None:
                reason = 'child_exited'
                raise ValueError('startup refused')
            if origin: break
            time.sleep(.02)
        if not origin:
            reason = 'startup_timeout'
            raise ValueError('startup timeout')
        with lock: guard.started = True
        check_stop()
        phase = 'closure_validation'
        validate_closure(profile)
        if time.monotonic() >= min(deadline, end):
            reason = 'startup_timeout'
            raise ValueError('startup timeout')
        check_stop()
        phase = 'owner_code'
        code_path, code_pin = _record_path(profile['owner_code'], Path(profile['private_root']), 128)
        owner_code = _pin(code_path, code_pin, 128).decode('ascii')
        try:
            phase = 'app_factory'
            app = transport.create_app(profile['grant'], profile['closure'][profile['grant']]['sha256'],
                                       'chatgpt-openai', origin, profile['client_id'], profile['callback'],
                                       owner_code, loopback_port=port,
                                       operation_guard=lambda: validate_closure(profile))
        finally:
            owner_code = None
        if time.monotonic() >= min(deadline, end):
            reason = 'startup_timeout'
            raise ValueError('startup timeout')
        check_stop()
        phase = 'server_startup'
        import uvicorn
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port, access_log=False,
                                proxy_headers=False, log_config=None, log_level='critical'))
        duplicate = root.dup()
        def serve():
            try: server.run(sockets=[duplicate])
            except BaseException: pass
        server_thread = threading.Thread(target=serve, daemon=True)
        server_thread.start()
        while time.monotonic() < end and (ready or time.monotonic() < deadline):
            check_stop()
            with lock:
                if guard.failed:
                    reason = 'stream_read_error' if observations['stream_read_error'] is True else 'guard_rejected'
                    raise ValueError('session stopped')
                if guard.origin != origin:
                    reason = 'origin_changed'
                    raise ValueError('session stopped')
                if child.poll() is not None:
                    reason = 'child_exited'
                    raise ValueError('session stopped')
                if not server_thread.is_alive():
                    reason = 'server_stopped'
                    raise ValueError('session stopped')
                if server.started and not ready:
                    output = json.dumps({'status': 'synthetic-only', 'origin': origin, 'mcp_url': origin + '/mcp'}, separators=(',', ':'))
                    if len(output.encode('utf-8')) > 511: raise ValueError('ready too large')
                    print(output, flush=True)
                    ready = True
                    phase = 'serving'
            time.sleep(.02)
        if not ready:
            reason = 'ready_not_emitted'
            raise ValueError('ready not emitted')
        status = 'lifetime_elapsed'
        reason = 'lifetime_elapsed'
    except KeyboardInterrupt:
        reason = 'interrupted'
        status = 'error'
    except SystemExit:
        reason = 'system_exit'
        status = 'error'
    except Exception:
        status = 'error'
    finally:
        try:
            elapsed = _elapsed_ms(begin)
        except KeyboardInterrupt:
            elapsed, status, reason = None, 'error', 'interrupted'
        except SystemExit:
            elapsed, status, reason = None, 'error', 'system_exit'
        owner_cleanup_failed = False if app is not None else None
        snapshot = {'guard_failed': None, 'recognized_origin': None,
                    'stream_eof': None, 'stream_read_error': None, 'guard_failure_mask': None}
        try:
            snapshot = _snapshot_observations(lock, guard, observations)
        except KeyboardInterrupt:
            status, reason = 'error', 'interrupted'
        except SystemExit:
            status, reason = 'error', 'system_exit'
        except Exception:
            pass
        try:
            pre_cleanup_child = _child_observation(child)
        except KeyboardInterrupt:
            status, reason = 'error', 'interrupted'
            pre_cleanup_child = {'state': 'unknown', 'exit_code': None}
        except SystemExit:
            status, reason = 'error', 'system_exit'
            pre_cleanup_child = {'state': 'unknown', 'exit_code': None}
        def on_hold(reason):
            report = {'schema': 'brain-chat-synthetic-hold-v1', 'run_id': run_id, 'reason': reason,
                      'port': port, 'child_pid': pid, 'child_creation_filetime': creation,
                      'server_thread_id': server_thread.ident if server_thread is not None else None,
                      'server_native_id': server_thread.native_id if server_thread is not None else None}
            try:
                if len(json.dumps(report).encode()) > 2048: raise ValueError('hold too large')
                shared._record(profile['intent_path'] + '.hold.json', report)
            except BaseException:
                print('private hold report unavailable', file=sys.stderr)
        owner_done = threading.Event()
        owner_result = []
        def close_owner():
            try:
                app.state.owner_cleanup()
                owner_result.append(True)
            except BaseException:
                owner_result.append(False)
            finally:
                owner_done.set()
        def begin_owner_close():
            owner_done.clear()
            threading.Thread(target=close_owner, daemon=True).start()
        if app is not None:
            try: begin_owner_close()
            except BaseException:
                owner_result.append(False)
                owner_done.set()
        class RetainedRoot:
            def close(self):
                nonlocal status, owner_cleanup_failed
                reported = False
                if app is not None:
                    while True:
                        try:
                            if not owner_done.wait(1):
                                if not reported: on_hold('owner'); reported = True
                                continue
                            if owner_result and owner_result[-1]: break
                            status = 'error'
                            owner_cleanup_failed = True
                            if not reported: on_hold('owner'); reported = True
                            time.sleep(.05)
                            begin_owner_close()
                        except BaseException:
                            status = 'error'
                            owner_cleanup_failed = True
                            if not reported: on_hold('owner'); reported = True
                root.close()
        shared.cleanup(child, server, server_thread, duplicate, RetainedRoot() if root is not None else None, on_hold)
    try:
        post_cleanup_child = _child_observation(child)
    except KeyboardInterrupt:
        status, reason = 'error', 'interrupted'
        post_cleanup_child = {'state': 'unknown', 'exit_code': None}
    except SystemExit:
        status, reason = 'error', 'system_exit'
        post_cleanup_child = {'state': 'unknown', 'exit_code': None}
    diagnostic = {'schema': 'brain-chat-synthetic-diagnostic-v1', 'phase': phase, 'reason': reason,
                  'elapsed_ms': elapsed, **snapshot, 'owner_cleanup_failed': owner_cleanup_failed,
                  'pre_cleanup_child': pre_cleanup_child,
                  'post_cleanup_child': post_cleanup_child}
    if (phase not in DIAGNOSTIC_PHASES or reason not in DIAGNOSTIC_REASONS or
            len(json.dumps(diagnostic, separators=(',', ':')).encode('utf-8')) > 1024):
        raise ValueError('diagnostic refused')
    receipt = {'schema': 'brain-chat-synthetic-receipt-v1', 'run_id': run_id,
               'profile_sha256': profile_digest, 'input_pins': pins, 'origin': origin, 'port': port,
               'child_pid': pid, 'child_creation_filetime': creation, 'spawn_attempted_at': attempted,
               'started_at': started, 'ended_at': _now(), 'status': status, 'cleanup': 'complete',
               'diagnostic': diagnostic}
    if len(json.dumps(receipt, sort_keys=True, separators=(',', ':')).encode('utf-8')) > 524288:
        raise ValueError('receipt refused')
    shared._record(profile['receipt_path'], receipt)
    return 0 if status == 'lifetime_elapsed' else 1


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) != 2: raise ValueError('arguments refused')
        profile = load_profile(*args)
        return run_profile(profile, args[1])
    except (Exception, KeyboardInterrupt):
        return 1
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
