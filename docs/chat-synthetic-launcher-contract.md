# Stage 2: synthetic authenticated Chat connection launcher

Date: 2026-11-05. Parent: chat-recall-spec.md and the reviewed transport contract.
Owner requested preparation and independent review. This contract authorizes source
and local synthetic work only; it does not authorize a second external session.
No canonical content, new dependency, paid service, API model call or Git action.

## Goal and existing evidence

Prepare one bounded fictional-note connection trial for ordinary ChatGPT. Stage1
established Main-observed public callback visibility before Create, with user-defined
OAuth client and token endpoint auth none. Its artifact audit passed. The discovery
alert was recorded after expiry, so no active-time failure or cause is established.
The callback's stability is unknown. Keep those distinctions in all status reports.

Reuse the frozen synthetic-only chat_recall_http.py factory and OwnerOAuth, the
existing managed reader, installed pinned dependencies and the reviewed Windows
listener/process/output/cleanup primitives in run_chat_discovery.py. Preserve all
existing frozen files except the explicitly sequenced construction-cleanup fix
below. The new files are scripts/run_chat_synthetic.py and
tests/test_run_chat_synthetic.py, owned by Implementer. Main owns this document,
tasks and private package/profile/evidence. Reviewer is read-only after freeze.
Do not monkeypatch the discovery launcher to make an authenticated service.

Feasibility review found a concrete factory gap: after OwnerOAuth construction,
later app setup can raise before the caller obtains app.state.owner_cleanup.
Phase A therefore releases only scripts/chat_recall_http.py and
tests/test_chat_recall_http.py for construction-safe cleanup and a trusted optional
per-operation validation callback. Ensure
every successfully constructed owner is explicitly closed if subsequent factory
setup raises, including BaseException interruption, without changing auth/schema
behavior or catching/rewrapping interrupts as success. Do not claim memory zeroing.
Test injected setup failure after owner allocation, token/ticket invalidation and
idempotence; retain the existing pre-lifespan CLI and normal-shutdown regressions.
The trusted operation guard, when supplied by the new launcher, runs immediately
before each reader operation and again before returning its result. Refuse with
the existing redacted error if either validation fails; no partial result escapes.
It is not a profile/tool-selected callback or arbitrary code import. Default None
preserves existing standalone factory behavior. Test both pre- and post-operation
refusal and unchanged two-tool schemas. Do not modify the reader itself.
Freeze and independently review these two files before Phase B new launcher work.
Do not edit OAuth, discovery launcher, reader, importer or any other source.
Main explicitly releases each phase only after its preceding contract/review gate.

## Fixed profile and preflight

New explicit CLI: python -B scripts/run_chat_synthetic.py PROFILE_PATH PROFILE_SHA256.
The later executable package uses its own exact copied script path. No default
profile, environment credential or fallback. JSON is bounded to 65536 bytes, rejects
duplicates/unknown fields, and requires an approved synthetic-only state and owner
reference, zero additional USD, exact Cloudflare/OpenAI/Sentry recipients, lifetime
at most 900 seconds and startup at most 60 seconds. Pending input refuses before
listener/Popen. Define and document the final schema in the implementation handoff.

Pin the exact runtime closure, helper, empty configuration, fictional corpus and
its complete policy/grant/pointer/manifest closure by size and SHA256. Runtime
basenames are a fixed allowlist, not arbitrary module names. Validate containment
and regular nonredirected paths before content reads, including helper/runtime,
secret, grant and every nested reader reference. The first bounded manifest read
necessarily precedes knowledge of its private root; state that bootstrap limit.
No nested reference may cause an out-of-root read before refusal. Require all
inputs under the new private package root, outside Git; fixtures under test-vault.
Do not copy or inspect any canonical or installed host profile.

Installed-environment trust clarification: the private-root rule covers supplied
profile/runtime/helper/config/credential/fixture/evidence files, not Python itself,
its standard library or the already verified installed dependency environment.
Reuse that existing interpreter and pinned MCP/Uvicorn closure; no new environment,
dependency installation, vendoring or isolation mechanism is authorized here.
Main pins the exact interpreter and existing dependency verification evidence in
the later package. Python startup, site initialization and installed dependencies
are a trusted pre-launch boundary, not code that this launcher can retroactively
validate. State that limitation explicitly; do not claim a hermetic runtime,
protection against hostile startup hooks or same-account environment replacement.
The launcher still validates its supplied copied local runtime files before loading
them and before Popen, and must not resolve a supplied module from another path.
This does not permit fixture or profile references outside the private root.

Grant source_kind is synthetic, client is chatgpt-openai, exact permitted note IDs
and empty prefixes. Include at least one denied fictional canary. Allowed content
and all publication metadata are immutable fixtures, not publisher output. Reuse
reader validation; publication/enrollment code is never invoked. Runtime preflight
and receipt record the exact immutable input pins. Keep private paths out of repo.

Startup pins alone do not freeze the existing reader's current-generation lookup.
The launcher-provided operation guard must revalidate the exact immutable grant,
policy, pointer, manifest and all selected-note pins and nested containment before
the reader dereferences them and again before any result returns. A consistently
repinned later generation is drift and refuses, even if the same ID is enrolled.
Post-start nested-reference redirection must refuse before out-of-root content is
opened; post-read drift must not release a previously computed result. Test those
cases. Pre/post validation is not isolation from adversarial same-account TOCTOU;
the trial makes no such guarantee.

