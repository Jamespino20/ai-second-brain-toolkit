# Bounded public discovery checker

Date: 2026-11-05. Purpose: a reusable local tool that, if a future separately
approved fictional-only session is started, can distinguish common metadata-fetch
failure categories without retaining private request/response contents. The
completed local investigation did not identify the prior discovery failure.

Implementer owns only `scripts/check_chat_discovery.py` and
`tests/test_check_chat_discovery.py`; all existing source/tests stay frozen. Main
owns this contract and later package; reviewer checks exact hashes independently.
No production execution, public endpoint request, real helper, credentials,
canonical data, host config or Git action in this source/local test slice.

CLI receives a trusted validated HTTPS origin, explicit existing private root and
create-only receipt path strictly beneath that root; reject Git ancestors and
redirected root/path components before any write. Strict origin is one lowercase DNS label under trycloudflare.com,
with no credentials, ports, path, query or fragment. Output is a single redacted
bounded summary. Make exactly two GETs (authorization metadata and path-specific
protected-resource metadata) and one unauthenticated fictional POST to /mcp, with
no redirects, credentials, user input, cookies, bearer headers or raw notes. Fixed
timeouts and per-response byte cap apply before JSON parsing. The 401 challenge may
be inspected in memory for a matching metadata URL; record only presence and match
booleans, never its raw value. Check issuer/resource/authorization-server match,
S256 and token-auth-none as booleans; no response bodies or exception text stored.

Distinguish actual HTTP status/redirect from fixed error categories DNS, TLS,
timeout, connection, other and oversized/malformed; unknown must remain unknown.
Catch HTTPError before URLError; bound error data and do not follow redirects.
Record only the fixed path class, numeric status or null, error category and boolean
checks; do not persist origins/URLs, raw headers, payloads, queries, exception
strings, credentials or environment values. Receipt is create-only; refuse any
existing path and reject redirects/reparse paths before writing. No arbitrary request
path, method, headers, proxy, callback or content chosen through CLI. Tests may
inject a local fake transport; production CLI must not rely on test-only adapters.

Validate the private root and ancestors, then reserve the receipt with exclusive
create before any request or DNS dispatch. An existing receipt or invalid path
must cause zero transport calls. Flush the empty reservation to durable storage
before dispatch. Write bounded final JSON through the same owned handle; after a
crash an empty or partial receipt is incomplete evidence, never success, and must
not be overwritten or adopted. A later run needs a new explicitly authorized path.
This does not defend against hostile same-account path replacement.

Use direct connections without inherited environment/system proxy discovery,
proxy credentials, cookies or redirect following; test a hostile proxy environment
without contacting it. Keep TLS verification enabled. Per-socket timeout is at most
10 seconds; body cap is 16,384 bytes with one extra byte read before JSON parsing.
Limit an inspected challenge to 4,096 bytes, receipt to 8,192 bytes and console
summary to 1,024 bytes. Header parsing itself must have finite, enforced line/count
bounds before unbounded buffering; test oversized headers. At most three fixed
requests are permitted. Socket timeouts alone do not bound DNS resolution or the
whole-process wall time; do not claim a full deadline without a tested mechanism.

Local tests cover strict origin validation, successful synthetic metadata and 401,
401 missing/wrong challenge, HTTP errors versus URLError DNS/TLS/timeout/connection,
redirect refusal, malformed and oversized responses, timeout, fixed request count,
create-only collisions and canaries proving redaction. No real helper/network beyond
disposable loopback/fake transport. Use the exact verified toolkit venv, report
native limitations, freeze both hashes and request independent review. A pass does
not identify the earlier error or guarantee ChatGPT's request behavior.

No new external session is authorized. A later exact inactive package, recipient
scope, user consent and active-input review precede any actual public execution.
