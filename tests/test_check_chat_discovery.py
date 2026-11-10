import io
import http.client
import os
import json
import socket
import ssl
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import check_chat_discovery as c

ORIGIN = 'https://fictional.trycloudflare.com'
CANARY = 'PRIVATE_CANARY_72'

class Reply:
    def __init__(self, status=200, body=b'{}', headers=None):
        self.status, self.body, self.headers = status, body, headers or {}
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, maximum): return self.body[:maximum]

class Fake:
    def __init__(self, replies): self.replies, self.requests = iter(replies), []
    def open(self, request, timeout):
        self.requests.append((request, timeout))
        value = next(self.replies)
        if isinstance(value, BaseException): raise value
        return value

def good():
    auth = {'issuer': ORIGIN, 'code_challenge_methods_supported':['S256'], 'token_endpoint_auth_methods_supported':['none']}
    resource = {'resource': ORIGIN+'/mcp', 'authorization_servers':[ORIGIN]}
    return [Reply(body=json.dumps(auth).encode()), Reply(body=json.dumps(resource).encode()),
            HTTPError(ORIGIN+'/mcp', 401, CANARY, {'WWW-Authenticate': 'Bearer resource_metadata="'+ORIGIN+'/.well-known/oauth-protected-resource/mcp"'}, io.BytesIO(b'{}'))]

