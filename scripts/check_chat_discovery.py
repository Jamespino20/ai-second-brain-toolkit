"""Bounded, redacted discovery checker; execution requires separate approval."""
import argparse
import http.client
import json
import os
from pathlib import Path
import re
import socket
import ssl
import stat
import sys
from urllib.error import HTTPError, URLError
from urllib.request import (Request, build_opener, HTTPRedirectHandler, ProxyHandler)

MAX_RESPONSE = 16384
TIMEOUT = 5
PATHS = (('authorization_metadata', '/.well-known/oauth-authorization-server', 'GET'),
         ('protected_resource_metadata', '/.well-known/oauth-protected-resource/mcp', 'GET'),
         ('mcp', '/mcp', 'POST'))

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def validate_origin(origin):
    if not isinstance(origin, str) or not re.fullmatch(r'https://[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.trycloudflare\.com', origin, flags=re.ASCII):
        raise ValueError('origin refused')
    return origin

def _path(value, directory):
    if not isinstance(value, str) or not value:
        raise ValueError('path refused')
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts or any(p.casefold() == '.git' for p in path.parts):
        raise ValueError('path refused')
    if os.name == 'nt' and any(':' in p for p in path.parts[1:]):
        raise ValueError('path refused')
    candidate = path if directory else path.parent
    for part in reversed((candidate, *candidate.parents)):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('redirected path')
        if not stat.S_ISDIR(info.st_mode) or os.path.lexists(part / '.git'):
            raise ValueError('path refused')
    if not directory and os.path.lexists(path):
        raise ValueError('receipt exists')
    return path

def _category(exc):
    if isinstance(exc, URLError): exc = exc.reason
    if isinstance(exc, socket.gaierror): return 'dns'
    if isinstance(exc, ssl.SSLError): return 'tls'
    if isinstance(exc, (TimeoutError, socket.timeout)): return 'timeout'
    if isinstance(exc, ConnectionError): return 'connection'
    return 'other'

def _challenge(headers, expected):
    value = headers.get('WWW-Authenticate', '') if headers else ''
    if not isinstance(value, str) or len(value) > 4096 or len(value.encode('utf-8')) > 4096:
        return None, None
    matches = re.findall(r'(?i)(?:^|[ ,])resource_metadata\s*=\s*"([^"\\]*)"', value)
    return bool(value), bool(re.match(r'(?i)^\s*Bearer(?:\s|$)', value) and len(matches) == 1 and matches[0] == expected)

def _metadata(data, name):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate field')
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError('invalid constant')
    obj = json.loads(data.decode('utf-8'), object_pairs_hook=pairs, parse_constant=invalid_constant)
    if not isinstance(obj, dict):
        raise ValueError('object')
    strings = ('issuer',) if name == 'authorization_metadata' else ('resource',)
    arrays = ('code_challenge_methods_supported', 'token_endpoint_auth_methods_supported') if name == 'authorization_metadata' else ('authorization_servers',)
    if any(key in obj and not isinstance(obj[key], str) for key in strings):
        raise ValueError('invalid field')
    if any(key in obj and (not isinstance(obj[key], list) or any(not isinstance(item, str) for item in obj[key])) for key in arrays):
        raise ValueError('invalid field')
    return obj

def make_opener():
    return build_opener(ProxyHandler({}), NoRedirect())

def check(origin, opener=None):
    validate_origin(origin)
    if opener is None: opener = make_opener()
    checks = dict.fromkeys(('issuer_match','resource_match','authorization_server_match','s256','token_auth_none','challenge_present','challenge_match'), None)
    results = []
    for name, path, method in PATHS:
        record = {'path': name, 'status': None, 'error': None}
        req = Request(origin + path, data=b'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' if method == 'POST' else None,
                      headers={'Accept':'application/json, text/event-stream', **({'Content-Type':'application/json'} if method == 'POST' else {})}, method=method)
        try:
            try:
                response = opener.open(req, timeout=TIMEOUT)
            except HTTPError as exc:
                response = exc
            with response:
                status = response.status if hasattr(response, 'status') else response.code
                if type(status) is not int or not 100 <= status <= 599: raise ValueError('status')
                record['status'] = status
                data = response.read(MAX_RESPONSE + 1)
                if len(data) > MAX_RESPONSE:
                    record['error'] = 'oversized'
                elif 300 <= status < 400:
                    record['error'] = 'redirect'
                elif status < 200 or status >= 400:
                    record['error'] = 'http'
                    if name == 'mcp' and status == 401:
                        checks['challenge_present'], checks['challenge_match'] = _challenge(response.headers, origin + PATHS[1][1])
                elif name != 'mcp':
                    try:
                        obj = _metadata(data, name)
                    except (UnicodeError, ValueError, RecursionError):
                        record['error'] = 'malformed'
                    else:
                        if name == 'authorization_metadata':
                            checks['issuer_match'] = obj.get('issuer') == origin
                            checks['s256'] = isinstance(obj.get('code_challenge_methods_supported'), list) and 'S256' in obj['code_challenge_methods_supported']
                            checks['token_auth_none'] = isinstance(obj.get('token_endpoint_auth_methods_supported'), list) and 'none' in obj['token_endpoint_auth_methods_supported']
                        else:
                            checks['resource_match'] = obj.get('resource') == origin + '/mcp'
                            checks['authorization_server_match'] = isinstance(obj.get('authorization_servers'), list) and origin in obj['authorization_servers']
        except http.client.LineTooLong:
            record['error'] = 'oversized'
        except (URLError, OSError, ValueError, TypeError, http.client.HTTPException) as exc:
            record['error'] = _category(exc)
        results.append(record)
    return {'schema': 'chat-discovery-check-v1', 'requests': results, 'checks': checks}

def _serialize(result):
    data = json.dumps(result, separators=(',', ':'), ensure_ascii=True).encode('ascii')
    if len(data) + 1 > 1024 or len(data) + 1 > 8192:
        raise ValueError('output too large')
    return data

def run(origin, private_root, receipt_path, opener=None):
    validate_origin(origin)
    root = _path(private_root, True)
    receipt = _path(receipt_path, False)
    if root not in receipt.parents:
        raise ValueError('receipt outside root')
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(receipt, flags, 0o600)
    with os.fdopen(fd, 'wb') as output:
        output.flush()
        os.fsync(output.fileno())
        result = check(origin, opener)
        output.write(_serialize(result) + b'\n')
        output.flush()
        os.fsync(output.fileno())
    return result

class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('arguments refused')

def main():
    parser = _Parser(add_help=False)
    parser.add_argument('--origin', required=True)
    parser.add_argument('--private-root', required=True)
    parser.add_argument('--receipt', required=True)
    try:
        args = parser.parse_args()
        result = run(args.origin, args.private_root, args.receipt)
        print(_serialize(result).decode('ascii'), flush=True)
        return 0
    except (Exception, KeyboardInterrupt):
        print('{"schema":"chat-discovery-check-v1","error":"refused"}', flush=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())
