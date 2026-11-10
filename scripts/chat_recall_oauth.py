"""In-memory owner-code OAuth state for a synthetic-only prototype."""
import hmac
import re
import secrets
import threading
import time
from urllib.parse import urlencode, urlsplit

from mcp.server.auth.provider import AccessToken, AuthorizationCode, AuthorizeError, TokenError
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken


def _https(value, *, origin=False):
    if not isinstance(value, str) or len(value) > 2048 or not value.isascii() or re.search(r'[\s\\*]', value):
        return False
    parsed = urlsplit(value)
    return (parsed.scheme == 'https' and bool(parsed.hostname) and not parsed.username and
            not parsed.password and not parsed.fragment and not parsed.query and
            ((not parsed.path) if origin else bool(parsed.path)))


class OwnerOAuth:
    """Owner-code possession only; does not attest a ChatGPT account.

    The operator must supply at least 256 random bits; syntax checks cannot prove entropy.
    """
    def __init__(self, origin, client_id, callback, owner_secret):
        if not _https(origin, origin=True) or not _https(callback):
            raise ValueError('invalid configured URL')
        if not isinstance(client_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', client_id):
            raise ValueError('invalid client')
        if not isinstance(owner_secret, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43,128}', owner_secret):
            raise ValueError('invalid owner code')
        self.origin, self.resource, self.callback = origin, origin + '/mcp', callback
        self._secret = owner_secret.encode('ascii')
        self.client = OAuthClientInformationFull(client_id=client_id, redirect_uris=[callback],
                                                 token_endpoint_auth_method='none',
                                                 grant_types=['authorization_code'], response_types=['code'],
                                                 scope='memory:read')
        self._lock = threading.Lock()
        self._tickets, self._codes, self._tokens = {}, {}, {}
        self._failures = []
        self._closed = False

    def close(self):
        with self._lock:
            self._closed = True
            self._tickets.clear()
            self._codes.clear()
            self._tokens.clear()
            self._failures.clear()
            self._secret = b''

    def _purge(self, now):
        for store in (self._tickets, self._codes, self._tokens):
            for key in [k for k, v in store.items() if v[0] <= now]:
                del store[key]
        self._failures = [t for t in self._failures if t > now - 60]

    async def get_client(self, client_id):
        with self._lock:
            return self.client if not self._closed and client_id == self.client.client_id else None

    async def register_client(self, client_info):
        raise ValueError('registration disabled')

    async def authorize(self, client, params):
        if (client.client_id != self.client.client_id or str(params.redirect_uri) != self.callback or
                not params.redirect_uri_provided_explicitly or params.scopes != ['memory:read'] or
                params.resource != self.resource or not re.fullmatch(r'[A-Za-z0-9_-]{43}', params.code_challenge) or
                not isinstance(params.state, str) or not 1 <= len(params.state) <= 256):
            raise AuthorizeError('invalid_request', 'request refused')
        now = time.time()
        with self._lock:
            if self._closed:
                raise AuthorizeError('temporarily_unavailable', 'request refused')
            self._purge(now)
            if len(self._tickets) >= 32:
                raise AuthorizeError('temporarily_unavailable', 'request refused')
            ticket, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            self._tickets[ticket] = (now + 120, csrf, params)
        return self.origin + '/consent?' + urlencode({'ticket': ticket})

    def consent_csrf(self, ticket):
        if not isinstance(ticket, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', ticket):
            return None
        with self._lock:
            if self._closed:
                return None
            self._purge(time.time())
            value = self._tickets.get(ticket)
            return value[1] if value else None

    def consent(self, ticket, form_csrf, cookie_csrf, secret):
        if (not isinstance(ticket, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', ticket)
                or not isinstance(form_csrf, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', form_csrf)
                or not isinstance(cookie_csrf, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', cookie_csrf)):
            return None
        now = time.time()
        with self._lock:
            if self._closed:
                return None
            self._purge(now)
            item = self._tickets.get(ticket)
            valid = (isinstance(secret, str) and len(secret) <= 128 and secret.isascii() and
                     hmac.compare_digest(secret.encode('ascii'), self._secret))
            csrf_valid = (item is not None and isinstance(form_csrf, str) and isinstance(cookie_csrf, str) and
                          hmac.compare_digest(item[1], form_csrf) and hmac.compare_digest(item[1], cookie_csrf))
            if not valid or not csrf_valid or len(self._failures) >= 10 or len(self._codes) >= 32:
                if len(self._failures) < 10:
                    self._failures.append(now)
                return None
            del self._tickets[ticket]
            params = item[2]
            code = secrets.token_urlsafe(32)
            record = AuthorizationCode(code=code, scopes=['memory:read'], expires_at=now + 60,
                                       client_id=self.client.client_id, code_challenge=params.code_challenge,
                                       redirect_uri=params.redirect_uri, redirect_uri_provided_explicitly=True,
                                       resource=self.resource, subject='owner-code-holder')
            self._codes[code] = (now + 60, record, params.state)
            return code, params.state

    async def load_authorization_code(self, client, authorization_code):
        with self._lock:
            if self._closed:
                return None
            self._purge(time.time())
            item = self._codes.get(authorization_code)
            return item[1] if item and client.client_id == self.client.client_id else None

    async def exchange_authorization_code(self, client, authorization_code):
        with self._lock:
            now = time.time()
            if self._closed:
                raise TokenError('invalid_grant', 'request refused')
            self._purge(now)
            item = self._codes.get(authorization_code.code) if authorization_code is not None else None
            if (item is None or item[1] != authorization_code or client.client_id != self.client.client_id or
                    len(self._tokens) >= 64):
                raise TokenError('invalid_grant', 'request refused')
            del self._codes[authorization_code.code]
            token = secrets.token_urlsafe(32)
            access = AccessToken(token=token, client_id=self.client.client_id, scopes=['memory:read'],
                                 expires_at=int(now + 300), resource=self.resource,
                                 subject='owner-code-holder', claims={'iss': self.origin})
            self._tokens[token] = (now + 300, access)
        return OAuthToken(access_token=token, expires_in=300, scope='memory:read')

    async def load_access_token(self, token):
        with self._lock:
            if self._closed:
                return None
            now = time.time()
            self._purge(now)
            item = self._tokens.get(token)
            if not item:
                return None
            access = item[1]
            if (access.token != token or access.client_id != self.client.client_id or
                    access.resource != self.resource or access.scopes != ['memory:read'] or
                    access.subject != 'owner-code-holder' or access.claims != {'iss': self.origin} or
                    type(access.expires_at) is not int or access.expires_at <= now):
                return None
            return access

    async def load_refresh_token(self, client, refresh_token):
        return None

    async def exchange_refresh_token(self, client, refresh_token, scopes):
        raise TokenError('unsupported_grant_type', 'request refused')

    async def revoke_token(self, token):
        with self._lock:
            self._tokens.pop(token.token, None)


class RedactedOAuth:
    """Keep provider exceptions out of SDK OAuth logs and responses."""
    def __init__(self, owner):
        self.owner = owner

    async def get_client(self, client_id):
        try:
            return await self.owner.get_client(client_id)
        except Exception:
            return None

    async def authorize(self, client, params):
        try:
            return await self.owner.authorize(client, params)
        except AuthorizeError as error:
            raise AuthorizeError(error.error, 'request refused') from None
        except Exception:
            raise AuthorizeError('server_error', 'request refused') from None

    async def load_authorization_code(self, client, code):
        try:
            return await self.owner.load_authorization_code(client, code)
        except Exception:
            return None

    async def exchange_authorization_code(self, client, code):
        try:
            return await self.owner.exchange_authorization_code(client, code)
        except Exception:
            raise TokenError('invalid_grant', 'request refused') from None

    async def load_access_token(self, token):
        try:
            return await self.owner.load_access_token(token)
        except Exception:
            return None

    async def register_client(self, client):
        raise ValueError('registration disabled')

    async def load_refresh_token(self, client, token):
        return None

    async def exchange_refresh_token(self, client, token, scopes):
        raise TokenError('unsupported_grant_type', 'request refused')

    async def revoke_token(self, token):
        return None
