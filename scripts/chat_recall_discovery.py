"""Discovery-only synthetic bootstrap; no reader, OAuth grant, or MCP tools."""
import argparse
import json
import re


_ORIGIN = re.compile(r'https://[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.trycloudflare\.com\Z')
_SECURITY = [(b'cache-control', b'no-store'), (b'referrer-policy', b'no-referrer'),
             (b'x-content-type-options', b'nosniff'),
             (b'content-security-policy', b"default-src 'none'; frame-ancestors 'none'")]


def create_app(origin, port):
    """Create an unstarted, non-reading ASGI metadata responder."""
    if not isinstance(origin, str) or not origin.isascii() or not _ORIGIN.fullmatch(origin):
        raise ValueError('configuration refused')
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('configuration refused')
    public_host = origin.removeprefix('https://').encode('ascii')
    allowed_hosts = {public_host, f'127.0.0.1:{port}'.encode(), f'localhost:{port}'.encode()}
    expected_origin = origin.encode('ascii')
    resource_url = origin + '/mcp'
    resource_metadata = origin + '/.well-known/oauth-protected-resource/mcp'
    resource = {'resource': resource_url, 'authorization_servers': [origin],
                'scopes_supported': ['memory:read'], 'description': 'Discovery-only; no authorization or tools.'}
    authorization = {'issuer': origin, 'authorization_endpoint': origin + '/authorize',
                     'token_endpoint': origin + '/token', 'response_types_supported': ['code'],
                     'grant_types_supported': ['authorization_code'], 'token_endpoint_auth_methods_supported': ['none'],
                     'code_challenge_methods_supported': ['S256'], 'scopes_supported': ['memory:read'],
                     'description': 'Discovery-only; authorization is disabled.'}

    async def respond(send, status, payload, method, extra=()):
        body = json.dumps(payload, separators=(',', ':')).encode('utf-8') if method != 'HEAD' else b''
        headers = [*_SECURITY, (b'content-type', b'application/json'),
                   (b'content-length', str(len(body)).encode()), *extra]
        await send({'type': 'http.response.start', 'status': status, 'headers': headers})
        await send({'type': 'http.response.body', 'body': body, 'more_body': False})

    async def app(scope, receive, send):
        if scope['type'] == 'lifespan':
            while True:
                event = await receive()
                if event['type'] == 'lifespan.startup':
                    await send({'type': 'lifespan.startup.complete'})
                elif event['type'] == 'lifespan.shutdown':
                    await send({'type': 'lifespan.shutdown.complete'})
                    return
            return
        if scope['type'] != 'http':
            if scope['type'] == 'websocket':
                await send({'type': 'websocket.close', 'code': 1008})
            return
        method = scope.get('method', '')
        try:
            path = scope.get('path', '')
            raw_path = scope.get('raw_path')
            query = scope.get('query_string', b'')
            headers = scope.get('headers', [])
            if (not isinstance(path, str) or not path.isascii() or len(path.encode('ascii')) > 2048 or
                    (raw_path is not None and (not isinstance(raw_path, bytes) or raw_path != path.encode('ascii'))) or
                    not isinstance(query, bytes) or len(query) > 4096 or not isinstance(headers, (list, tuple)) or
                    len(headers) > 64):
                raise ValueError()
            if any(not isinstance(item, (list, tuple)) or len(item) != 2 or
                   not all(isinstance(v, bytes) for v in item) for item in headers):
                raise ValueError()
            if sum(len(k) + len(v) for k, v in headers) > 16384:
                raise ValueError()
            hosts = [v for k, v in headers if k.lower() == b'host']
            origins = [v for k, v in headers if k.lower() == b'origin']
            if len(hosts) != 1 or hosts[0] not in allowed_hosts or len(origins) > 1 or (origins and origins[0] != expected_origin):
                raise ValueError()
        except (TypeError, ValueError, UnicodeError):
            await respond(send, 400, {'error': 'request_refused'}, method)
            return
        if path == '/mcp':
            challenge = ('Bearer resource_metadata="' + resource_metadata + '"').encode('ascii')
            await respond(send, 401, {'error': 'discovery_only'}, method, [(b'www-authenticate', challenge)])
        elif method == 'GET' and path == '/.well-known/oauth-protected-resource/mcp':
            await respond(send, 200, resource, method)
        elif method == 'GET' and path == '/.well-known/oauth-authorization-server':
            await respond(send, 200, authorization, method)
        else:
            await respond(send, 404, {'error': 'request_refused'}, method)
    return app


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('configuration refused')


def main(argv=None):
    parser = _Parser(add_help=False)
    parser.add_argument('--origin', required=True)
    parser.add_argument('--port', required=True)
    try:
        args = parser.parse_args(argv)
        if not re.fullmatch(r'[0-9]{1,5}', args.port):
            raise ValueError('configuration refused')
        port = int(args.port)
        app = create_app(args.origin, port)
        import uvicorn
        config = uvicorn.Config(app, host='127.0.0.1', port=port, access_log=False,
                                proxy_headers=False, log_config=None, log_level='critical')
        uvicorn.Server(config).run()
        return 0
    except (Exception, SystemExit, KeyboardInterrupt):
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
