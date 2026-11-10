"""One-run local supervisor for the fictional Chat trial; never start implicitly.

The launcher remains responsible for its helper, OAuth and server cleanup. This
supervisor never terminates it. Stage records are observations, not a guarantee
that the session remains alive. A separately approved, reviewed package is
required before running this against a real endpoint.
"""
from contextlib import ExitStack
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import threading
import chat_ready_capture as capture

FIELDS={'root','interpreter','interpreter_sha256','launcher','launcher_sha256','profile','profile_sha256','checker','checker_sha256','ready_timeout','lifetime_timeout'}
CHECKS={'issuer_match','resource_match','authorization_server_match','s256','token_auth_none','challenge_present','challenge_match'}
REQUESTS=[('authorization_metadata',200,None),('protected_resource_metadata',200,None),('mcp',401,'http')]

class Refused(Exception): pass

def pairs(values):
    out={}
    for k,v in values:
        if k in out: raise Refused('duplicate key')
        out[k]=v
    return out

def load_json(data):
    try:
        return json.loads(data.decode('utf-8'), object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(Refused('invalid constant')))
    except (UnicodeError,ValueError,RecursionError) as e: raise Refused('invalid json') from e

def hash_file(path, expected, max_size):
    path=Path(path)
    if not path.is_absolute() or not isinstance(expected,str) or len(expected)!=64 or any(c not in '0123456789abcdef' for c in expected):
        raise Refused('pin refused')
    for p in (path,*path.parents):
        s=p.lstat()
        if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400: raise Refused('redirect refused')
    if not path.is_file(): raise Refused('pin refused')
    digest=hashlib.sha256(); size=0
    with path.open('rb') as f:
        while True:
            chunk=f.read(65536)
            if not chunk: break
            size+=len(chunk)
            if size>max_size: raise Refused('input too large')
            digest.update(chunk)
    if digest.hexdigest()!=expected: raise Refused('pin refused')

def process_creation(child):
    if sys.platform != 'win32': raise Refused('unsupported process identity')
    api=ctypes.WinDLL('kernel32',use_last_error=True).GetProcessTimes
    api.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4
    api.restype=wintypes.BOOL
    created,exited,kernel,user=(wintypes.FILETIME() for _ in range(4))
    if not api(int(child._handle),ctypes.byref(created),ctypes.byref(exited),ctypes.byref(kernel),ctypes.byref(user)):
        raise Refused('process identity refused')
    return (created.dwHighDateTime<<32)|created.dwLowDateTime

def checker_pass(value):
    if not isinstance(value,dict) or value.get('schema')!='chat-discovery-check-v1': return False
    requests,checks=value.get('requests'),value.get('checks')
    if not isinstance(requests,list) or len(requests)!=3 or not isinstance(checks,dict) or set(checks)!=CHECKS: return False
    return all(isinstance(x,dict) and (x.get('path'),x.get('status'),x.get('error'))==y for x,y in zip(requests,REQUESTS)) and all(checks[k] is True for k in CHECKS)

def write_record(file, value):
    raw=json.dumps(value,separators=(',',':'),ensure_ascii=True).encode()+b'\n'
    if len(raw)>1024: raise Refused('record too large')
    file.write(raw); file.flush(); os.fsync(file.fileno())

def validate(cfg):
    if not isinstance(cfg,dict) or set(cfg)!=FIELDS: raise Refused('config refused')
    root=Path(cfg['root'])
    if not root.is_absolute() or '..' in root.parts: raise Refused('root refused')
    capture._check_directory(root)
    # Establish containment and reject redirects for every package input before
    # opening or hashing any input, including the interpreter.
    for key in ('profile','launcher','checker'):
        path=Path(cfg[key])
        if not path.is_absolute() or '..' in path.parts or root not in path.parents: raise Refused('input outside root')
        capture._check_directory(path.parent)
        info=path.lstat()
        if not stat.S_ISREG(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400 or info.st_nlink!=1:
            raise Refused('input redirect refused')
    for key,limit in [('interpreter',200_000_000),('launcher',131072),('profile',131072),('checker',131072)]:
        hash_file(cfg[key],cfg[key+'_sha256'],limit)
    if not os.path.samefile(sys.executable,cfg['interpreter']): raise Refused('interpreter refused')
    for key,maximum in [('ready_timeout',60),('lifetime_timeout',930)]:
        if type(cfg[key]) is not int or not 1<=cfg[key]<=maximum: raise Refused('timeout refused')
    with open(cfg['profile'],'rb') as stream:
        profile=load_json(stream.read(131073))
    if not isinstance(profile,dict) or not isinstance(profile.get('intent_path'),str): raise Refused('profile refused')
    lifetime=profile.get('lifetime_seconds')
    if type(lifetime) is not int or not 1<=lifetime<=900: raise Refused('lifetime refused')
    intent=Path(profile['intent_path'])
    if not intent.is_absolute() or '..' in intent.parts or root not in intent.parents: raise Refused('intent refused')
    capture._check_directory(intent.parent)
    stop=Path(str(intent)+'.stop.json')
    if os.path.lexists(stop): raise Refused('stop collision')
    return root, stop, lifetime

def request_stop(path):
    capture._check_directory(path.parent)
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0)
    fd=os.open(path,flags,0o600)
    with os.fdopen(fd,'wb') as out:
        out.write(b'stop\n'); out.flush(); os.fsync(out.fileno())

