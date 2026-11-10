# Synthetic Chat startup diagnostics

Date: 2026-11-05. Source/local synthetic work only. The first approved trial
exited before ready with a null recorded origin; cleanup was reported complete.
Its cause is unknown because helper output and the relevant branch were not saved.
Do not infer that the helper failed, emitted no origin, or never contacted a relay.

## Scope and ownership

After independent reviewer pause/release, implementer may modify only
`scripts/run_chat_synthetic.py` and `tests/test_run_chat_synthetic.py` under Main's
explicit release. Keep HTTP/OAuth, discovery launcher, reader, profiles and prior
receipts frozen. Main owns this contract, package and task documents; reviewer
independently checks exact frozen source and test hashes. No real helper, relay,
Chat connection, canonical data, credential access, config or Git work in this slice.

## Diagnostic contract

Extend the create-only final receipt with a bounded structured diagnostic object.
Use fixed allowlisted phase and reason values, elapsed monotonic time in bounded
numeric form, and booleans for the observed guard failure, recognized origin,
stream EOF and stream-read error when actually known. Unknown must remain unknown;
never infer observations from cleanup. Distinguish child status observed before
launcher termination from any status observed after termination. Only an actual
bounded integer exit code or null is permitted; never put arbitrary child output,
exceptions, paths, request URLs, OAuth data, code, tokens or note text into the
diagnostic. Keep receipt, stderr and ready output redacted and size bounded.

Define and document every enum, null case and transition in the implementation
handoff. If failure happens before intent/receipt can be created, keep failure
closed and do not manufacture a receipt. Preserve create-only collision behavior,
the exact approved profile and runtime security checks, all source capability
boundaries, one validated origin, startup/lifetime deadlines, ready semantics,
owner-state invalidation, exclusive socket ownership and supervised cleanup hold.
The previously approved first-run evidence is immutable and is never rewritten.

## Synthetic verification

Use disposable fixtures, fake streams/children and local-only tests. Demonstrate
the intended fields for child exit before origin, live child with guard rejection,
stream read exception and EOF without newline; verify split chunks, long output,
invalid/changed origin, interrupt, timeout and startup failure. Check that actual
pre-termination child status is distinct from launcher-induced termination and that
failure before origin never constructs the authenticated app. Exercise canaries
for credentials, paths, URLs, queries and raw output in the receipt/stderr/ready.
Retain coverage of socket hold, owner cleanup, record collisions, fixed fixture
closure and five-line fictional recall. Skip unsupported native behavior honestly.

Run the focused launcher suite and relevant HTTP/discovery regression suites using
the previously verified toolkit `.venv-graphify/Scripts/python.exe -B`. Freeze both
files, document exact hashes, tests, schema/limits and independent review. A PASS
proves only local diagnostic behavior, not the cause of the past attempt or live
interoperability. A new external attempt needs a concrete reviewed proposal and
separate owner approval; do not auto-retry or reuse consumed records.
