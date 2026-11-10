# Focused helper-output guard diagnostic

Date: 2026-11-05. The diagnostic retry recorded a guard rejection and a child
exit code 1 before cleanup. The rejected bytes and reason for exit are unknown;
neither observation establishes the cause of the other.

## Source-only change

After coordinated reviewer pause and explicit Main release, the implementer may
change only `scripts/run_chat_discovery.py`, `tests/test_run_chat_discovery.py`,
`scripts/run_chat_synthetic.py`, and `tests/test_run_chat_synthetic.py`. All other
files, profiles, past receipts and live configurations stay frozen.

Add a bounded, fixed classification at the existing `OutputGuard` failure sites:
startup total-byte limit, line limit, invalid candidate, candidate boundary and
changed origin. Specify whether the value is first-trigger or a finite set of
observed triggers, including null/unknown and synchronization semantics. Preserve
the exact existing accepted/rejected input behavior and output bounds. Do not
duplicate the parser. Never record candidate/line/URL/host/path text, raw helper
output, exception strings, credentials, tokens, queries or note content.

Include the classification in the synthetic launcher's detached, locked
pre-cleanup snapshot and bounded diagnostic receipt. Preserve child status timing,
all-null interrupted snapshot semantics, owner cleanup, exclusive listener hold,
ready behavior and create-only receipts. Existing source and receipt remain evidence
of their original runs; no classification can recover earlier missing output.

Test every failure category, simultaneous/multiple failures, split chunks, valid
origin and unrelated documentation URLs, EOF without newline, changed origin,
output caps and secret/path/query canaries. Prove original accept/reject behavior
unchanged on the same cases. Exercise pre-cleanup snapshot versus a late pump update,
child pre/post cleanup, interrupt, socket and owner cleanup, and existing fictional
OAuth/recall regression suites. Tests use fake streams/children and local-only
fixtures; no real helper or relay. Use the exact previously verified toolkit venv
interpreter, qualify skips and simulated signals, freeze four hashes and request an
independent source/local review. A category narrows a future guard trigger; it does
not establish why the helper exited or guarantee future interoperability.

No live retry, new tunnel, Chat connection, credential use, canonical access,
configuration change or Git action is authorized by this source-only slice. A
future exact package and separate owner approval precede another external attempt.
