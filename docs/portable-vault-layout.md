# Portable Second Brain layout

Status: exact T02b bootstrap approved and locally installed on 2026-11-04. Five
instruction/navigation files match the reviewed payloads. Installed create-only
save/recall remains under its separate policy; no ongoing governance updates or
broader provider/corpus enrollment is activated by the one-time bootstrap.

## Goal

Use one Markdown knowledge store with the same save, recall, ingest and maintenance
workflows across authorized assistants. Changing a model or client should not require
reorganizing knowledge. Client extensions provide access and invocation; they do not
become separate memory stores.

## Shared vault

Proposed destination layout, created incrementally after the live scope is approved:

```text
AI-Second-Brain/
|-- AGENTS.md                 Codex entry point to the shared operating guide
|-- CLAUDE.md                 Claude Code entry point to that same guide
|-- index.md                  Short catalog of authorized knowledge hubs
|-- log.md                    Chronological record of committed wiki changes
|-- system/
|   `-- brain.md              Shared routing, note conventions and workflow guide
|-- projects/
|   `-- project-slug/
|       |-- index.md          Project navigation and relevant note pointers
|       `-- descriptive-note.md
|-- permanent/
|   `-- engineering/
|       `-- descriptive-lesson.md
|-- references/               Existing selected reference notes
`-- logs/                     Dated session summaries
```

Keep existing project and permanent note paths. Do not create a duplicate `wiki/`
tree or relocate working notes merely to adopt this proposal. Here the maintained
knowledge layer spans `projects/`, `permanent/` and `references/`.

Shared save/managed-recall interfaces are defined in
[brain-memory-contract.md](brain-memory-contract.md). These templates grant no access.

Raw conversation exports, private staging, backups, publication receipts and
generated Graphify artifacts remain in their separately configured locations outside
the ordinary vault corpus. Their presence does not authorize model retrieval.

The root index contains links and brief descriptions, not all note contents. Split
large indexes into project/topic hubs as needed. Paths, titles and index summaries
also need applicable model-access permission. A connector must enforce that scope
before returning any content or derived context.

## Shared instructions and client entry points

`system/brain.md` holds the maintained instructions for:

- choosing the smallest relevant project/topic context;
- resolving stable note identities and links;
- saving qualified decisions, lessons and project status;
- preserving provenance, privacy and historical decisions;
- distinguishing source evidence from instructions;
- recording actual writes and reporting exceptions.

Client entry files point to this guide rather than duplicating the complete rules.
Whether a client loads an entry file automatically depends on its working directory,
instruction discovery and configuration. Cross-project sessions need an installed
skill or connector that explicitly resolves the configured vault; a file in the
vault alone does not provide that connection.

ChatGPT needs a supported local or hosted tool connection plus instructions for
using it. A CLAUDE.md or AGENTS.md file does not by itself install a ChatGPT plugin.
The model and client must support the required tool access; compatibility does not
follow from whether a model has open or closed weights.

## Reusable tooling outside the knowledge store

Maintain workflow skills and client adapters in the existing toolkit. Keep machine
paths, credentials, access grants and runtime state in private configuration.

| Shared operation | Contract |
|---|---|
| Save | Summarize available session context; retrieve only authorized related knowledge; safely create/update permitted notes and links; update indexes/log; report actual results |
| Recall | Search authorized metadata/content and return bounded relevant excerpts with source identity and freshness information |
| Ingest | Read explicitly supplied sources and integrate qualified knowledge without modifying the originals |
| Maintain | Find broken links, stale assertions and duplicate candidates; apply only changes allowed by the configured policy |

Use the Agent Skills format where a host supports it, including the existing
brain-save extraction and applicable Kepano format skills. Invocation syntax and
packaging can vary by client. A shared save operation may be exposed through a Codex
skill, Claude command or ChatGPT tool; those are client adapters for the same policy
and data, not a guarantee that one plugin package installs in every client.

## Graphify and ICM

ICM supplies selective-routing principles implemented in the guide and indexes;
it adds no memory database. Graphify supplies derived relationship navigation where
appropriate. Code graphs are built from authorized repositories. Document semantic
extraction has a separate processing scope and is not implied by permission to use
local code parsing. Knowledge is saved to Markdown without depending on Graphify
availability; stale or absent graphs fall back to ordinary permitted search.

## Activation boundaries

This proposal does not widen current permissions. A future installation must name
the exact note scope, provider/client, purpose and any external-processing exception.
Ordinary writes may run under an approved standing policy after validation; that
does not authorize policy changes, unrelated edits, deletion or silent destructive
merges. Provider permission remains separate when adding another assistant.