class CheckerTests(unittest.TestCase):
    def test_origin_strict(self):
        c.validate_origin(ORIGIN)
        for value in ['http://x.trycloudflare.com','https://X.trycloudflare.com','https://a.b.trycloudflare.com','https://-a.trycloudflare.com','https://a-.trycloudflare.com','https://a.trycloudflare.com/','https://a.trycloudflare.com:443','https://a.trycloudflare.com?x','https://u@a.trycloudflare.com','https://a.trycloudflare.com#x']:
            with self.subTest(value=value), self.assertRaises(ValueError): c.validate_origin(value)
    def test_success_and_fixed_requests(self):
        fake=Fake(good()); result=c.check(ORIGIN, fake)
        self.assertEqual(len(fake.requests),3)
        self.assertEqual([r.get_method() for r,_ in fake.requests],['GET','GET','POST'])
        self.assertEqual([r.full_url.removeprefix(ORIGIN) for r,_ in fake.requests],['/.well-known/oauth-authorization-server','/.well-known/oauth-protected-resource/mcp','/mcp'])
        self.assertTrue(all(v is True for v in result['checks'].values()))
        self.assertNotIn(ORIGIN,json.dumps(result)); self.assertNotIn(CANARY,json.dumps(result))
    def test_challenge_missing_and_wrong(self):
        for header, present in [({},False),({'WWW-Authenticate':'Bearer resource_metadata="https://bad.example/"'},True)]:
            replies=good(); replies[2]=HTTPError(ORIGIN,401,CANARY,header,io.BytesIO(b''))
            checks=c.check(ORIGIN,Fake(replies))['checks']
            self.assertEqual(checks['challenge_present'],present); self.assertFalse(checks['challenge_match'])
    def test_errors_status_and_redirection(self):
        cases=[(HTTPError(ORIGIN,404,CANARY,{},io.BytesIO(b'x')),'http',404), (HTTPError(ORIGIN,302,CANARY,{'Location':'https://bad.example'},io.BytesIO(b'')),'redirect',302), (URLError(socket.gaierror(11001,CANARY)),'dns',None),(URLError(ssl.SSLError(CANARY)),'tls',None),(URLError(socket.timeout(CANARY)),'timeout',None),(URLError(ConnectionRefusedError(CANARY)),'connection',None),(URLError(ValueError(CANARY)),'other',None)]
        for exc,category,status in cases:
            with self.subTest(category=category):
                fake=Fake([exc,*good()[1:]]); out=c.check(ORIGIN,fake)
                self.assertEqual((out['requests'][0]['error'],out['requests'][0]['status']),(category,status)); self.assertEqual(len(fake.requests),3)
                self.assertNotIn(CANARY,json.dumps(out))
    def test_bad_and_oversized_json(self):
        for body,kind in [(b'{bad','malformed'),(b'x'*(c.MAX_RESPONSE+1),'oversized')]:
            out=c.check(ORIGIN,Fake([Reply(body=body),*good()[1:]]))
            self.assertEqual(out['requests'][0]['error'],kind)
    def test_private_create_only_and_redaction(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); target=root/'receipt.json'; fake=Fake(good())
            result=c.run(ORIGIN,str(root),str(target),fake)
            self.assertEqual(json.loads(target.read_text()),result)
            self.assertNotIn(ORIGIN,target.read_text()); self.assertNotIn(CANARY,target.read_text())
            fake2=Fake([])
            with self.assertRaises((ValueError,FileExistsError)): c.run(ORIGIN,str(root),str(target),fake2)
            self.assertEqual(fake2.requests,[])
            with self.assertRaises(ValueError): c.run(ORIGIN,str(root),str(root.parent/'outside.json'),Fake([]))
    def test_redirect_handler_never_follows(self):
        handler = c.NoRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 302, '', {}, 'https://bad.example/'))
    def test_timeout_raised_during_read(self):
        class Slow(Reply):
            def read(self, maximum): raise socket.timeout(CANARY)
        out=c.check(ORIGIN,Fake([Slow(),*good()[1:]]))
        self.assertEqual(out['requests'][0]['error'],'timeout')
        self.assertNotIn(CANARY,json.dumps(out))
    def test_malformed_schema_and_limits(self):
        for body in (b'[]', b'null', b'"text"', b'\xff'):
            with self.subTest(body=body):
                self.assertEqual(c.check(ORIGIN,Fake([Reply(body=body),*good()[1:]]))['requests'][0]['error'],'malformed')
    def test_cli_argument_errors_are_redacted(self):
        script=Path(__file__).resolve().parents[1]/'scripts'/'check_chat_discovery.py'
        result=subprocess.run([sys.executable,'-B',str(script),'--secret-'+CANARY], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode,1)
        self.assertNotIn(CANARY,result.stdout+result.stderr)
        self.assertEqual(json.loads(result.stdout)['error'],'refused')
        self.assertEqual(result.stderr,'')
    def test_existing_symlink_receipt_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); dest=root/'dest'; dest.write_text('preserve')
            link=root/'receipt'
            try: link.symlink_to(dest)
            except OSError: self.skipTest('symlinks unavailable on this Windows account')
            fake=Fake([])
            with self.assertRaises(ValueError): c.run(ORIGIN,str(root),str(link),fake)
            self.assertEqual(dest.read_text(),'preserve'); self.assertEqual(fake.requests,[])
    def test_reservation_is_durable_before_transport_and_same_handle(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); target=root/'receipt.json'; events=[]; real_fsync=os.fsync
            class Checking(Fake):
                def open(self, request, timeout):
                    self_outer.assertEqual(events, ['fsync'])
                    self_outer.assertTrue(target.exists())
                    self_outer.assertEqual(target.read_bytes(),b'')
                    return super().open(request, timeout)
            self_outer=self; fake=Checking(good())
            def fsync(fd): events.append('fsync'); real_fsync(fd)
            with patch.object(c.os,'fsync',side_effect=fsync): c.run(ORIGIN,str(root),str(target),fake)
            self.assertEqual(len(fake.requests),3); self.assertLessEqual(target.stat().st_size,8192)
    def test_failed_reservation_flush_prevents_transport(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); fake=Fake([])
            with patch.object(c.os,'fsync',side_effect=OSError(CANARY)):
                with self.assertRaises(OSError): c.run(ORIGIN,str(root),str(root/'receipt'),fake)
            self.assertFalse(fake.requests)
    def test_body_and_challenge_byte_caps(self):
        self.assertEqual(c.MAX_RESPONSE,16384)
        self.assertEqual(c._challenge({'WWW-Authenticate':'Bearer '+('x'*4097)}, 'unused'),(None,None))
    def test_system_proxy_discovery_disabled(self):
        import urllib.request
        with patch.dict(os.environ, {'HTTPS_PROXY':'http://127.0.0.1:9','HTTP_PROXY':'http://127.0.0.1:9','ALL_PROXY':'http://127.0.0.1:9'}), patch.object(urllib.request,'getproxies',side_effect=AssertionError('proxy discovery')):
            opener=c.make_opener()
        self.assertFalse(any(isinstance(h, urllib.request.HTTPCookieProcessor) for h in opener.handlers))
        self.assertFalse(any(isinstance(h, urllib.request.ProxyHandler) for h in opener.handlers))
    def test_stdlib_header_limits_and_redacted_classification(self):
        class Socket:
            def __init__(self, payload): self.payload=payload
            def makefile(self, *args): return io.BytesIO(self.payload)
        for header in [b'X: '+b'a'*65536+b'\r\n', b''.join(b'X: a\r\n' for _ in range(101))]:
            response=http.client.HTTPResponse(Socket(b'HTTP/1.1 200 OK\r\n'+header+b'\r\n'))
            with self.assertRaises(http.client.HTTPException): response.begin()
        out=c.check(ORIGIN,Fake([http.client.LineTooLong(CANARY),*good()[1:]]))
        self.assertEqual(out['requests'][0]['error'],'oversized')
        self.assertNotIn(CANARY,json.dumps(out))
    def test_receipt_and_stdout_limits_are_enforced(self):
        self.assertLessEqual(len(c._serialize(c.check(ORIGIN,Fake(good())))),1024)
        with self.assertRaises(ValueError): c._serialize({'unexpected': 'x'*8192})
    def test_unknown_for_failed_metadata_and_other_checks_survive(self):
        failures=[Reply(status=101,body=b'{}'),URLError(socket.gaierror(1,CANARY)),URLError(ssl.SSLError(CANARY)),URLError(socket.timeout(CANARY)),URLError(ConnectionRefusedError(CANARY)),HTTPError(ORIGIN,404,CANARY,{},io.BytesIO(b'')),HTTPError(ORIGIN,302,CANARY,{},io.BytesIO(b'')),Reply(body=b'{'),Reply(body=b'x'*(c.MAX_RESPONSE+1))]
        keys=[('issuer_match','s256','token_auth_none'),('resource_match','authorization_server_match')]
        for index in (0,1):
            for failure in failures:
                with self.subTest(index=index, failure=type(failure).__name__):
                    replies=good(); replies[index]=failure
                    checks=c.check(ORIGIN,Fake(replies))['checks']
                    for key in keys[index]: self.assertIsNone(checks[key],key)
                    for key in keys[1-index]: self.assertIs(checks[key],True,key)
                    self.assertIs(checks['challenge_match'],True)
    def test_wrong_field_types_and_ambiguous_json_are_malformed_unknown(self):
        cases=[(0,b'{"issuer":17}'),(0,b'{"issuer":"a","issuer":"b"}'),(0,b'{"issuer":NaN}'),(0,b'{"code_challenge_methods_supported":[12]}'),(1,b'{"resource":null}'),(1,b'{"authorization_servers":"not-an-array"}')]
        for index,body in cases:
            with self.subTest(index=index,body=body):
                replies=good(); replies[index]=Reply(body=body); out=c.check(ORIGIN,Fake(replies))
                self.assertEqual(out['requests'][index]['error'],'malformed')
                keys=('issuer_match','s256','token_auth_none') if index == 0 else ('resource_match','authorization_server_match')
                for key in keys: self.assertIsNone(out['checks'][key])
    def test_failed_mcp_and_uninspected_challenge_are_unknown(self):
        class Slow(Reply):
            def read(self, maximum): raise socket.timeout(CANARY)
        cases=[URLError(socket.gaierror(1,CANARY)),URLError(ssl.SSLError(CANARY)),URLError(socket.timeout(CANARY)),HTTPError(ORIGIN,403,CANARY,{},io.BytesIO(b'')),HTTPError(ORIGIN,302,CANARY,{},io.BytesIO(b'')),Reply(status=200),Reply(status=401,headers={'WWW-Authenticate':'Bearer '+('x'*4097)}),Reply(status=401,body=b'x'*(c.MAX_RESPONSE+1),headers={'WWW-Authenticate':'Bearer'}),Slow(status=401,headers={'WWW-Authenticate':'Bearer'})]
        for failure in cases:
            with self.subTest(failure=type(failure).__name__):
                replies=good(); replies[2]=failure
                checks=c.check(ORIGIN,Fake(replies))['checks']
                self.assertIsNone(checks['challenge_present']); self.assertIsNone(checks['challenge_match'])
                self.assertTrue(checks['issuer_match']); self.assertTrue(checks['resource_match'])
    def test_observed_absence_and_mismatch_are_false(self):
        replies=good(); replies[0]=Reply(body=b'{"issuer":"wrong","code_challenge_methods_supported":[],"token_endpoint_auth_methods_supported":[]}'); replies[1]=Reply(body=b'{}'); replies[2]=HTTPError(ORIGIN,401,CANARY,{},io.BytesIO(b''))
        checks=c.check(ORIGIN,Fake(replies))['checks']
        self.assertTrue(all(value is False for value in checks.values()))
    def test_failure_states_survive_receipt_and_stdout_serialization(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); replies=good(); replies[0]=URLError(socket.timeout(CANARY)); replies[2]=Reply(status=403)
            result=c.run(ORIGIN,str(root),str(root/'r.json'),Fake(replies))
            saved=json.loads((root/'r.json').read_text()); printed=json.loads(c._serialize(result))
            self.assertEqual(saved,printed); self.assertIsNone(saved['checks']['issuer_match']); self.assertIsNone(saved['checks']['challenge_match'])
            self.assertNotIn(CANARY,json.dumps(saved))
    def test_git_ancestor_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'.git').mkdir()
            with self.assertRaises(ValueError): c.run(ORIGIN,str(root),str(root/'receipt.json'),Fake([]))

if __name__ == '__main__': unittest.main()
