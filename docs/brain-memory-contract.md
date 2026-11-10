# Shared save and recall contract

Status: T01 source contract frozen and peer-reviewed; create-only integration received
fresh independent scoped GO on 2026-11-02. This document and
the inert policy example grant no live access. Existing staging and fixed-note reader
contracts keep their current meaning. All integration fixtures contain synthetic data.

## Ownership and compatibility

A owns publication/knowledge helpers and tests. B owns managed recall/MCP helpers and
tests, and later the existing adapter/skill integration. Neither edits the other's
files without acknowledged transfer. Shared source schemas change only through a
written contract revision. Keep references/, projects/, permanent/ and logs/ intact.

`brain-save-context-v1` remains the same five-field packet: schema, role, coverage,
items, artifacts. Roles, eight-item limit, provenance classifications and current-
context limitations are unchanged. Models cannot supply a policy, filesystem root,
destination path, grant, manifest pointer or new permission through this packet.

No publication configuration means the existing staging CLI/result remains unchanged.
A configured publisher adds a `publication` result; it must preserve the actual staged
receipt even when publication refuses or only partially commits. Never count staged
proposals as saved notes. Existing immutable source/candidate records remain intact.

## Local publication interface

Proposed Python entry point:

```python
publish_staged(private_root, staged_receipt, policy_path, policy_sha256) -> dict
```

Arguments are fixed by the local host configuration except the receipt returned by
the existing stage operation. Treat that receipt as untrusted until the persisted
receipt, archived source hash, candidate bytes and reconstructed candidate agree.
Accept a duplicate-stage result too: a prior staging operation may not have published.
Never import arbitrary private files from model-supplied receipt fields.

`brain-publication-policy-v1` is private, independently hash-pinned configuration.
Required fields and their types are shown in the inert example. It defines the exact
vault root, owner authorization, create prefixes, exact update enrollments, bootstrap
operations, local-read scope, optional receipt metadata and capacity limits. Invalid,
revoked, changed or disabled policy cannot mutate the canonical vault. Keep the
existing private marker denying live writes/external exports unchanged; this separate
policy is the authority for a future narrowly activated publisher.

T03 creates a managed session note only. T05 adds enrolled-section updates/recovery;
T07 adds project/lesson routing, deduplication, links and permitted indexes/logs.
Unsupported requested operations must refuse rather than imply an implemented feature.
Governance/bootstrap files have exact separately approved paths and payload hashes;
ordinary create prefixes never authorize governance, settings, raw exports or deletion.

Derive the transaction ID from the immutable staged source, candidate and policy
hashes. Claim a vault-wide publisher lock atomically in private staging. BUSY permits
one identical retry; a stale lock is not permission to delete it. Journal intended
targets/hashes and recoverable preimages before mutation. Install flushed temporary
files on the target filesystem without clobbering a concurrent new file. Verify final
bytes before recording success or enrolling a note for recall. Existing-note exclusion
requires independent editor/process probes in T05; hash-then-replace alone is insufficient.

Multi-file publication is recoverable, not globally atomic. Incomplete work remains
explicit and private; recovery cannot overwrite later edits. Retain transaction and
source identity across retries. A successful receipt replays as NO_CHANGE with zero
new mutations, after checking actual state. Same intent with inconsistent bytes refuses.

Publication result, including all zero-valued counters:

```json
{
  "schema": "brain-publication-result-v1",
  "status": "SAVED",
  "transaction_id": "<stable opaque digest>",
  "counts": {"saved": 1, "updated": 0, "linked": 0, "skipped": 0, "quarantined": 0},
  "error_code": null,
  "sync_status": "UNVERIFIED"
}
```

Statuses: SAVED, NO_CHANGE, PARTIAL, QUARANTINED, DISABLED, REFUSED, BUSY. Counters
are integers; error_code is null or a safe code, and transaction_id is null when no
publication intent is attempted (disabled policy or empty capture). Otherwise it is
the stable digest.
Counters
describe actual committed work. Unsafe independent items may be withheld; dependent
changes must be withheld too. No hidden global rollback or false zero-write failure.
Model-facing results contain no paths/titles/excerpts unless explicitly permitted.
Use stable safe error codes, never raw exceptions or source bodies. Direct helpers
raise ValueError for invalid configuration/input; CLI/MCP boundaries redact exceptions.
CLI adapters use nonzero exit for REFUSED/BUSY/PARTIAL/QUARANTINED and retain receipts.
Local publication always reports sync UNVERIFIED; T12 records cloud proof separately.

Canonical metadata preserves privacy, source locators, roles, dates, uncertainty and
external_processing:false. Mark automatic validation as policy-validated, never human-
reviewed. Candidate validation/rendering stays staging-only; do not relax it for writes.

## Committed managed-note manifest

After verified writes, publish an immutable private manifest and atomically advance
`publications/<policy_id>/managed/latest.json` under the configured private root.
Manifest filenames use the manifest-content hash; transaction identity remains
inside the manifest. A recovered transaction can therefore enroll against a later
generation after another capture commits, retaining abandoned generations intact.
The pointer is {"manifest": "<relative-generation-file>", "sha256": "<file-hash>"}.
Resolve its relative path only beneath that fixed managed directory, with link/path
checks. Unmanaged existing notes are never enrolled from a matching prefix alone.

