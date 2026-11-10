# Exact-byte historical import contract

Status: source implementation authorized, 2026-11-04. The owner approved the
four-stage contract/build/test/review plan. This contract elaborates that source
scope; it is not canonical activation or a personal-content read grant. Existing
save/recall policy, runtime, host configuration and T05 remain unchanged.

## Objective and scope

Import a small already reviewed set of Markdown notes without rewriting its
historical claims, evidence, candidate status or links. Success is exact-byte
create-only installation, truthful partial/retry results, a private managed manifest
compatible with the existing reader, and synthetic cited recall under a separate
explicit grant. No historical extraction or synthesis occurs in this importer.

The first real proposal will contain five separately reviewed notes, including
distinct nested navigation files. No existing root index/log or governance file
may be changed, adopted or enrolled. Real destination availability is not yet checked.

The approved first source slice is one historical batch per dedicated policy.
It neither aggregates corpora nor widens the active session-memory grant. A later
activation request must name exact payload, publication and citation/read scope.

## Files, stack and interface

- `scripts/publish_historical.py`: additive Python3.13 module; no CLI, network,
  watcher, environment discovery, model invocation or automatic grant creation.
- `tests/test_publish_historical.py`: unittest fixtures in temporary private roots
  and disposable `test-vault` roots. No actual pilot contents or live paths.
- This contract and existing plan/todo: Main-owned documentation.
- Reuse bounded reads, path checks, no-clobber install, cooperative publication
  lock and private pointer primitives from existing modules read-only. Do not call
  `commit_new`, `render_note`, or pretend historical content is a session capture.
- No dependency or existing source/runtime changes in this slice.

Public keyword interface:

```python
publish_historical(private_root, manifest_path, manifest_sha256,
                   policy_path, policy_sha256,
                   authorization_path, authorization_sha256)
```

A separate read-only `validate_historical` with the same arguments may share the
loader and return only sanitized status/count/IDs. It must not create directories,
journals, locks, pointers or receipts. Paths/pins come from an owner-controlled
invocation, never a Markdown instruction or model-exposed tool argument.

## Trusted pins and bounded inputs

The caller supplies trusted expected SHA-256 values for manifest, policy and
authorization. Files are local, non-hardlinked regular files under the marked
private root; roots are absolute, checked, nonredirected, disjoint and outside a
repository vault. The existing private marker remains restrictive. It is not a
publication authority. All reads, including retries, growing inputs and state,
are bounded through the existing reader, never `Path.read_bytes()` on untrusted
runtime input. JSON objects reject duplicate keys and unsupported shapes/types.
The existing `migrate.private_root` reads its marker unbounded; validate the same
private-root constraints with a bounded marker read here. Likewise strictly parse
policy JSON before relying on the existing permissive JSON policy loader. These
are local guards, not changes to existing helpers.

Limits: manifest/authorization/evidence/note/attempt records at most128000 bytes
each (policy32000, pointer4096); batch1-16 notes, evidence1-16 files, total note
bytes at most16*128000. Managed manifest at most1048576 bytes, at most256 notes.
Relative input paths are at most512 characters; marker/lock reads have small
explicit caps. Check serialized state limits before creating private records.
Journal may include the bounded batch identity/entries, not all note bodies.
Batch/entry IDs match `[A-Za-z0-9_-]{1,80}`; hashes are lowercase64hex; booleans
are booleans and sizes positive integers, not bools.

### Manifest: `brain-historical-import-v1`

Required fields: `schema`, `batch_id`, `client` (exactly `codex-openai` in v1),
`review_evidence`, `notes`. Each evidence item has private relative `path`, positive
`size`, `sha256`. Hash and size of every named evidence file are verified; do not
follow source locators, URLs, attachments or unlisted archive members.

Each note has exactly `id`, `source`, `path`, `sha256`, `size`, `privacy`,
`external_processing`, `source_references`. `source` is its private relative
Markdown payload; `path` is its intended vault-relative Markdown destination.
Privacy is `personal` or `synthetic`, external_processing is false. Citation refs
are1-8 nonempty strings, each at most512 chars and at most2048 combined, and match
the note's frontmatter `sources`. Citations can reveal locators, so they are part
of the explicit later read approval. Evidence hashes bind review artifacts; they
do not make their assertions independently true.