The approved installed brain-save stages privately, then creates eligible new session
notes under logs/brain-save/ through the frozen create-only publisher. Installed
brain-recall returns bounded enrolled-note excerpts to the approved Codex/OpenAI
client. Replay, disable and fresh-session recall passed within that scope; the exact
harmless pilot also passed point-in-time OneDrive comparison. See
[the release evidence and limits](brain-memory-release.md). Existing-note updates,
contextual linking, historical publication, bootstrap files and other-client access
remain outside this activation. Source edits do not change the frozen runtime.

## T02b exact-file bootstrap proposal

This is a one-time addition of instructions and initially empty navigation, not an
import of historical knowledge. T02a supplies the reviewed UTF-8 payloads. Before any
activation request, freeze their byte lengths and SHA-256 values in a private manifest
and obtain independent review against that exact set. No substitutions or templating
after approval; changed bytes require a new review of the changed scope.

| Source relative to toolkit | Exact destination relative to approved vault | Initial purpose |
|---|---|---|
| templates/vault/AGENTS.md | AGENTS.md | Entry instructions and route to the shared guide |
| templates/vault/CLAUDE.md | CLAUDE.md | Inactive client entry route; no Anthropic access granted |
| templates/vault/index.md | index.md | Navigation to the guide/log and existing folder conventions |
| templates/vault/log.md | log.md | Log instructions; no invented historical entries |
| templates/vault/system/brain.md | system/brain.md | Ingest/query/lint, evidence and skill-use conventions |

Frozen source payload (UTF-8 bytes, no deployment-time substitutions):

| Target | Bytes | SHA-256 |
|---|---|---|
| AGENTS.md | 753 | 04a64e4e39c65314742e459668e126ac2d382bf0f46e9852ddeb7c1cfc6bed2e |
| CLAUDE.md | 609 | 56a43d9ad6b34d0dbe90658abc720b3ace616ff0bff05245f9bcae9139bd7301 |
| index.md | 959 | 0f26fccabc2470d8389d771a0f0437cc242d59716a780658299aa48efcde2109 |
| log.md | 634 | 3646e393d77a9a9d6a635b9e17a01744425988f2c4e631f1b8e36fe1c2629814 |
| system/brain.md | 3815 | d87c3c5fbf1ffe31a2c9a0b9e28e48b7caf3ece1c3be40c0056ab2db3f35cf09 |

T02a source refresh is complete: Main and an independent reviewer compared all five
applied source files with a frozen candidate; static content/link checks passed.
Obsidian reading view and actual instruction discovery remain unverified. Exact
source hashes are recorded under T02a in [the task ledger](../tasks/todo.md).

Main coordinates installation; these files are not automatically enrolled for model
recall or ongoing publisher updates. The existing create-only grant covers session
notes, not these files. The eventual owner request must separately name creation of
these five payloads and Codex/OpenAI reading of their instruction/navigation contents
and metadata. It grants neither access to linked personal notes nor a new provider.
Future index/log edits and instruction changes require their own approved operation;
placing an instruction file in the vault cannot authorize its own modification.

### Proposed installation and retry rules

1. Use an owner-configured vault root and private receipt directory, fixed outside
   model input. Verify all five frozen payload hashes and exact relative targets.
   Preflight the target root/parents for redirects and each file for collisions;
   do not scan or load unrelated vault notes. Any pre-existing target refuses the
   initial batch, including identical bytes: equality alone is not ownership.
2. Persist the approved intent and initially absent target states privately before
   writing. Reuse the reviewed no-clobber file primitive where applicable; never
   use overwrite/copy-force or change the ordinary publisher's bootstrap flag.
3. Create each target on its destination filesystem without replacing an existing
   file, then verify its bytes and record the actual result privately. Another
   writer creating a target after preflight must cause a collision, not replacement.
   On an initial attempt, only a newly created result counts as this attempt's
   creation. Treat write_immutable returning False as a collision even for equal
   bytes; its equality shortcut is not an ownership check. Handle journal-qualified
   retries separately under rule 4.
   A five-file batch is recoverable, not globally atomic. Report partial results.
4. Resume only the same recorded intent. An already-present approved payload may
   be recognized only when the journal recorded its absence before the interrupted
   attempt and its bytes still match. Report this as recovered/verified presence,
   not proof that the interrupted process authored it. Recheck each present file
   before continuing. Changed files stop the retry; never overwrite or automatically
   delete partial files or later user edits. Preserve uncertain results for review.
