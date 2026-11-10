import json, pathlib, sys, tempfile, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
import chat_ready_capture as cap
class Process:
    def __init__(self, alive=True): self.alive = alive
    def poll(self): return None if self.alive else 1
class ReadyCaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
    def payload(self, **updates):
        p = {'status':'synthetic-only','origin':'https://fake.trycloudflare.com','mcp_url':'https://fake.trycloudflare.com/mcp'}
        p.update(updates); return json.dumps(p,separators=(',',':')).encode()+b'\n'
    def test_success_and_collision(self):
        with cap.reserve(self.root, 'ready.jsonl') as (writer, reader):
            with self.assertRaises(FileExistsError): cap.reserve(self.root, 'ready.jsonl').__enter__()
            writer.write(self.payload())
            self.assertEqual(cap.wait_ready(reader,Process(),.1)['origin'],'https://fake.trycloudflare.com')
    def test_refuses_bad_records(self):
        bad=[b'{}\n', b'{"status":"synthetic-only","status":"synthetic-only"}\n', self.payload(status='live'),
             self.payload(origin='https://fake.trycloudflare.com:443',mcp_url='https://fake.trycloudflare.com:443/mcp'),
             self.payload(origin='https://x.trycloudflare.com/path'), self.payload(mcp_url='https://evil/mcp'),
             self.payload()+b'junk', b'x'*513, b'\xff\n']
        for i,data in enumerate(bad):
            with self.subTest(i=i):
                with cap.reserve(self.root,str(i)) as (writer,reader):
                    writer.write(data)
                    with self.assertRaises(cap.CaptureError): cap.wait_ready(reader,Process(),.1)
    def test_partial_timeout_and_early_exit(self):
        with cap.reserve(self.root,'partial') as (writer,reader):
            writer.write(b'{"status":')
            with self.assertRaises(cap.CaptureError): cap.wait_ready(reader,Process(),.01)
        with cap.reserve(self.root,'exited') as (writer,reader):
            writer.write(self.payload())
            with self.assertRaises(cap.CaptureError): cap.wait_ready(reader,Process(False),.1)
    def test_exit_after_read_is_refused(self):
        class ExitsAfterRead:
            def __init__(self): self.calls = 0
            def poll(self):
                self.calls += 1
                return None if self.calls == 1 else 1
        with cap.reserve(self.root,'after-read') as (writer,reader):
            writer.write(self.payload())
            with self.assertRaises(cap.CaptureError): cap.wait_ready(reader,ExitsAfterRead(),.1)
    def test_invalid_timeout_refused(self):
        with cap.reserve(self.root,'timeouts') as (_,reader):
            for timeout in [0, -1, 61, True, float('nan')]:
                with self.subTest(timeout=timeout):
                    with self.assertRaises(ValueError): cap.wait_ready(reader,Process(),timeout)
    def test_names_and_root_are_bounded(self):
        for name in ['../outside','child/record','', '.', '..']:
            with self.subTest(name=name):
                with self.assertRaises((ValueError, OSError)): cap.reserve(self.root,name).__enter__()
        with self.assertRaises((ValueError,OSError)): cap.reserve(self.root/'missing','record').__enter__()
if __name__=='__main__': unittest.main()
