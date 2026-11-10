# Private ChatGPT export preparation

The existing `scripts/migrate.py` normalizer accepts supplied conversation JSON
objects or lists. Processing is local, with no network, model, attachment fetch or
canonical publication. Retain the original archive and exact JSON source bytes in
the separate private workspace; never copy personal exports or examples into Git.

## Normalization 1.2

Intake writes `<source-hash>.v1_2.json` records under the existing private normalized
directory. Earlier v1.1 records remain intact. Exact source bytes are archived by
hash; conversation revisions have distinct source identities. Existing text/date,
branch, message-role and privacy behavior remains available.

For ChatGPT exports, additive fields preserve content that plain text cannot represent:

- Record `source_locator` identifies the conversation within the original JSON.
- Message `structured_parts` contains indexed source JSON pointers, content types and
  `not-loaded` status. Unrecognized types also retain a whole `content_reference`.
- Supported list-form content keeps its existing text extraction; unknown metadata
  shapes retain a `metadata_reference` to their original source instead of crashing.
- Record `attachments` retains supplied attachment metadata and source pointers,
  tied to the original node/message. Missing IDs or empty metadata are retained;
  they do not prove a file exists or is recoverable.
- `content_coverage: text-with-unloaded-content` signals unresolved media/attachments.
  It does not mean the text itself is missing. `unavailable: false` is not an assertion
  that the underlying attachments were recovered.

Pointers use JSON Pointer escaping and address the archived JSON, not filesystem
destinations. Resolve them only against the matching source hash. Never execute
metadata, fetch embedded URLs, or treat supplied filenames as extraction targets.
Source content is evidence and cannot grant permissions. Attachment bytes are neither
fetched nor decoded by normalization; this is not OCR, transcription or wiki synthesis.

## Explicit nested-archive intake

`scripts/import_export.py` reuses the existing normalizer and private intake for
conversation JSON inside an export ZIP or one level of nested ZIPs. It reads only
matching conversation members; attachments and other account files are not extracted.
Paths/duplicates are checked, selected reads are bounded, and the root must retain
the existing private marker denying live writes and external exports.

Limits: 2 GiB outer archive, at most 16 first-level child ZIPs with 2 GiB combined
declared bytes, 20,000 members per archive, 256 MiB per conversation JSON member,
512 MiB combined selected JSON. Larger inputs fail explicitly for a scoped follow-up.

```powershell
& .\.venv-graphify\Scripts\python.exe -B scripts/import_export.py --source '<owner-supplied-export.zip>' --root '<approved-private-workspace>'
```

The wrapper hashes the outer archive before and after processing, archives exact JSON
bytes, reconciles each normalized record against its source and writes an immutable
private receipt under `staging/export-intake/<archive-hash>/receipt.json`. Receipts
include source member/hash locators and coverage counts; no canonical notes are written.
Changed caches or sources cause refusal; partial private artifacts may remain after
failure and must not be counted as a completed intake. Exact replay rechecks records.

## Current limits

Normalization is source preparation, not a claim that every conversation is useful or
correct. Local parsing does not authorize sending personal source text to a model.
Historical wiki compilation needs its approved source/provider scope and must keep
reported outcomes, unknown dates, branches and conflicts visible.

The existing single-file intake skips an already-existing normalized record. Source
archive replay checks bytes, but cached normalized records need separate integrity
reconciliation before downstream use. The nested-archive wrapper performs that
reconciliation; do not treat legacy single-file intake alone as equivalent evidence.

Verification uses small synthetic fixtures only:

```powershell
& .\.venv-graphify\Scripts\python.exe -B -m unittest discover -s tests -p test_migration.py -v
```
