# Metadata discovery launcher: source contract

Date: 2026-11-05. Status: SOURCE REVIEW PENDING; NOT ACTIVATION AUTHORITY.
Depends on reviewed [discovery-only helper](chat-recall-discovery-contract.md).
Implementer owns only scripts/run_chat_discovery.py and
tests/test_run_chat_discovery.py after Main release; earlier source stays frozen.
Main owns docs/private approval proposals; reviewer is read-only. No new packages,
canonical/config/skill/Git actions, real cloudflared launch or remote test in this
source slice. Local synthetic socket/subprocess tests are allowed explicitly here.

## Exact bounded launch interface

CLI accepts an absolute private manifest path and its separately supplied SHA-256,
no command strings or arbitrary network targets. Read <=65536 bytes through regular,
nonredirected paths; strict JSON rejects duplicate keys. Require exact schema,
state approved, scope metadata-discovery-only, nonempty owner reference, additional
spend limit zero, lifetime in 1-900 seconds, startup timeout in 1-60 seconds and
recipients exactly Cloudflare, OpenAI and Sentry. Approval is a Main-attested owner
record, not cryptographic proof of identity. Reject pending/disabled/malformed
profiles before binding or starting a child. No notes, grant, callback, client ID,
owner code, token or personal-content exception is accepted by this launcher.

The private manifest pins its runtime directory, exactly run_chat_discovery.py and
chat_recall_discovery.py, helper executable/hash and a private YAML file whose
exact bytes are `{}` plus newline. All are regular nonredirected paths under one
explicit private root, outside any .git ancestor. Verify exact source/helper/config
hashes before use. Reader/publisher modules must never be imported. No shell=True,
service install, login, named tunnel, update, paid model/API, certificate or account
operation. Neither config, binary, source nor approval is modified by execution.

Start the launcher only through the reviewed package/interpreter boundary. Its
self-hash is a consistency check, not authentication of Python code already run.
Keep top-level imports to standard library; verify discovery bytes before loading
that module. Existing uvicorn is imported only after profile checks. Path/hash
preflights do not provide adversarial same-account check/use isolation or prove
the entire interpreter trustworthy. No process-crash exclusion guarantee follows.

Bind IPv4 127.0.0.1:0 with SO_EXCLUSIVEADDRUSE set BEFORE bind on native Windows;
listen and retain the root socket until the exact child has been reaped. Refuse
unsupported platforms, existing ownership conflicts or failed socket operations.
Use socket.dup() in the same process with installed Uvicorn's run(sockets=[dup]);
never release/rebind or assume Unix fd passing. Native preliminary probe is private
socket-probe-v1/probe-v2.py, but actual launcher proof remains mandatory.

Launch only the pinned executable as an owned Popen child, with argument vector:
`tunnel --no-autoupdate --no-prechecks --config <pinned-empty-yaml>
--metrics 127.0.0.1:0 --management-diagnostics=false --loglevel info
--protocol http2 --url http://127.0.0.1:<held-port>`.
Use a minimal child environment containing SystemRoot/WINDIR plus private TEMP/TMP;
do not inherit TUNNEL_*, proxy, tracing, access-token or unrelated credentials.
No user/global environment or home configuration changes. Persist no raw logs.

Drain child output continuously with line/total startup bounds (4096/65536 bytes)
and startup deadline. Accept exactly one literal HTTPS origin of the helper's
trycloudflare.com shape; no arbitrary URL, callback learning or URL normalization.
Keep raw output only transiently and drop it; receipt records origin and minimal
status, not queries/headers/tokens. Before any ASGI service, validate exact origin
and configure the frozen discovery factory. No serving with a placeholder origin.
No unknown input can turn this into a recall/publisher service.

Continue bounded draining/discarding after startup so a full pipe cannot stall
the child. A second origin differing from the first stops the session; do not
retain log text or auto-rebind. No first origin by startup deadline also stops.

Run Uvicorn in a controlled thread using a duplicate of the continuously retained
root socket, with loopback, access_log false, proxy_headers false and generic
critical logging. Monitor child exit, server failure, owner interrupt and lifetime.
On any stop/error, stop/reap only the owned child BEFORE releasing the root socket;
stop/join the server and close its duplicate too. Terminate then bounded kill/wait
is allowed only through that exact Popen ownership, never broad process names or
stale PIDs. If child stop cannot be confirmed, retain the port and report cleanup
blocked rather than freeing a potentially forwarded target. No automatic restart,
hostname rebinding, scope promotion or existing host-config rollback.

Cleanup-blocked behavior is an explicit hold-open/manual-intervention state: keep
the root socket and launcher alive, report minimal child/server identity privately
and wait for confirmed child exit and server-thread completion. The nominal
lifetime bounds forwarding, not an unsafe process exit during failed cleanup.
Do not return/exit and claim the socket is still retained. This is not proof of
cleanup after launcher process crash, power loss or forcible termination.

Use two explicit manifest paths under the private root: an immutable create-only
intent and a separate immutable create-only final receipt. Before any child, both
must be absent and the intent must be exclusively created with source/manifest/
helper pins and run identity. Do not infer crash durability from create-only or
an fsync call. Final receipt records generated origin, held port, child PID plus
creation evidence, start/end and cleanup status. No raw process output or secrets.
Write it only after cleanup is confirmed; a blocked session retains the intent
and held socket and reports the hold state without claiming completed cleanup.
Any collision/final write failure refuses, preserves existing bytes and stops
owned resources; no automatic adoption, replay or repair. A later execution needs
a new reviewed approval record. External URL cessation, Chat UI
behavior and account association still require separate authorized proof.

## Required tests and review

TDD: malformed/pending/tampered manifests, path redirects, source/helper/config
drift and unsupported platforms cause zero child launch. With disposable synthetic
fixtures only, test argument vector/minimal environment, startup output caps/timeouts,
invalid/changed/missing origin, child/server failure, interrupt/lifetime, receipt
collision and cleanup ordering. Use fake subprocess adapters where necessary;
never the real helper. Native Windows real independent subprocess bind attempts
must fail while the actual chosen server serves metadata and after it stops while
the parent root remains held; prove cleanup releases ownership after child exit.
Exercise error cleanup with a pre-created child/held socket, not only call counts.
Demonstrate fake helper output cannot promote to OAuth/tools. Preserve zero request
body consumption and metadata-only helper source pins.

Focused suite then one full regression; freeze both hashes for independent source
and synthetic review. Main independently rechecks focused behavior and one meaningful
mutation in private source copies. Source PASS does not permit a real helper run:
the exact inactive package, recipients, time bound, owner-operated UI stop conditions
and disable procedure must first be reviewed and approved by the owner.