Predefine a nonsecret client ID, scope memory:read, exact callback-ID-specific HTTPS
ChatGPT callback and token auth none. Main will place the previously observed
callback in a pinned private profile. No wildcard, stable callback assumption,
DCR, CIMD fetch, refresh, callback learning or hot configuration changes. If the
new ChatGPT form's callback differs, owner stops before Create/consent; the trial
cannot use the mismatching callback. Stop and prepare a separately reviewed change.

The owner access code is a new cryptographically generated >=256-bit local pilot
credential. Supply it through a bounded pinned private regular file, never argv,
environment, stdout, general logs, source, public package or conversation. Do not
generate any secret during source tests except disposable canaries. Main creates
the real pilot file only as part of later approved activation. Operator provides
the file path to the owner; the owner opens/enters the code locally and manually.
Do not automate authentication dialogs or claim code possession proves account ID.

## Continuous lifecycle and cleanup

Reserve create-only intent before Popen; existing/partial intent, hold or final
records refuse, with no overwrite/retry. Retain one exclusive Windows loopback
socket continuously across the actual server lifetime. Start one exact pinned
helper with the previously reviewed flags, scrubbed environment and empty config.
Only one validated helper-derived trycloudflare HTTPS origin is accepted. Reuse
bounded streaming parsing; changed origin, malformed candidate, long output,
child exit, failed process identity or server failure stops the trial.

After origin discovery, construct the existing synthetic HTTP factory with fixed
grant/client/callback/code and actual origin/port. Use real Uvicorn on a duplicate
of the retained socket, no access/query/error-body logging and no proxy trust.
Do not expose memory before OAuth. Preserve audience, S256, CSRF, bounded body,
single-use ticket/code and redacted refusal behavior; do not weaken the wrapper
to accommodate unverified Chat behavior. Exactly its two read-only tools, no save.

Emit exactly one bounded flushed structured ready JSON containing only status
synthetic-only, validated origin and /mcp URL, after server.started, owned child
alive and output guard valid. Never include callback, code, token, query or note
content in ready/error output. Success requires that ready was actually emitted;
late startup without ready refuses. Overall lifetime includes helper startup.

On every exit, including app construction/pre-lifespan/startup failure, close the
OAuth owner state idempotently so issued tokens and tickets become invalid. Stop
and reap only the owned helper, then stop/join server before releasing root socket.
Cleanup-blocked retains supervision/socket and bounded create-only private owned
process/server identity evidence; no false final cleanup. Preserve GetProcessTimes
owned-handle identity, create-only final receipt and all v4 lifecycle guarantees.
Final receipt never stores secret/token/callback query/note content. No guaranteed
cleanup after forced kill/power loss, same-account hostile race or remote behavior.

## Required local verification and freeze

Use unittest with no real helper or remote calls. Full actual Python CLI subprocess
must use a fictional helper adapter and actual Uvicorn, observe ready while alive,
and exercise authenticated S256 search plus initial five-line read through the
actual socket, returning expected fictional ID/hash/lines. Preserve exact pre/post
fixture bytes. Unauthenticated tools and denied note cannot return canary content.
No test-only production hooks or sitecustomize dependency in the production CLI.
Document any adapter/preload used by the test rather than calling it production proof.

Test invalid/pending/drifted profile, canonical-shaped synthetic input rejection,
out-of-root runtime/helper/secret and nested reader-reference trap-open cases,
redirection/record collisions, secret/log canary exclusion and owner cleanup both
before and after lifespan. Exercise child/server failure, interrupt (qualify signal
simulation), startup deadline/no-ready interleaving, changed origin/output caps,
held listener, cleanup-blocked identity and final receipt collision. Reuse relevant
existing tests where they actually execute the shared function; do not count copied
test names as proof of the new integration. Skip unsupported native behavior honestly.

Focused: python -B -m unittest discover -s tests -p test_run_chat_synthetic.py -v.
Run existing transport and discovery-launcher focused suites for integration regressions.
Freeze both new hashes and handoff schemas/results/limits before independent review.
No edits to frozen files without coordinated release. No external invocation now.

## Subsequent activation proposal

After source/local review, Main prepares an inactive exact-byte package and an
owner-readable request: new hostname rule, pinned callback/client/fixture/runtime,
same three recipients plus fictional note/citation and OAuth traffic, >=256-bit
pilot code handled locally, $0/900s/60s, exact owner-operated Create/install/consent
steps, allowed bounded checks, disconnect/cleanup and failure behavior. Independent
package comparison precedes presenting that concrete access grant for approval.
No API Playground/billed calls, real-note promotion, other providers or save path.
Account UI observations remain separate from genuine other-account isolation proof.

Official sources checked 2026-11-05:
- https://developers.openai.com/plugins/build/auth (predefined client, exact callback,
  S256/resource enforcement; stable redirect needs full issuer-response semantics).
- https://developers.openai.com/plugins/deploy/connect-chatgpt (owner Create/install,
  fresh conversation and actual tool verification; UI availability is not proof).

This adds the missing launcher integration to the existing approved recall design;
it does not reopen its architecture or lower its canonical/account gates.