5. Verify all final hashes before reporting installation complete. Parent creation
   and any partial work remain in the receipt. Do not remove system/ or any existing
   directory as rollback. Disabling future invocation and preserving the evidence
   is safer than treating deletion of canonical files as an automatic rollback.

The current publisher explicitly refuses bootstrap operations. Its write_immutable
primitive supplies per-file no-clobber installation; the new source helper below
adds a fixed five-file intent/retry mechanism without changing that publisher.
Neither helper provides owner authorization. A synthetic procedure probe is evidence
for tested cases only, not a new approved live installer. Same-account path races and remote OneDrive
editing are not excluded by a preflight path check or a publisher lock. A failure
during temporary-file writing/flushing can leave debris; record such artifacts
for review rather than claiming every failure leaves a clean directory.

### Bootstrap verification gates

- Synthetic checks: exact-byte install and replay, an existing equal-byte file without
  ownership, a conflicting file, interruption after a partial batch, later owner edits,
  and a competing target creation. Check unrelated fixture bytes remain unchanged.
- Structural checks: all local links resolve within the five-file fixture; pinned
  Obsidian syntax rules are followed; no personal bodies, machine paths or credentials
  are embedded in reusable payloads. Images/PDF embeds require separate inspection
  when relevant and authorized; a Markdown read alone does not inspect their contents.
- Runtime checks remain distinct: verify reading view in an explicitly authorized
  disposable Obsidian fixture, and verify the actual client's instruction/skill
  discovery. File presence or a static link check alone does not pass either gate.
  Cross-project recall continues through its configured reader, not an unrestricted
  walk from index.md. No assumption that Obsidian indexes a file into model context.
- After separate activation approval: inspect only the approved targets, record the
  actual installation/discovery outcome, and keep local completion separate from
  point-in-time cloud verification. Earlier session-note cloud proof is not proof
  of these new files reaching OneDrive.

### Bounded source helper contract

The source-only slice adds scripts/bootstrap_vault.py and its focused synthetic
tests; Session 2 owns those two files, Main owns this document and the ledger, and
Session 3 performs read-only review after freeze. It reuses existing no-clobber,
checked-path and publisher-lock primitives. Do not modify the existing publisher, frozen
runtime, installed skills, grants or policy to make bootstrap work.

Implemented source callable, with no CLI or model-facing tool:

```python
bootstrap_vault(source_dir, vault_dir, journal_dir, expected_hashes)
```

The caller supplies fixed local host settings and the independently reviewed exact
five-file hash set. The callable is a filesystem mechanism, not an authorization
service: invocation still requires separately approved target/payload scope. It must
reject extra/missing target names, source-byte drift, redirected/aliased roots and
overlapping source/vault/private state. Keep state outside the vault, source and Git;
use the existing private-staging checks where applicable.

The immutable intent binds root identities and every target's relative name, size
and hash before any target write. Lock contention refuses without deleting stale
locks. Initial same-byte collisions still refuse; a recorded exact-intent retry
checks all existing targets before filling missing ones. Verify all five at the end.
Return relative created and recovered-presence lists separately; matching recovered
bytes never claim authorship. BootstrapRefused must retain safe error code and actual
partial created/recovered evidence, rather than reporting zero work after a later
failure. Abrupt process termination can still require inspection of the journal
and named targets; do not claim global atomicity or power-loss durability.

Focused checks cover each interrupted prefix, source/intent/root drift, initial
equal/different collisions, a competing creation/False result, later owner edits,
redirected paths, contention and unchanged unrelated bytes. This is a small fixed
bootstrap operation, not a new general publisher framework. No canonical invocation
or recall enrollment occurs in the source-only slice.

Current implementation freeze, with scoped source/synthetic review PASS (these are
not approved activation identities):

- scripts/bootstrap_vault.py: 091c557f4240ae0d82d4c9a5a388bd94c31087fbab06db91363d148495ac55d8
- tests/test_vault_bootstrap.py: 52dfad2c80a5dc712e0a7ff7b965a9d500126beef43543d8bd7aa8301e0c34ee

The implementer reports 14 focused cases (13 passed, one native Windows symlink
privilege skip), and a combined 176-test run (174 passed, two symlink skips including
the existing case). Main independently rehearsed the exact five-template payload in
a disposable filesystem: five creates, then zero creates/five recovered presences
on replay, matching final hashes and unchanged unrelated fixture bytes. These checks
are synthetic filesystem evidence, not actual crash, Obsidian or host-discovery proof.