### Authorization: `brain-historical-import-authorization-v1`

Required fields: `schema`, `state`, `reference`, `purpose`, `client`, `batch_id`,
`manifest_sha256`, `policy_id`, `vault_root`. Execution requires `state=approved`,
nonempty reference/purpose, matching client/batch/manifest/policy and exact checked
vault root. This is a pinned owner-controlled receipt, not a generated consent claim.
It authorizes this local publication only; provider recall still needs its separate
grant and personal-content exception. Pending/revoked/mismatched receipts refuse.

### Dedicated policy

Use existing `brain-publication-policy-v1` validation with enabled/approved owner
authorization, limits and create prefixes. Require an additional `historical_import`
object with exactly `batch_id`, `client`, `manifest_sha256`, `authorization_sha256`,
matching this request. Policy owner reference must match authorization reference.
Do not alter/reuse the active session-memory policy or transplant a new policy hash
onto its old corpus. A disabled policy returns DISABLED without mutation.

## Payload, paths and links

Validate every source before any target mutation. Preserve exact UTF-8 bytes;
do not render, normalize, rewrite metadata, replace historical status or stamp
human review. Parse the existing JSON-compatible YAML frontmatter subset strictly:
unique simple keys and JSON values, id/privacy/external_processing matching the
manifest, `sources` matching citation refs. Other reviewed fields remain intact.
Restricted privacy or metadata disagreement refuses the whole batch.

Path components use conservative ASCII letters/digits/dot/underscore/hyphen,
start with a letter/digit, have no trailing dot/space, and reject Windows device
names (including before extensions), traversal, absolute paths, backslashes,
streams, controls, `.git`/`.obsidian`, aliases and case-insensitive duplicates.
Destination paths must have a directory and fit an approved create prefix. Refuse
`system/` and root governance/index/log files; never inspect unrelated vault notes.
Existing parents are checked without blindly resolving away redirection. Check
all target paths again at mutation boundaries. Hardlinks and redirected paths refuse.

The supported import dialect has explicit vault-root wikilinks, optional `.md`,
display aliases and a single exact heading fragment; same-note heading links are
allowed. Every internal target is in this exact batch and every heading exists.
No basename guessing, embeds, block links, unresolved/out-of-batch links, relative
Markdown file links or HTML resource loading. External hyperlinks are preserved
as text and never fetched. Fence/inline-code examples are not navigation links.
Unsupported link constructs refuse instead of guessing. This static gate supplements
the separate human/native rendering evidence, not a universal Markdown parser.

## Create, enrollment and retry protocol

1. Validate complete input/evidence/policy/authorization and all payload metadata,
   links, identities and capacity before target mutation. Under the existing vault
   publication lock recheck pins/state. BUSY does not publish or delete stale locks.
2. Deterministic transaction identity binds checked roots, all three trusted pins,
   batch, entries and evidence. Its private batch intent is immutable and written
   before targets. The first attempt requires every target absent, including equal
   unmanaged bytes. Initial intent-write collision is not ownership.
3. Before each target create, write a separate immutable per-note attempt record.
   No-clobber install must return True to count CREATED. After True and exact-byte
   verification, write a separate immutable positive installed record. Only this
   positive record can qualify file presence for automatic recovery. False/FileExistsError,
   including equal concurrent bytes, never counts as our write or gets enrolled;
   persist a collision/quarantine record when possible and stop the batch. No
   auto-renaming, adopting, merging, deleting, updating or silent fallback.
