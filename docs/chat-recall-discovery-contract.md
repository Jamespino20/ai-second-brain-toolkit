# Chat recall discovery-only bootstrap contract

Date: 2026-11-05. Status: SOURCE REVIEW PENDING; NO NETWORK ACTIVATION.
Parent: [recall specification](chat-recall-spec.md). Existing transport contract
and its three source/test files remain frozen. This additive source slice does
not change the approved corpus, OAuth flow or reader enforcement.

## Reason and boundary

[OpenAI authentication](https://developers.openai.com/plugins/build/auth) says to
copy the exact callback from the MCP management page. [Connection setup](https://developers.openai.com/plugins/deploy/connect-chatgpt)
begins with a reachable endpoint. Neither establishes that the callback is visible
before authenticated tool discovery. A metadata-only experiment is a hypothesis,
not a proven way around this ordering. Do not invent a callback or relax OAuth.

Implementer owns only scripts/chat_recall_discovery.py and
tests/test_chat_recall_discovery.py after explicit contract release. Main owns
this contract and private proposals; independent reviewer is read-only. No edits
to existing runtime, dependencies, source/test freezes, skills, config or Git.
Use existing Starlette/uvicorn dependencies; no installation or paid/API requests.

## Source interface

An unstarted ASGI factory and explicit CLI accept only a trusted HTTPS origin
and loopback port. The origin must be one literal ASCII DNS label beneath
trycloudflare.com, without credentials, port, path, query or fragment; no wildcard.
Port must be a strict integer in 1-65535. CLI always binds 127.0.0.1, disables
access logging and proxy-header trust, and redacts configuration/runtime errors.
There is no grant, file, secret, client-ID or callback input. No reader, publisher,
fixture, external fetch, filesystem loader, token store or consent machinery.

GET /.well-known/oauth-protected-resource/mcp returns the fixed origin + /mcp
resource, authorization_servers containing exactly the origin and memory:read.
GET /.well-known/oauth-authorization-server returns exact issuer/origin, /authorize
and /token endpoint URLs, authorization_code/code, public-client none, S256 and
memory:read. No DCR, CIMD, refresh, RFC9207 or identity support is advertised.
These documents describe the intended authenticated backend; the bootstrap itself
cannot complete authorization and must be labelled discovery-only in responses.

/mcp always returns 401 with a Bearer resource_metadata challenge to the exact
protected-resource URL. It never initializes MCP, lists tools or executes a tool,
regardless of bearer/header/body contents. Only GET on the two metadata routes
succeeds. /authorize, /token, /consent and all other requests refuse without
redirect, echoed input, cookies, credentials, codes or tokens. HEAD/OPTIONS do not
silently open another capability. No request body is read, buffered or parsed.

Check exactly one Host matching fixed public host or the explicit loopback hosts
with the configured port. Reject duplicate Host/Origin, mismatched Origin and
path above 2048 bytes, query above 4096 bytes, headers above 16384 bytes total or
64 fields with bounded generic errors. HEAD /mcp returns 401 with an empty body;
other HEAD responses also have no body and never succeed as metadata GET. GET metadata
does not need Origin; when supplied, Origin must exactly match configured origin.
All HTTP responses are no-store, no-referrer, nosniff and deny framing. No request
queries, bodies or headers are logged. No remote callback/client auto-learning.

## Required source verification

Use real ASGI request/response tests, no listener or external endpoint calls.
Verify exact metadata/issuer/resource equality, the challenge, method/path/host/
origin/header/query limits and generic non-reflecting errors. Send initialize,
tools/list, tools/call, fake bearer, consent/token and large-body canaries: none
can succeed, redirect or issue credentials, and receive() is never consumed.
Check no imports of memory/publisher/data loaders. Mock CLI server configuration,
normal return and startup errors; prove loopback/access-log/proxy flags and no
unredacted output. Meaningful failing tests precede implementation. Freeze both
hashes after focused/full checks, then independent source/synthetic review.

## Future staged proposal, not authorized by this file

Only after source review: prepare an exact helper/runtime/recipient/time-limit/
cleanup proposal for owner approval. Stage 1 requires continuous exclusive
ownership of a loopback socket before tunnel provisioning, retained into the
chosen server without release/rebind. A closed port is not a reservation. Prove
the actual Windows socket/server protocol and a competing-bind refusal locally
before any execution request; do not assume Unix fd passing works on Windows.
The future orchestrator records the generated origin, validates/binds that exact
origin and starts only this metadata helper on the continuously owned socket.
Orchestrator source and native protocol proof are outside this two-file slice
and remain explicit pre-activation gates. Owner-operated Chat UI
checks predefined public-client support and exact callback before any Create,
connection or consent grant. If the UI requires those first, stop and report the
unmet prerequisite; no fallback, guessed callback or OAuth authorization attempt.

No personal or fictional note content is loaded/exposed in Stage 1. Public
metadata is accessible to anyone with the URL; Cloudflare relays/terminates TLS
and OpenAI fetches the metadata. They must be named recipients in the proposal.
Cloudflare's temporary free route has changing hostname, no SSE/uptime guarantee.
Keep the process stopped until approved; no paid domain/account/model API/trial.

Helper telemetry is a further pre-activation gate: upstream cloudflared 2026.10.7
[server startup](https://github.com/cloudflare/cloudflared/blob/2026.10.7/cmd/cloudflared/tunnel/cmd.go)
initializes Sentry, and its [entry point](https://github.com/cloudflare/cloudflared/blob/2026.10.7/cmd/cloudflared/main.go)
can capture errors/panics. This is source evidence, not a reproduced binary data
flow or proof of a disable setting. Before activation, prove telemetry is disabled
or review/name Sentry and diagnostic/device metadata in the exact owner recipient
proposal. Do not claim Cloudflare/OpenAI are the only possible recipients yet.

Capture only the public origin, owner-confirmed client/callback settings and
minimal status. No raw OAuth query, state, authorization code, token, cookie or
password capture. A changed tunnel hostname invalidates the binding and approval
record; stop instead of automatically reconfiguring. Stop only receipt-owned
helper processes, verify port/process exit and close the pending UI form without
changing existing connections. Stage 2 recall requires a separate exact active
profile review and owner consent. The discovery helper has no promotion switch.
