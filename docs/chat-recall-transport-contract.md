# Synthetic Chat recall transport contract

Date: 2026-11-05. Parent: owner-approved [chat-recall](chat-recall-spec.md).
Status: SOURCE PROTOTYPE ONLY. No network helper, tunnel, key, plugin connection,
canonical profile, grant expansion or personal-data processing is activated.

## Decision and cost evidence

Prototype candidate: existing local managed reader + stateless JSON Streamable
HTTP + a small single-owner OAuth authorization server, suitable for a future
explicitly approved temporary Cloudflare Quick Tunnel test. The public tunnel
will NOT start in this source slice. The server binds loopback only when started.

[Cloudflare's command reference](https://developers.cloudflare.com/workers/wrangler/commands/tunnel/#tunnel-quick-start)
explicitly calls Quick Tunnels free and account-free. This establishes the stated
price of a temporary development tunnel, not production uptime or a permanent
free endpoint. No paid domain, API model, hosting plan or trial is required by the
prototype. Do not install/run cloudflared or Wrangler in this slice.

[Limitations](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/):
no SSE, changing hostname, no uptime guarantee; email-PIN authentication does not
support non-interactive clients. Do not use that PIN gate for Chat MCP traffic.

[OpenAI authentication](https://developers.openai.com/plugins/build/auth) requires
OAuth code + S256 PKCE, exact callback allowlisting, resource audience and scope.
Chat cannot present an arbitrary custom API key. OAuth here means an explicit
single-owner consent/access-code flow, not fabricated identity or a public demo
that automatically grants tokens. No external identity service is introduced.

Cloudflare would relay request/response data and terminate public TLS in a future
test; it is an additional data recipient. Source work does not authorize that
transmission. A frozen synthetic fixture, runtime, account and disable proposal
must be reviewed before any external test. Personal notes remain excluded. The
OpenAI Secure MCP Tunnel alternative remains unselected because its exact account
cost is unverified; Main observed an accessible Personal Tunnels page with no
existing tunnels, without creating one. No inference from UI availability to cost.

## Ownership and immutable boundaries

Implementer: only scripts/chat_recall_oauth.py, scripts/chat_recall_http.py and
tests/test_chat_recall_http.py. Main owns this contract, task/spec docs and private
handoffs. Reviewer owns independent read-only source/synthetic review after hashes
are frozen. Existing source, runtime, dependencies, installed skills and config
remain untouched, especially the frozen historical importer/tests. No Git action.
Use relevant implementation, TDD, security and source-driven skills.

## Trusted configuration and synthetic restriction

Provide a factory for local ASGI testing and an explicit CLI starter. Trusted
configuration fixes grant path/hash/client, HTTPS public base, exact Chat callback
URI and the generated high-entropy owner access-code reference. Tool arguments
never choose these. Use the pinned installed MCP 2.3.0 dependency closure.

This prototype MUST reject grants whose source_kind is not synthetic, and only
use grants rooted in an existing test-vault under the reader's synthetic rules.
Reject canonical grants before serving; do not touch a live grant to test this.
Reuse managed_memory search_managed/read_managed under captured trusted settings,
not copied policy checks or a new corpus scanner. Exactly two tools, same narrow
schemas and read-only annotations. No save, arbitrary path/command or network tool.
Do not expose secrets, local config, raw input or exception details in errors/logs.
All settings/key material/fixtures/evidence remain outside the repository.

The owner access code is a cryptographically random, at least 256-bit pilot secret
provided privately by the operator, never a real account password or hardcoded
credential. Do not print it, accept it in a URL/query, include it in a package or
store it in a public profile. Validate bounded secret input and use constant-time
comparison. Secret generation/entry is outside this source slice's CLI execution.

## OAuth and HTTP requirements

- Use SDK OAuth/PKCE handlers and AuthSettings; explicitly enable resource/audience
  checking. A token lookup is authoritative only for tokens minted by this process.
- Permit only authorization_code with S256 and public-client token auth none in
  the prototype; no M2M, JWT bearer or refresh flow. Bound registrations and states.
- Client registration must have exactly the operator-pinned HTTPS Chat redirect,
  required scope memory:read and supported grant/response/auth methods. No wildcard
  redirects, remote metadata fetching, user-selected issuer or arbitrary client URL.
- The pinned callback must be copied from a real future connector management page;
  tests use synthetic callback values. If implementing RFC9207 stable callbacks,
  advertise issuer identification correctly and return exact iss; otherwise use
  only the exact callback-specific Chat URI. Do not invent a production callback ID.
- Authorization creates a bounded, expiring random consent ticket. A separate owner
  form/consent step checks the pilot secret, exact Origin, client, scope, resource,
  redirect and PKCE binding before minting a short-lived single-use code. Require
  CSRF protection and prohibit framing/caching. GET alone never issues a code/token.
- Invalid secret attempts are rate-limited with bounded state. Do not leak whether
  a secret partially matched. No open redirect and no browser credentials collected.
- Bind codes and tokens to client, exact redirect, issuer, resource and scope.
  Code exchange is one-time under concurrent requests. Reject expiry, replay,
  wrong client/audience/scope, code verifier and redirects. SDK defaults are not
  assumed safe: demonstrate them in real endpoint tests. Bound all dictionaries.
- Access tokens are high-entropy opaque values with short lifetimes and no refresh
  token; stop/restart clears them. Verify owner identity, scope, issuer/audience and
  expiry on each request. Secret/token values never appear in server logs.
- Use JSON response mode and stateless HTTP. Do not depend on SSE subscriptions or
  unprotected origin access. Keep SDK Host/Origin checks; allow only the configured
  HTTPS host and required loopback test hosts. Do not trust forwarded headers to
  construct redirects or grant identity. CLI always binds 127.0.0.1.
- Enforce bounded request sizes including OAuth forms/registration. Reject oversized
  and malformed inputs without echoing their values. Authentication precedes tools.
- On managed refusal return redacted MANAGED_RECALL_REFUSED and stop. Do not turn
  refusal into an empty success or retry against another transport/profile.

## Required synthetic verification

Meaningful TDD with installed SDK/ASGI or real loopback clients; no paid model calls:

1. OAuth discovery/protected metadata and exactly two tools; unauthenticated MCP
   cannot list/call tools. Authentic full code+S256 flow permits search/read of a
   fixture with expected ID/hash/lines and unchanged pre/post file bytes.
2. GET/unauthorized consent gives no code; wrong secret, CSRF/Origin, forged ticket,
   expiry, cross-client, redirect, scope/resource, replay and bad/plain/missing PKCE
   refuse. Show single-use code exchange under concurrent requests.
3. Wrong/expired token, wrong audience/scope/owner and cross-account attempts fail;
   bounded exhaustion refuses; no secret/input/path canaries in responses/logs.
4. Reject canonical grant with mocked/synthetic metadata only; no actual live access.
   Denied-note canaries, changed pin, disabled grant, oversized requests, unknown IDs,
   and reader window/character limits refuse without config/fixture mutation.
5. JSON-only response path needs no SSE session; validate cleanup on errors and
   handler shutdown, and no source/config/canonical modifications.

Freeze all new file SHA-256 values after focused tests, then hand off for independent
review before changing frozen bytes. Correct required findings under coordinated
release/refreeze. Source/synthetic PASS alone never means Chat/Tunnel is connected.

## After the source slice

Main prepares a concrete, reviewed synthetic activation/recipient proposal only if
source review passes. A future tunnel/connector needs owner confirmation at the
actual access-grant step and a fresh regular Chat synthetic tool proof. Canonical
Chat access is a further exact scope/profile review; this prototype cannot enable
it. T13b saving and T05 updates remain disabled/unimplemented here.

## Review clarifications incorporated before source release

Reviewer and implementer identified SDK and protocol defaults that this slice must
not inherit silently. The following requirements take precedence over ambiguous
wording above; parent acceptance gates are retained rather than marked complete.

Use a single predefined public OAuth client with an operator-pinned client ID and
exact callback in the first slice. No public DCR, CIMD fetching or refresh endpoint
is needed. The official Chat authentication documentation supports predefined
clients. Whether the target connector UI accepts this exact public-client profile
is still an external synthetic test gate, not a claim from source or documentation.
Metadata must advertise only auth-code, response type code, token auth none and
S256, with no unsupported refresh/secret-auth/registration capabilities. Explicitly
require code_challenge_method=S256 at the HTTP boundary; reject missing, plain or
duplicate/ambiguous OAuth security parameters. SDK defaults are not evidence.

Prefer the exact callback-ID-specific URI copied from a future connector page;
synthetic tests use a fixed test callback. Do not advertise RFC9207 issuer response
support or use a stable production callback unless implemented on every successful
AND error authorization redirect, with exact equality of AS metadata issuer,
protected-resource authorization_servers and returned iss. Test all those cases
if this optional mode is implemented. No callback wildcard or fabricated real ID.

Enforce body limits while receiving ASGI chunks, independently of absent, false,
chunked or misleading Content-Length, before an unbounded buffer/form/JSON parse.
Test bounded 413/refusal and cleanup for auth, consent, token and MCP endpoints.
Consent tickets and authorization codes are each atomically single-use under
concurrent POST/exchange; only one can succeed. Bound expiry and all state stores.

Do not log access URLs, OAuth queries, request bodies, tickets, authorization codes,
owner secrets or bearer tokens. Consent responses set Referrer-Policy no-referrer,
Cache-Control no-store and CSP frame-ancestors none; no query-string owner secret.
Only protocol-required code/state redirect values may leave via the exact allowed
callback. SDK request/exception rendering must not echo input or secret canaries.

Identity proof is deliberately qualified: the local pilot proves possession of an
operator-supplied high-entropy access code and binds the issued grant to its exact
OAuth client/resource. It does NOT attest which real ChatGPT account is signed in.
Tests distinguish unapproved client/no-owner-credential from genuine remote-account
isolation. Real account/profile association remains unproved and live canonical
activation is prohibited in this synthetic-only prototype. Do not lower the parent
account-access gate or imply that redirect+PKCE alone authenticates a ChatGPT user.