4. A retry requires the exact prior intent and consistent attempt/installed records.
   Only a prior attempted matching present target with a matching positive installed
   record may be RECOVERED_PRESENT (not continuous identity/ownership proof).
   An attempt without a positive installed record always refuses, even for matching
   bytes: crash between install and recording success trades availability for safety.
   Known collision/quarantine markers refuse retry. Missing or changed
   attempted/enrolled targets refuse: never recreate later owner-deleted notes.
   A missing unattempted target may be created; an existing unattempted target is a
   collision. Ambiguous post-write errors are PARTIAL/UNCERTAIN, never invented saved
   counts. Strict ambiguous-attempt refusal may need owner recovery even when a crash
   happened before file creation or after a successful install; document that tradeoff.
5. Verify all exact target bytes before adding entries. Publish one immutable
   compatible managed-manifest generation and replace only its private pointer,
   checking old pointer and all pins immediately before mutation. Validate prior
   manifest fields, unique IDs/casefolded paths, limits, privacy and source refs.
   Preserve valid existing entries; conflicting/intervening state may refuse but
   must never be overwritten or silently dropped. Prior enrolled data cannot be
   recreated just because a receipt is missing.
6. Recheck all target bytes and pins, then write a private immutable completion
   receipt. Exact completed replay is NO_CHANGE with no new generation or targets.
   Completion records bind transaction/pins, exact entries and the committed
   generation/manifest hash. Before replay, verify the current pointer and manifest
   against those recorded pins, and all positive installed records/target bytes.
   A journal-qualified pointer/receipt interruption may recover with zero new file
   creates. Source/evidence/auth/policy/intent/receipt drift fails closed. Do not
   delete canonical files or roll back owner edits to simulate an atomic batch.

The batch is not atomic across files. An interrupted attempt may leave some exact
files unenrolled, or enrollment may precede the final receipt. Report that honestly.
Local cooperative locks and pathname checks are not same-account isolation,
continuous editor exclusion, native crash durability or remote OneDrive exclusion.
Creating files does not make T05 updates safe. Private pointer replacement is not a
canonical existing-note write path. Cloud sync stays UNVERIFIED.

## Results and verification

Return structured sanitized status, transaction ID, per-note IDs/outcomes, counts,
generic error codes and `sync_status=UNVERIFIED`. Never emit bodies, absolute paths,
source text, authorization values or exception strings. Counts separate new saved
files from recovered presence, unchanged and not attempted; updated/linked stay0.
Statuses distinguish DISABLED, REFUSED, BUSY, COMPLETED, NO_CHANGE, PARTIAL and
QUARANTINED. Failure after any known mutation stays PARTIAL rather than claiming
zero effects. Failed receipt writing is not success.

```powershell
python -B -m unittest discover -s tests -p test_publish_historical.py -v
python -B -m unittest discover -s tests -v
```

Use RED/GREEN increments: (1) bounded pinned loader/abuse cases; (2) actual
create/replay and collision; (3) interruptions/recovery/enrollment and synthetic
existing-reader citations. Exercise wrong/missing/duplicate keys and pins, disabled/
revoked approvals, wrong provider/prefix/ID, duplicate/reserved/redirected paths,
oversized/growing source/target/intent/state, mismatched metadata and link headings,
equal unmanaged target, real independent-process competing creation, lock contention,
failures before/after intent/attempt/create/manifest/pointer/receipt, source drift,
owner edits/deletion and intervening private manifest changes. Verify unchanged
unrelated bytes, honest counts and no sensitive error canaries. Platform skips must
be explicit. Existing source full suite must remain green.

Freeze source/tests with hashes before independent review. First real proposal
remains PENDING_NOT_AUTHORIZED, with exact note/evidence/policy/authorization/read
grant/package pins, conditional activation and recovery instructions. Do not invoke
the importer on the canonical vault or change global MCP configuration in this slice.

## Primary references

- [Python3.13 os operations](https://docs.python.org/3.13/library/os.html): Windows
  rename refuses an existing destination; POSIX rename can replace it, so preserve
  the existing platform-specific no-clobber primitive. fsync is not a full system
  crash-durability claim.
- [Windows file naming](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file):
  conservative device-name, case and path handling.
- [Obsidian internal links](https://obsidian.md/help/links): explicit folder paths
  start at vault root and heading links select note sections.