def checker_result(args):
    # The checker is an owned child. Its stdout is consumed at a hard cap;
    # unlike communicate(), this never accumulates arbitrary output in memory.
    proc=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,shell=False)
    result=[]
    def read_bounded():
        try:
            data=bytearray()
            while len(data)<1026:
                chunk=proc.stdout.read(1026-len(data))
                if not chunk: break
                data.extend(chunk)
            result.append(bytes(data))
        except Exception:
            result.append(None)
    thread=threading.Thread(target=read_bounded,daemon=True); thread.start()
    try:
        deadline=time.monotonic()+30
        while proc.poll() is None:
            if result and (result[0] is None or len(result[0])>1025): raise Refused('checker output refused')
            if time.monotonic()>=deadline: raise Refused('checker timeout')
            time.sleep(.02)
        proc.wait(timeout=5)
    except BaseException:
        try: proc.kill(); proc.wait(timeout=5)
        except Exception: pass
        raise
    finally:
        thread.join(timeout=5)
        if not thread.is_alive(): proc.stdout.close()
    if thread.is_alive() or not result or result[0] is None or len(result[0])>1025 or proc.returncode!=0:
        raise Refused('checker refused')
    return result[0]

def wait_startup_grace(child, overall_deadline):
    """Wait five seconds while the owned launcher is alive."""
    grace = 12.0 if overall_deadline - time.monotonic() >= 60.0 else 5.0
    target=time.monotonic()+grace
    if target>=overall_deadline: raise Refused('insufficient trial lifetime')
    while True:
        if child.poll() is not None: raise Refused('launcher exited during grace')
        now=time.monotonic()
        if now>=overall_deadline: raise Refused('trial lifetime elapsed')
        if now>=target: return
        time.sleep(min(.05,target-now))

def run(cfg):
    root,stop,lifetime=validate(cfg)
    receipt=root/'supervisor-checker.json'
    if os.path.lexists(receipt): raise Refused('checker receipt collision')
    with ExitStack() as stack:
        # Reserve every name before starting a child; an interrupted stage is empty.
        status={name:stack.enter_context((root/name).open('xb',buffering=0)) for name in ('supervisor-ready.json','supervisor-gate.json','supervisor-final.json')}
        writer,reader=stack.enter_context(capture.reserve(root,'supervisor-stdout.jsonl'))
        started=time.monotonic()
        child=subprocess.Popen([cfg['interpreter'],'-B',cfg['launcher'],cfg['profile'],cfg['profile_sha256']],stdin=subprocess.DEVNULL,stdout=writer,stderr=subprocess.DEVNULL,shell=False)
        ready=None; gate=False; phase='startup'; exited=False; creation=None
        try:
            creation=process_creation(child)
            ready=capture.wait_ready(reader,child,cfg['ready_timeout'])
            write_record(status['supervisor-ready.json'],{'schema':'supervisor-ready-v1','pid':child.pid,'creation_filetime':creation,'ready':ready})
            phase='startup_grace'
            wait_startup_grace(child,started+lifetime)
            phase='checker'
            output=checker_result([cfg['interpreter'],'-B',cfg['checker'],'--origin',ready['origin'],'--private-root',str(root),'--receipt',str(receipt)])
            if child.poll() is None:
                capture._check_directory(receipt.parent)
                info=receipt.lstat()
                if not stat.S_ISREG(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400 or info.st_nlink != 1:
                    raise Refused('checker receipt refused')
                with receipt.open('rb') as report:
                    recorded=report.read(1025)
                equivalent = output == recorded or (recorded.endswith(b'\n') and output == recorded[:-1] + b'\r\n')
                if equivalent:
                    gate=checker_pass(load_json(recorded))
            write_record(status['supervisor-gate.json'],{'schema':'supervisor-gate-v1','pid':child.pid,'creation_filetime':creation,'passed':bool(gate)})
            phase='waiting'
        except (Exception, KeyboardInterrupt, SystemExit):
            gate=False
        finally:
            stop_written=False
            if not gate:
                try:
                    request_stop(stop); stop_written=True
                except Exception:
                    pass
            # Never kill the owner of launcher cleanup. If it exceeds its bounded
            # lifetime, report pending; no claim that cleanup happened.
            try:
                child.wait(timeout=cfg['lifetime_timeout'])
                exited=child.poll() is not None
            except (KeyboardInterrupt, SystemExit):
                gate=False
                phase='interrupted'
                if not stop_written:
                    try:
                        request_stop(stop); stop_written=True
                    except Exception:
                        pass
                try:
                    child.wait(timeout=5)
                    exited=child.poll() is not None
                except (Exception, KeyboardInterrupt, SystemExit): exited=False
            except Exception:
                gate=False
                phase='wait_error'
                if not stop_written:
                    try:
                        request_stop(stop); stop_written=True
                    except Exception:
                        pass
                try:
                    child.wait(timeout=5)
                    exited=child.poll() is not None
                except (Exception, KeyboardInterrupt, SystemExit): exited=False
            write_record(status['supervisor-final.json'],{'schema':'supervisor-final-v1','pid':child.pid,'creation_filetime':creation,'phase':phase,'gate_observed':gate,'stop_written':stop_written,'launcher_exited':exited})
        return 0 if gate and exited else 1

def main():
    p=argparse.ArgumentParser(); p.add_argument('config'); p.add_argument('config_sha256'); a=p.parse_args()
    try:
        hash_file(a.config,a.config_sha256,16384)
        with open(a.config,'rb') as f: data=f.read(16385)
        return run(load_json(data))
    except Exception:
        print('supervisor refused',file=sys.stderr); return 1

if __name__=='__main__': raise SystemExit(main())
