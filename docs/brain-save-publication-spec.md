# Specification: brain-save automatic publication

Status: DRAFT for owner review. This document grants no access and enables no writes.

## Objective

Complete the existing explicit brain-save workflow: summarize the current available
conversation, organize meaningful engineering knowledge, connect authorized related
notes, and save ordinary validated changes into the canonical Obsidian vault.
After one-time policy approval and activation, ordinary saves require no content
handoff or per-save approval. Sensitive, ambiguous or conflicting changes remain
private exceptions. This is one end-to-end save capability, not a new memory system.

The existing capture implementation stays in place. Obsidian Markdown remains
canonical; private evidence, recovery records and derived lookup data stay outside
both the repository and the canonical vault.

## Assumptions and exclusions

- Initial runtime: an existing interactive Codex session on one Windows machine.
- Preserve explicit-only invocation, available-context limitations, project/session/
  role identity, the eight-item limit and existing evidence classifications.
- Preserve v1 staging behavior for installations without an activated publish policy.
- The publisher adds no hooks, transcript discovery, second model session, database,
  embeddings or Graphify processing. The revised overall plan separately includes a
  recall skill and client adapters under the same bounded interfaces.
- No canonical-note text, excerpt or derived summary enters model context without
  separate applicable external-processing authorization.
- A successful local save does not establish OneDrive cloud synchronization.

## Existing implementation to reuse

- `skills/brain-save/`: explicit invocation and current-context extraction guidance.
- `scripts/save_interactive_memory.py`: packet validation, identity, artifact hashes,
  immutable evidence, scoped replay and candidate reconstruction.
- `scripts/capture_outcomes.py`: existing heuristic privacy filter.
- `scripts/migrate.py`: metadata conventions, hash/JSON helpers and draft formatting.
  Its staging-only root, candidate validator and renderer remain staging-only.
- `scripts/selected_memory.py`: applicable path-containment and redirection checks.
  Its hash-pinned external-model retrieval grants remain separate and unchanged.
- `scripts/run_codex_capture.py` and `scripts/backup.py`: reference patterns for
  locking, temporary replacement, integrity checks and restoration verification.
  They are not proof of canonical publication or concurrent-edit safety.
- `.agents/skills/obsidian-markdown/`: vendored wikilink/frontmatter references.

The shared implementation interface and recall boundary are defined in
[brain-memory-contract.md](brain-memory-contract.md). The inert policy example is
not an installed configuration or live grant. Preserve references/ in the existing vault.

Expected additions: a focused local publication helper, synthetic publication tests,
an inert policy example and updates to the existing skill/packet guide and brain-save
documentation. No new framework or service is required. Names and function boundaries
will be resolved during implementation planning.

## Publication policy

An owner-approved private policy must distinguish local reads, new-note creation,
managed updates and model-facing receipt metadata. A model packet cannot select a
vault root, widen scope, enroll arbitrary notes, enable publication or alter policy.
Missing, revoked, changed or invalid policy must prevent canonical writes.

Proposed initial scope, subject to owner approval:

| Operation | Proposed limit |
|---|---|
| New session records | `logs/brain-save/` |
| New project knowledge | Tool-managed notes under `projects/`, with a deterministic project identity namespace |
| New reusable lessons | Tool-managed notes under `permanent/engineering/` |
| Existing-note updates | Exact enrolled notes; managed sections only |
| Related-note local reads | Approved namespaces and exact selected existing notes; no implicit traversal through links |
| Model-facing output | Approved counts and safe status codes; note paths/titles only when specifically permitted |

Approval of a namespace rule should cover future ordinary projects within that rule;
new project creation must not introduce a registration handoff on every save.
Unmanaged existing notes are never adopted merely because their paths are in scope.
Governance files, raw histories, attachments, credentials and Obsidian settings are
excluded. The private staging marker continues to deny live writes; do not repurpose
or weaken it to activate the separate canonical publisher.

## Observable behavior

1. The user invokes brain-save in the current conversation. The skill extracts the
   existing bounded evidence packet and calls the local adapter once.
2. With publication inactive, existing staging behavior remains available. With an
   activated policy, validated staged evidence feeds the local publisher without a
   second model session or manual proposal handoff.
3. Ordinary engineering decisions, outcomes, lessons and next actions are routed to
   concise session/project/lesson records. Publication eligibility does not promote
   a reported result into independently verified completion.
4. The local helper resolves related notes only within its approved local-read scope.
   Use stable IDs, project identity and conservative topic matching. Add path-qualified
   wikilinks to validated targets. Ambiguous matches may be skipped without blocking
   a valid new note. Do not emit canonical-derived match text into tool output.
5. Preserve exact-source deduplication. Detect repeated normalized claims in the
   permitted destination and avoid repeating their prose, while retaining distinct
   session provenance. Do not silently merge merely similar assertions. Do not dedupe
   across privacy boundaries or collapse separate role/session evidence records.
6. Updates preserve unmanaged bytes and earlier dated assertions. Only an enrolled
   managed section and explicitly permitted metadata fields may change. Historical
   decisions survive; explicit supersession records describe replacements.