```json
{
  "schema": "brain-managed-manifest-v1",
  "policy_id": "<policy-id>",
  "policy_sha256": "<approved-policy-hash>",
  "generation": 1,
  "transaction_id": "<committed-transaction>",
  "notes": [{"id": "<stable-note-id>", "path": "logs/brain-save/project/note.md",
             "sha256": "<verified-note-hash>", "size": 123,
             "privacy": "personal", "external_processing": false,
             "source_references": ["<source-reference>"]}]
}
```

Note paths are canonical-root-relative POSIX Markdown paths, unique case-insensitively.
IDs are unique and stable across updates. Preserve full source/role/session provenance
in notes/private receipts. A model cannot add entries or refresh hashes. A grant to the
managed corpus is an explicit new standing-scope policy, not a relaxation of legacy
fixed-hash grants. Policy/manifest pins are integrity checks, not OS isolation against
an unrestricted same-account process; no hostile-process security is claimed.

## Scoped managed recall

B provides these Python helpers and an optional read-only stdio MCP adapter:

```python
search_managed(grant_path, grant_sha256, client, query, limit=4) -> dict
read_managed(grant_path, grant_sha256, client, note_id, start_line=1, line_count=20) -> dict
```

The fixed private grant has schema `brain-managed-read-grant-v1`; fields:
`client` (codex-openai, chatgpt-openai or claude-anthropic), `source_kind` (synthetic or
canonical), `root`, `private_root`, `policy_path`, `policy_sha256`, `manifest_pointer`, `prefixes`
(approved managed-note subtrees), `note_ids` (additional exact approved managed IDs),
and `owner_authorization` with state, reference, purpose and
personal_content_external_model_approved. Startup supplies an independent grant hash
and matching client. Root and pointer must match the pinned policy and exact
`<private_root>/publications/<policy_id>/managed/latest.json` location. Private-root
path/marker checks remain applicable; no grant weakens that marker. An entry is
eligible only when its path matches a granted prefix or its ID
is explicitly granted; all entries still require trusted publisher enrollment.
At least one nonempty, safe prefix or exact note ID is required; an empty scope is
never shorthand for all notes. Paths, titles and source references returned in recall
are part of the named client's approved read scope; publication's model_output flags
apply separately to publication receipts.

Canonical mode needs explicit personal-content processing consent for that named
client/purpose, including its metadata and source references. Synthetic mode requires
a disposable test-vault root and synthetic privacy markers; it must reject personal
notes. Publisher integration tests may exercise canonical mode against entirely
synthetic temporary fixtures carrying personal labels, as existing reader tests do;
that does not activate live grants or authorize redirecting a synthetic client profile.
Historical E03 packet approval is current-session compilation only, not a recall grant.

Reuse existing checked_path, lexical-search and citation conventions where practical.
Legacy selected_memory.py and its two read-only tools retain their exact authority.
The new reader requires policy.enabled to be true and policy owner authorization to
be approved with a nonempty reference, in addition to the named client's approved
read grant. Revoking/disabling this policy blocks managed recall too. To stop capture
publication while retaining authorized recall, disable the publisher invocation in
host settings without modifying the approved policy. No absent/disabled policy
implicitly grants reads.

The new reader checks grant/policy hashes and authorization before notes, validates
eligible note paths/sizes/hashes before any excerpt, and refuses stale/missing notes.
Read the pointer again and recheck grant/policy pins before returning. Any change in
the full pointer identity (raw bytes, manifest path or hash), grant or policy causes
refusal/retry, even if the generation number is unchanged. No mixed generations.
Within one reader process, track the highest validated generation per grant/policy
identity; reject a lower generation or a different manifest identity at that same
generation. Protect this check/update for concurrent calls, after final pin validation.
Do not claim persistent rollback protection across process restarts: the configured
private pointer is trusted at startup, within the documented same-account boundary.
No link traversal or whole-vault discovery.

Bounds: query 1-300 characters, 1-4 results; reads 1-40 lines and at most 8,000
characters; 128,000 bytes per note; configured maximum 256 managed notes. Validate
citations too: at most eight source references per note, 512 characters each and
2,048 characters combined. Overflow refuses rather than truncating provenance.
Validate
argument types strictly, including booleans passed as integers. Search output keeps
query, selected_note_count and matches with note_id, path/relative_path, sha256,
source_references, line, excerpt and score. Read output keeps note identity/citations,
start_line, end_line and numbered lines. Add mode `managed-read-only-markdown` and
manifest_generation. Empty authorized searches return no matches; scope errors return
no excerpt. Model arguments cannot choose paths or broaden any startup setting.

The new MCP adapter advertises exactly search_managed_memory and read_managed_memory
with read-only/non-destructive annotations. Startup environment names are
SECOND_BRAIN_MANAGED_GRANT, SECOND_BRAIN_MANAGED_GRANT_SHA256 and
SECOND_BRAIN_MANAGED_CLIENT. No grant/policy/root path is a model tool argument.

## Checkpoints

Freeze these schemas for A/B parallel implementation after independent read-only
review. Tests cover meaningful observable behavior, tampering, limits and replay.
One-time live activation still needs concrete owner-approved write/bootstrap and
provider/read scope, independent GO and a recoverable pilot. Runtime source to installed
skill updates preserve local settings. Publication, recall, client access and OneDrive
cloud sync must each demonstrate their own result before being called working.