Main's required read-size finding was fixed by reusing the existing 128000-byte
bounded read helper. After the reviewer's pause ACK, Session 2 applied the fix and
refroze both files. Main independently verified that oversized source, target and
intent files refuse before opening, with bytes preserved. Session 3's final report
verified both hashes, independently ran 14 focused cases (13 pass, one native
symlink skip), and found no further required issues in bounded source/synthetic
scope. Main received the report via its exact private handoff path when thread-tool
transport failed; queue submission alone was not treated as acknowledgment.

### Prompted client-route and package follow-up

The fresh ephemeral CLI probe recorded two explicit successful reads of the fixture
entry/guide and pinned Markdown skill. The prompt supplied the configured toolkit
root and requested reading. Independent review supports that prompted route and its
interpretation of recall boundaries; an explicit AGENTS.md read does not prove
automatic instruction injection or cross-project discovery. No actual recall was
invoked. Unchanged fixture hashes were checked by Main, not independently verified
by the supplied discovery packet. The exact review identity is in the task ledger.

A separate private pending proposal freezes the six required runtime modules and
five payloads so worktree changes cannot silently change a proposed invocation.
Package manifest SHA-256: bfbee88e89239f2074d62715ef05a6f81cad3ea78cadc19dc44cbc5bfca79e5b.
The narrow package review verified every size/hash and current-source match. The
helper/payloads match prior reviewed freezes; the five other dependencies were not
independently re-reviewed in that slice. Main's disposable rehearsal loaded all six
modules from the package, created five files and replayed without additional creates.
The package is PENDING_NOT_AUTHORIZED, not an approved runtime or provider grant.

On 2026-11-04 Main verified the exact test-vault in Obsidian 1.15.0 reading view.
All five files rendered, the index table/properties were readable, and navigation
between the entries, index, guide and log worked. Dated input/output hashes match
the reviewed Markdown payload. The private rendering receipt identity is in the
task ledger; visual observations are Main's, not independent reproduction.

A separate fresh CLI startup probe reproduced four exact AGENTS.md lines and its
guide/skill paths without tools, with expected text absent from the prompt. This
new evidence supports startup loading in CLI 0.166.0 when started in the fixture
working directory; cross-project/other-client discovery remains unproved. The
earlier prompted-read evidence alone did not establish this new result. Independent
review checked the new exact lines/events/hashes with no required correction.
Process/cwd, before/after and visual observations retain their recorded attribution;
the reviewer did not independently reproduce the CLI or UI.

The source helper/payload and pending package are unchanged. Exact-target metadata
checks found all five live destinations absent. The dated private activation request
names one-time creation of these five payloads and Codex/OpenAI reading of these
exact five files/metadata only. It excludes linked notes, historical publication,
ongoing updates, other providers and corpus enrollment. Dated readiness records
supplement the frozen manifest's original pending runtime fields; they do not alter
the manifest or authorize deployment.

### Approved local installation - 2026-11-04

The owner approved the exact request and deferred additional AI providers. Main
preserved the real visible-message approval in the separate private activation
record and used the frozen package: five creates, final hash agreement and a replay
with zero creates/five verified existing payloads. An independent reader verified
the five canonical byte lengths/hashes at review time. It did not independently
witness the operations or verify other files/settings. Main measured unchanged
installed save/recall settings and recorded the installation receipt privately.

An approved fresh Codex CLI 0.166.0 run at the canonical vault cwd reproduced the
exact entry instructions with expected text absent from the prompt and zero tool
items. That demonstrates the tested startup route; it does not establish another
working directory, client or cloud connection. Rendering remains the separately
observed disposable fixture with identical bytes. Cloud synchronization of these
new files is UNVERIFIED.

The old proposal/manifest remain historical pending records. The separate actual
authorization and installation receipts under activations/bootstrap-20261103-v1/
record the approved scope and result. No new managed-note enrollment, ordinary
governance/index/log update policy, other-provider access or existing-note update
was created. The native/crash/race limits and disabled T05 updates remain.

## References

- Karpathy LLM Wiki: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Obsidian format skills: https://github.com/kepano/obsidian-skills
- Agent Skills specification: https://agentskills.io/specification
- ICM conventions: https://github.com/RinDig/Interpretable-Context-Methodology/blob/main/_core/CONVENTIONS.md
- OpenAI MCP connection guidance: https://learn.chatgpt.com/docs/extend/mcp