7. Ordinary supported assertions, qualified reports and clearly marked proposed next
   actions can publish. Suspected secrets, restricted/sensitive material, unsupported
   completion claims, contradictory changes and unsafe updates fail or quarantine.
   Privacy filtering remains heuristic; broad semantic contradiction detection is
   not claimed. Ambiguity never authorizes replacing an existing assertion.
8. Independent valid changes may complete when another item is quarantined. Changes
   that depend on a rejected item must also be withheld. Private receipts identify
   what actually committed, what was skipped and why.

Existing immutable candidates remain candidates. Canonical records must distinguish
automatic policy validation from human review; never label an automatic publication
as owner-reviewed. Preserve privacy, external-processing denial, timestamps, claim
evidence, source locators and coverage limitations in the resulting records.

## Atomic writes, recovery and OneDrive

- Serialize publisher operations across sessions without merging their identities.
- Before mutation, persist a private write-ahead record containing policy identity,
  intended targets, preimage hashes, recoverable preimage bytes and intended hashes.
- Recheck target/path safety and content preconditions before committing. A simple
  read-hash-then-replace sequence alone is insufficient concurrent-edit protection;
  validate the Windows exclusion strategy against an independent editor process.
- Use flushed temporary files on the destination filesystem and atomic per-file
  installation. New destinations must not clobber files created by another writer.
  Temporary artifacts must contain no broader content than the approved target.
- Re-read committed bytes before recording success. Multiple note replacements are
  recoverable transactions, not an assertion of filesystem-wide atomicity.
- Resume interrupted work only when journal and current hashes establish the safe
  next step. Otherwise quarantine. Recovery never overwrites a later user edit or
  deletes evidence to manufacture a successful receipt.
- Initial operation assumes one publishing machine and no concurrent edits to
  managed sections from another device. Detected sync conflicts, unavailable files,
  hydration failures or unexpected edits are exceptions; never force replacement.
  Local locks cannot guarantee protection against later remote OneDrive edits.
- Restore must be scoped to affected notes and conditioned on current hashes. The
  whole-vault backup helper must not run automatically with broader read access.

## Skill experience and implementation conventions

Keep the skill entrypoint short: summarize, call the adapter, report its result.
Put detailed packet/schema rules in the existing reference. Preserve
`allow_implicit_invocation: false`. Installation and any source-to-installed update
must preserve machine-local settings and be separately validated before activation.

Retain standard-library Python where practical, descriptive snake_case functions,
small helpers and safe error codes, consistent with the existing adapter:

```python
require(packet['coverage'] in {'visible-context', 'compacted-context'}, 'INVALID_COVERAGE')
```

The final user reply should state saved/updated/linked/skipped/quarantined counts.
No routine approval prompt follows a successful ordinary save. Actual result fields
and safe code names must be specified and tested during implementation; this draft
does not change the current CLI contract.

## Verification and success criteria

Use `unittest` with temporary synthetic vaults and private staging. Tests must prove
observable invariants, not merely match skill wording. No personal fixtures.

| Case | Required outcome |
|---|---|
| Ordinary project result and reusable lesson | One invocation creates appropriate notes, valid links and a truthful receipt without approval |
| Exact replay and repeated cross-session claim | No duplicate knowledge prose; distinct provenance and role/session records remain |
| Managed existing-note update | Unmanaged bytes, historical assertions and privacy metadata remain intact |
| Unauthorized paths, changed policy, redirection or hardlinks | No unauthorized read/export/write; safe refusal |
| Sensitive or unsupported item mixed with valid items | Unsafe material withheld; only independent eligible changes can commit |
| Matching against external-processing-denied notes | Local linking works; note text and derived excerpts/summaries never appear in model-facing output |
| Independent editor or competing publisher | No silent lost update; conflict is reported or quarantined |
| Crash at each journal/write/receipt boundary | Safe replay or explicit quarantine; no false success or overwrite of later edits |
| Unavailable file or simulated sync conflict | Canonical content is preserved; no forced hydration success claim |
| Disabled/revoked policy and legacy installation | No canonical writes; documented v1 staging behavior preserved where applicable |

Existing regression command, run from the toolkit repository:

```powershell
& .\.venv-graphify\Scripts\python.exe -B -m unittest discover -s tests -v
```

Validate the revised source skill with the installed skill-creator validator and
exercise the adapter end to end with a synthetic packet. Live activation requires
independent read-only GO plus owner approval of the concrete private policy and
installed capability. Synthetic tests do not establish real OneDrive synchronization.

## Boundaries and remaining owner decisions

Always preserve evidence distinctions, deny undeclared scope and retain recoverable
versions. Never silently delete canonical notes, rewrite governance, export denied
content, enable hooks, push Git changes or weaken existing retrieval grants.

The remaining product decisions are the exact publication/enrollment scope and
acceptance of the initial single-publishing-machine limitation. Approval to build
and test this specification is separate from authorization to activate live writes.
Implementation, independent review and repository actions retain their named-session
and authorization boundaries. No implementation or activation is authorized by the
presence of this draft.
