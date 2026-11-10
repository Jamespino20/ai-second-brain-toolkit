# Second Brain sprint tasks

Status: active; implementation and checks are recorded below. See [plan.md](plan.md) for
policy, ownership, dependencies, safety limits and the revised 2-3 day schedule.
The brownfield baseline is 95 passing tests plus one documented skip; it is not
evidence that any new task below is complete. Proposed file names may be simplified.
New Main maintains this ledger after its 2026-11-03 ownership ACK. Historical A/B
labels below preserve attribution; new worker assignments await disjoint-path ACKs.

## Start here

Continuation 2026-11-03: the owner requested **AI Second Brain - New Main Terminal**
to take over. Read [handoff-new-main.md](handoff-new-main.md) and its private packet
before working. First reconcile schema/navigation deployment and recurring wiki
maintenance into this existing checklist; prepared templates are not a live wiki.
Establish acknowledged Main/Implementer/Reviewer ownership before parallel edits.

1. Source milestone: T01/T03/T06 and T08 source packages are implemented and frozen.
2. The owner approved the create-only scope; installed Codex save/recall is active.
   One harmless save, replay, disable and blind fresh CLI recall passed.
   The exact pilot cloud download and configured Personal account now match.
   Native Explorer status/availability also passed at that time.
   Next: use save/recall in real work; develop safe updates and meaningful links.
3. T05 updates, T07 contextual linking and other-client proof remain open.
   Earlier OneDrive pilot verification passed; ongoing synchronization is not guaranteed.
   E03's exact five-note historical pilot is now locally published/enrolled and recalled;
   native history-tool refresh was later completed through the supported app-server
   API; this batch's exact-five cloud bytes matched on 2026-11-05 (point-in-time only).

E00 is completed inspection only. E01/E02 and T02 have completion evidence below;
other tasks remain open until their own acceptance checks pass.
Original T01-T15 identifiers are preserved so existing handoffs remain valid.

### Remaining work in execution order (updated 2026-11-05)

- [x] T02a -> T02b: refresh source instructions/navigation and deploy the exact approved
      five-file bootstrap; dated local/cloud proof is recorded below.
- [x] E03: selected pilot fidelity, private reading-view, exact-five approved local
      publication and fresh CLI recall gates pass. E04 broader history remains open;
      current canonical read authority covers only its exact named-provider grant.
- [ ] T13a -> T13b: regular Chat recall, then create-only saving; first establish
      a supported authenticated connection with $0 additional charges.
- [ ] T05 -> T07: safe enrolled-section updates, meaningful links, conservative
      cross-session deduplication and recoverable managed index/log maintenance.
- [ ] T10 -> T11: independently review the new frozen scope and activate only after
      its approval; demonstrate the complete Codex wiki loop using existing T06/T08.
- [ ] T16: explicit repeatable wiki health checks and an approved repair workflow.
- [ ] T04/T09 -> T13: verify the actual ChatGPT host and prove its round trip;
      C01 separately authorizes/proves Claude or explicitly defers it.
- [ ] T15: reconcile final capability status/instructions; T14 Graphify is optional.
- [x] T17: one-repository installer and explicit private-state migration (scripts/install_toolkit.py, scripts/install.ps1, tests/test_installer.py).

Completed create-only save/recall and T12 point-in-time cloud evidence stay completed.
Top-level tasks that include wider wiki acceptance remain partial. Dated paragraphs
below record intermediate states; this summary and the latest follow-up supersede
earlier statements that installation or the exact pilot cloud check is still pending.

## E00: Check export structure and existing importer compatibility

- [x] Complete. Owner: current inspection session. Dependencies: none. Scope: S.

Acceptance:
- [x] Locate the supplied archive and inspect nested archive inventories locally.
- [x] Parse every conversation shard and exercise existing normalization in memory;
      report only aggregate results, without exposing bodies/titles or extracting files.
- [x] Identify the attachment/structured-part provenance gap and retain it as E01.

Verification: observed local Python zipfile/json preflight and migrate.normalize calls
completed with no normalization failures. No note synthesis, intake write, publication
or model-facing archive upload occurred. Detailed inventory/counts remain private.
Files touched: none.

## E01: Preserve attachment and structured-content references during normalization

- [x] Complete. Owner: A. Dependencies: E00. Estimate: 1-2 hours. Scope: M.

Acceptance:
- [x] Preserve attachment/structured-part locators, original conversation/node identity,
      dates and branch membership; mark unresolved/unavailable content explicitly.
- [x] Keep plain-text compatibility, private-output restrictions and exact-source
      integrity; normalization never fetches attachments or executes embedded content.
- [x] Existing consumers tolerate the versioned additive fields; no personal export
      samples enter repository fixtures or model context.

Verification: small synthetic fixtures reflecting the observed structures, including
text-only, multimodal, missing-attachment and branched cases. Run:
python -B -m unittest discover -s tests -p test_migration.py -v.
Likely files (3): scripts/migrate.py, tests/test_migration.py,
docs/export-intake.md. Freeze shared helper changes before B consumes them.

Result 2026-10-31: six new synthetic regressions were observed RED before their fixes;
16 focused migration tests pass. B's independent read-only review initially found
compatibility regressions, then issued scoped GO after fixes and independent probes.
Full integration suite at this point: 110 tests, 109 passed, one existing Windows
symlink skip. No canonical publication or source processing by a model was tested.

## E02: Stage the supplied history privately with recoverable provenance

- [x] Complete (private source intake). Owner: A. Dependencies: E01. Scope: M.

Acceptance:
- [x] Preserve the original export and record source/member hashes; normalize all
      supplied shards into the existing private workspace with per-source identities.
- [x] Reconcile conversation/node counts, duplicates, branches and attachment gaps;
      exact replay does not silently overwrite changed evidence or claim full fidelity.
- [x] Any archive reading/extraction is constrained to safe selected members and
      bounded sizes; no raw histories, attachments or inventory enter Git or the vault.

Verification: local source/hash/count reconciliation and a replay using private
receipts. Tests use small nested synthetic archives and unsafe-member names. Do not
mistake a parse success for verified knowledge or permission to send sources to a model.
Likely files (3): scripts/import_export.py if a wrapper is necessary,
tests/test_export_intake.py, docs/export-intake.md; runtime records stay private.

Result 2026-10-31: all supplied shards normalized privately; exact-source hashes and
cache reconciliation passed. A real replay verified unchanged bytes across the scoped
source/normalized/receipt files. B issued independent scoped GO, including a narrow
size-limit recheck after metadata showed the initial cap was too small. Eight new
synthetic intake tests pass; final full suite: 110 tests, 109 passed, one existing skip.
Receipt and coverage inventory remain private. No attachments were fetched/decoded,
no source text entered a model, and zero canonical notes were published.

### CE1: Reliable private source material

- [x] E01 regression passes; E02 source integrity/coverage report is recorded privately.

## E03: Compile a selected project batch into a private linked wiki pilot

- [x] Complete for the exact selected pilot. Owner: A/Main; independent fidelity,
      rendering and separately authorized fresh CLI recall evidence recorded.
      Dependencies: E02, T01/T02, approved source-processing scope.
      Estimate: 1-2 hours for a small initial batch. Scope: M.

Acceptance:
- [x] Choose one project/topic batch within the approved source/provider scope and
      create concise project, decision and lesson pages in private staging using the
      existing note conventions. Do not copy every conversation into a wiki page.
- [x] Notes have dated provenance, valid wikilinks, a small index/log and preserved
      uncertainty/history. Plans, user claims and assistant reports retain their status.
- [x] Selected sources are reconciled to generated notes or explicit skips; sensitive
      items and contradictions remain exceptions. This does not activate live publication.
- [x] Current Main and named OpenAI reviewer have exact private-processing approval;
      independent fidelity review covers all four claims and ten excerpt dispositions.
- [x] Derived preview preserves original evidence and resolves historical-status
      findings; all five note hashes/frontmatter and 18 link/heading targets checked.
- [x] Verify all five preview notes and representative navigation in Obsidian reading
      view through official CLI/URI; Main observed, independent artifact audit only.

Verification: independent checks of sampled claims against approved source locators,
link validation and an authorized fresh-session recall probe when the grant permits;
otherwise demonstrate recall with equivalent synthetic fixtures and mark live recall pending.
Likely repository changes: none by default; use existing formats and private packets.
Any necessary reusable helper must be separately scoped, small and tested with synthetic data.

Result 2026-10-31: the owner explicitly approved the exact selected packet for the
current OpenAI conversation. The immutable proposal remains unchanged; a separate
private authorization receipt records the bounded exception. Five candidate Markdown
notes were compiled, with four qualified claims and 18 verified internal links.
All ten excerpts are accounted for: four integrated and six skipped with reasons.
Candidate schema, YAML, link targets/headings, source roles/locators and draft hashes
pass local checks. Obsidian reading view, independent source review and fresh-session
recall remain NOT RUN; E03's overall verification stays open. B did not receive private
source or derived note contents. Source approval grants no canonical publication.

Preparation 2026-11-04: Main inspected only metadata and hashes for the exact
existing pilot. The historical authorization explicitly excludes other sessions;
no source/draft text was displayed to or interpreted by Main. The packet hash and
all five current draft hashes match validation. A concrete private review request
is staged at private staging/wiki-review-proposal-2026-11-04/ (manifest SHA-256
`03d277561f97d7eeadecc997ac83281801ca169603280e42de25d43d646a0f37`).
At preparation it was PENDING_NOT_AUTHORIZED: proposed OpenAI processing by current Main and
the existing Independent Reviewer, exact packet/five drafts only, private fidelity,
links and disposable reading-view review. It grants no canonical publication or
enrollment, existing-note edits, broader archives/attachments or provider expansion.
That proposal required exact new-session approval before reviewing bodies and a
separate later canonical import request. Its historical manifest stays unchanged.

Approved review 2026-11-04: owner explicitly approved the exact private packet and
five drafts for Main plus the named independent OpenAI reviewer. Separate
authorization-2026-11-04.json SHA-256
`ec1235899d42bbe09b3a0a98193e17b7e9395bcdec0b74c1e79e3943e01ec2c9`
records that approval under the proposal directory. Reviewer checked all four claims
and ten dispositions against the packet, preserving role/date/truncation/inference.
Main created separate derived copies; original packet/drafts remain unchanged.
The root index/log collision was avoided through explicit distinct preview paths;
their historical status wording was corrected and independently re-reviewed.
Frozen preview-v2 manifest SHA-256
`0ca68655051f8279eb6c9abde39cca18e136e93e34fda7759ac6a32a274cac7a`;
independent v2 finding-resolution review SHA-256
`3ae9fd2fb74c17b8ccfdf0592a03f6ea50ff209f71846f56f49d88640a1f0a91`.
Both original and preview static checks resolve all18 wikilinks/headings, personal
privacy and candidate/evidence labels retained. Main's static-v2 report SHA-256
`ff193eb923a6935cf202fc514de5c0445f1a5c1fa373a814b861d20699e9cb09`.
The initial reading-view attempt was blocked by minimized Obsidian. After the owner
enabled official CLI1.15.0 and opened exact v2, Main checked all five notes in native
preview: 15 properties each, 18 resolved links and seven native link navigations.
Screenshots were visually inspected; all five final hashes match the frozen v2.
An accidental private goals-note edit was preserved and restored with owner consent.
Independent review verified supplied receipt/catalog hashes and current five bytes,
without independently reproducing or interpreting the UI. Current private evidence:
review-status-2026-11-04-complete.json and
cli-render-verification-2026-11-04/reading-view-verification.json (SHA-256
`83855a5506ff92e59eb0f532db4db80825bffd09d8b64270be413d92423b9c07`).
Earlier REVIEW-RESULTS.md/review-status.json remain historical snapshots.
At that private-review checkpoint, historical publication/enrollment and recall
were unapproved/unperformed. The separately approved live follow-up below records
the later exact-five activation; original review evidence remains historical.

### E03-H: Exact-byte historical create-only importer

Source implementation authorized 2026-11-04. Main owns the frozen
[contract](../docs/historical-import-spec.md), integration and inactive exact-file
proposal. Implementer owns only scripts/publish_historical.py and
tests/test_publish_historical.py; Independent Reviewer owns read-only synthetic
review after frozen hashes. Active runtime/configuration and T05 remain unchanged.

- [x] Establish exact-pin, bounded-input, no-clobber and dedicated-policy contract.
- [x] Independent contract review: f9ad186bca7619d6e5779b9616099c64cd6a7e45b93dc2f496ec9f6156cb7b71.
      Unconfirmed attempted writes always refuse automatic recovery, including equal
      bytes; positive installed records follow confirmed successful creates.
- [x] Implement loader, actual create/enrollment and truthful partial/retry results
      through RED/GREEN synthetic slices.
- [x] Prove independent-process collisions, fail points, owner edits/deletion,
      pointer/receipt consistency and existing-reader scoped synthetic citations.
- [x] Freeze source/tests; independent source/synthetic review and full regression.
- [x] Complete exact-five inactive package and explicit publication/read request.
- [x] Obtain later exact canonical activation approval before execution/enrollment.
- [x] Create/enroll exactly five absent destinations; verify exact bytes and zero-save
      replay, with independent hash-only canonical verification.
- [x] Verify historical recall via native MCP in a fresh CLI and real stdio MCP through
      the current app's command tool, keeping their host evidence distinct.
- [x] Refresh MCP in the app and verify native history tools there. Supported
      app-server config/mcpServer/reload resolved absence after owner restart; actual
      current-app native search/read passed. No UI automation or configuration write.
- [ ] Verify cloud-copy bytes for this newly imported five-note batch; local results
      and earlier bootstrap cloud checks do not prove this upload.

Private preparation: staging/historical-import-20261104-v1. Five exact reviewed
v2 payloads and eight evidence pins are staged; authorization remains pending,
policy disabled and personal-content read approval false. Real destination
availability, canonical execution and historical host exposure are NOT RUN.
Read-only task baseline records seven current source/installed/config hashes;
it does not resolve the prior host-config drift or imply global immutability.

Source result: importer SHA-256
`c92975d4ea18ea9f51002f7c8eadeedd71b2c40be2dba540a8216c16079710a2`,
tests `8e3f89bc10b2120ac9bf05990cf89123f706628699200f409a0dc601a160f936`.
Independent v2 review SHA-256
`b2b48bc3d98a7f3254f033c4a52485ce4f6ebe62592536a0b6d021486305a03d`
supersedes initial NO-GO after three demonstrated pointer/replay findings were
fixed and independently reprobed. Focused42/41pass/1native-symlink skip;
Main full219/216pass/3native-symlink skips. Corrected eight-module package plus
test/lock/contract manifest SHA-256
`cbe9af1281f8e1f731f5fb15c53957e31bac9579b505187eca5b47717eb4765b`.
Main packaged synthetic create/exact-byte/replay/real-MCP search/read/scope refusal
PASS; proof `4ecc0c08da6dfe262f344c3ba35aff9df3ee689fe8e3f9cda0407f719f694028`.
Earlier first-package test/proof artifacts remain scoped historical results, not
corrected-source release evidence. Seven preparation start/end hashes match.
Frozen inactive activation manifest7d2888.../request5ac3b8... passed independent
package metadata/byte review SHA-256
`758d24c7ff43b39a8d43071372e44a3a2153c63038518480552d42db3512bb8d`.
Exact owner activation decision remains pending; canonical availability remains
NOT RUN. No live authorization, installed-dependency integrity, same-account race,
native crash durability, historical model-session or cloud result is inferred.

Live follow-up 2026-11-04 supersedes that preparation state: owner replied
`i approve` after the exact publication/future OpenAI-read scope explanation.
Main recorded actual approval and separate active copies; independent active-input
comparison PASS (`04f61db808441f79ec243722a5255dcb1a84421c0b504b52488210ddae8f4379`).
All five target paths were absent/nonredirected at Main's metadata preflight. Frozen
importer created five and enrolled generation1, with no recovered/adopted files,
updates or links. Exact replay returned NO_CHANGE, saved0, unchanged5 and no new
generation. Independent canonical bytes/enrollment review PASS
`228b4313831c92e9f75134282c4f5057a03f07de2a553e2d474abdd4c8dfedde`;
initial absence/create/replay remain Main-observed, not independently witnessed.

The exact reviewed `second_brain_history` entry was appended to the current host
configuration. Before/after checks preserved its existing byte prefix and parsed
entries; the earlier unrelated config drift remains unresolved and no old rollback
was used. Fresh explicit CLI verification completed two native historical calls
and zero shell/file-change items, generation1 with expected note/citation hash.
Proof `6eade2115ab47d01f1c78def58a5ca934d6ac5079e2299eb8116840e64575c28`.
Two non-tool error items remain unexamined; the first pre-start attempt had an own
override-key quoting error, corrected only per invocation before any tools ran.
Current-app command-to-real-stdio proof PASS
`35ea7dab7cc7754cab43adcbdd4f19e39c07bc374133d49dc64e845fa706f91d`.
Native history tools were absent from Main and one other app task; no native app
discovery claim. Private activation records are under
activations/historical-import-20261104-v1/. New-note cloud bytes, live canonical
Obsidian rendering, whole-vault preservation and native crash durability remain
unproved. Prior private-v2 rendering applies only to the same reviewed bytes.
Final independent evidence/current-host comparison PASS, report SHA-256
`34437ce547946ead4f9e1b0ee79b4ef9823b694f80be4ddfa74247c19b5769e5`:
17 evidence pins, two completed native CLI calls and exact current prefix/entry
checked; no note interpretation, new live call or native app proof inferred.

Later native-app diagnosis: the owner's restart and fresh session still reported
history tools unavailable. Main found the supported app-server control API. Using
the existing CLI proxy with the documented Unix-socket WebSocket transport,
own-thread status returned no history server before config/mcpServer/reload and
connected/two tools afterward. Actual native tools then appeared; one search and a
three-line read returned the expected approved ID/hash/source at generation1.
Native proof SHA-256
`13d3ea49355ae31beac84fd5cb843f400e8f442adb2a3d6a54645eeb3a82ebee`;
control report `ca9ee087615388f544cd6df2a930a180f21f3ec784c21ff6c105be4209d51490`.
Config bytes6a1fc169... matched before/after this reload, history entry/grant and
source/test freeze unchanged. This later config differs from the old installation
receipt; no rollback/reconciliation or source edit was performed. Earlier manual-
only advice is superseded; Computer Use's app-UI prohibition remains respected.
Current native proof is not a new blind/fresh-session test after reload. Cloud
verification remains pending. Diagnostics are private under the activation's
native-app-diagnostic-v1/ directory.

Parallel generic feasibility: current publisher validates/reconstructs session
captures, not arbitrary historical Markdown; direct commit-helper invocation would
bypass required validation. A small separately specified/verified historical entry
point, policy/enrollment and named-client reader route are needed before an import
activation proposal. Source-only report SHA-256
`2bce1d82ba70a6de2c69462025f0d69e777f15385f6f43460764c9ba58013aa6`.
No code, live policy/grant or canonical writes followed; root index/log updates stay
excluded with T05/T07 open. No other archive/attachment/provider access was used.

### CE2: Useful private wiki pilot

- [x] Source fidelity, processing permissions, link validity and actual recall status
      recorded separately; exact-five approved local publication and fresh CLI recall
      pass. Current-app native recall later passed after supported configuration
      reload; this batch's cloud proof remains separately open.

## E04: Expand historical knowledge in tracked batches

- [ ] Complete or explicitly ongoing. Owner: A. Dependencies: E03, T11/T12 pilot proof.
      Estimate: timeboxed batches on Day 3; further coverage estimated from the pilot.
      Scope: S per batch.

Acceptance:
- [ ] Prioritize useful projects/topics and consolidate repeated claims without
      erasing provenance; sources map to integrated, skipped, quarantined or deferred.
- [ ] Each batch uses the same approved processing/publication policy and recoverable
      write path; no whole-export model upload or unbounded source expansion.
- [ ] Report historical coverage separately from system readiness. Do not mark this
      task complete while unprocessed selected sources remain unaccounted for.

Verification: private batch receipts, sampled evidence/link checks and authorized
recall of newly integrated knowledge. No repository changes expected for ordinary batches.

## T01: Freeze a minimal reusable save/recall contract

- [x] Source complete (synthetic scope). Owner: A. Dependencies: none. Estimate: 1 hour. Scope: M.

Description: reconcile the existing drafts with the brownfield and define the small
interface both terminals use, including inactive policy and version compatibility.

Acceptance:
- [x] Preserve existing staging behavior; freeze packet/result, managed-note IDs,
      policy and committed-manifest interfaces without adding a memory framework.
- [x] Propose exact bootstrap/write/read/provider scopes; distinguish local matching
      from external-model recall and keep historical grants unchanged.
- [x] Both terminals acknowledge file ownership; drafts preserve references/ and
      explicitly describe the additional recall/client scope.

Verification: inspect contracts against existing adapter/reader tests and threat
boundaries; record unresolved decisions without activating policy. No runtime change.
Likely files (4): docs/brain-save-publication-spec.md, docs/portable-vault-layout.md,
docs/brain-memory-contract.md, examples/brain-publication-policy.example.json.

Result 2026-11-02: B peer-reviewed the shared contract and A resolved policy-enabled
and pointer/generation requirements. Interfaces are frozen; the example remains inert.

## T02: Prepare the reused wiki instructions and format guidance

- [x] Complete (synthetic source templates). Owner: B. Dependencies: none;
      reconcile with T01 before live installation/freeze.
      Estimate: 1 hour. Scope: M.

Description: adapt Karpathy's pattern to current paths and reuse the pinned Kepano
Markdown guidance instead of introducing a folder migration or another framework.

Acceptance:
- [x] Synthetic templates provide a small entry guide, index, chronological change
      log and shared operating instructions; existing canonical paths stay intact.
- [x] Instructions route to relevant authorized notes and current repository evidence;
      retrieved content is evidence, never authority to change policy.
- [x] Establish how target clients discover the existing pinned Obsidian Markdown
      skill; avoid duplicate-name installations and unnecessary CLI/plugin dependencies.

Verification: inspect rendered fixture links/frontmatter against the vendored skill;
review instruction size and discovery route. Do not install into the live vault.
Likely files (5): templates/vault/AGENTS.md, CLAUDE.md, index.md, log.md, system/brain.md.

Result 2026-10-31: B drafted five templates; UTF-8/YAML, six internal wikilinks and
whitespace checks passed. A independently read all five. A added exact template
exceptions to .gitignore while retaining general vault exclusions. Instructions use
an explicit configured-toolkit skill path; actual host discovery, Obsidian rendering,
live installation and policy activation remain NOT RUN.

## T02a: Refresh source instructions for the active save/recall loop

- [x] Source refresh complete, statically reviewed. Owner: Session 2; five files frozen.
      Dependencies: T01, completed T02/T08 evidence. Scope: M, five source files.

Description: update the existing templates to describe current create-only Codex
behavior and pending wiki capabilities without changing active policies or runtime.

Acceptance:
- [x] All five templates agree on canonical/private/tooling boundaries, explicit
      save/recall, citation/evidence handling and the existing folder layout.
- [x] The guide distinguishes proposed bootstrap from deployment, excludes automatic
      capture and does not imply that CLAUDE.md grants Anthropic access.
- [x] Synthetic navigation targets resolve and no machine paths, grants or personal
      note bodies are added to reusable templates.

Verification: inspect all five source templates and render/check a disposable
synthetic fixture against the pinned Obsidian formatting guidance; record links and
instruction discovery limits. No live vault reads or writes are needed.
Files: templates/vault/AGENTS.md, templates/vault/CLAUDE.md,
templates/vault/index.md, templates/vault/log.md, templates/vault/system/brain.md.

Result 2026-11-03: Session 2 applied the exact five-template source update; Main
and Session 3 independently matched source bytes to the frozen candidate manifest.
The reviewer found no blocking content findings; UTF-8, static wikilinks and pinned
Obsidian syntax guidance checked. Obsidian reading view and actual host discovery
remain NOT RUN and are separate T02b gates; no canonical deployment followed.
Source hashes: AGENTS.md 04a64e4e39c65314742e459668e126ac2d382bf0f46e9852ddeb7c1cfc6bed2e;
CLAUDE.md 56a43d9ad6b34d0dbe90658abc720b3ace616ff0bff05245f9bcae9139bd7301;
index.md 0f26fccabc2470d8389d771a0f0437cc242d59716a780658299aa48efcde2109;
log.md 3646e393d77a9a9d6a635b9e17a01744425988f2c4e631f1b8e36fe1c2629814;
system/brain.md d87c3c5fbf1ffe31a2c9a0b9e28e48b7caf3ece1c3be40c0056ab2db3f35cf09.

## T02b: Prepare and deploy the exact approved vault bootstrap

- [x] Complete for approved local creation/byte verification and canonical CLI startup. Owner: Main. Dependencies: T02a and independent frozen review;
      separate exact-file approval before live installation. Scope: S per phase.

Description: prepare a concrete proposal for the five vault-relative targets
AGENTS.md, CLAUDE.md, index.md, log.md and system/brain.md. Specify reviewed bytes,
ownership, collision handling and recovery before asking to activate that scope.

Acceptance:
- [x] Source proposal names exact contents/targets, discovery behavior and managed
      ownership; an existing target is preserved/refused rather than overwritten.
- [x] Disposable installation/replay/collision/recovery checks pass; instructions and
      links work in the fixture. File presence alone is not client-discovery proof.
- [x] After separate owner approval, install only approved files, record exact
      results and verify navigation/discovery within authorized scope; otherwise
      remain PROPOSAL READY, NOT DEPLOYED. Provider grants stay separate.

Verification: synthetic pre/post byte checks, no-clobber replay and collision probes;
independent review of frozen contents, followed by separately approved live checks.
Likely source files: docs/portable-vault-layout.md; reuse existing bootstrap helpers
if sufficient. Any new helper/tests must be scoped before implementation. Machine
settings, target-state metadata, approvals and deployment receipts stay private.

Next slice ownership ACK: Session 2 owns scripts/bootstrap_vault.py and
tests/test_vault_bootstrap.py only; Main owns documentation/ledger and Session 3
reviews only after the helper/test freeze. A small callable reuses existing
no-clobber/path/lock primitives; no CLI, installed-skill change or live invocation.
The agreed API and partial-result contract are in docs/portable-vault-layout.md.

Current source implementation freeze 2026-11-03 (scoped source/synthetic review PASS):
- scripts/bootstrap_vault.py: 091c557f4240ae0d82d4c9a5a388bd94c31087fbab06db91363d148495ac55d8
- tests/test_vault_bootstrap.py: 52dfad2c80a5dc712e0a7ff7b965a9d500126beef43543d8bd7aa8301e0c34ee

The implementer reports 14 focused tests (13 pass, one native symlink skip) and
176 combined tests (174 pass, two native Windows symlink skips). Main independently
rehearsed the exact five templates in a disposable filesystem: created five, replay
created zero/recovered five, final hashes match and unrelated fixture bytes survive.
Additional independent negatives refused missing/extra hashes, overlapping roots,
root aliases and an intent-write failure with no target writes. These are synthetic
checks, not actual crash, directory durability, Obsidian or host-discovery evidence.

Main's required bounded-read finding is resolved in the current source freeze:
_read now reuses the existing 128000-byte ceiling. Source/target/intent oversized
regressions were added, and Main independently proved refusal before opening each
oversized file with bytes preserved. Session 2 confirmed receiving Session 3's
explicit pause/release ACK before making the fix; that ACK reached the implementer
directly while Main's thread-tool transport was unavailable. No further source edits
are authorized during the new freeze.

Main received Session 3's exact private handoff
handoffs/2026-11-03-bootstrap-review.md. The reviewer verified both current hashes,
independently ran 14 focused tests (13 pass, one native symlink skip) and found no
further required issues in the bounded source/synthetic scope. Actual crash/directory
durability, native symlink behavior, same-account path races, Obsidian reading view,
client discovery and live/cloud deployment remain unproved. T02b's full gate stays
open; the source helper is reviewed, not activated.

Tool handoffs failed when the local codex_tui MCP transport stopped responding;
codex queue plus the exact private report provided verified fallback delivery.
Queue submission alone does not prove receipt. No full-suite rerun on unchanged source.

Progress 2026-11-03: Main prepared the exact five-path source proposal in
docs/portable-vault-layout.md and corrected its obsolete staging-only description.
Session 3 ACKed independent read-only reviewer ownership. It independently probed
the existing write_immutable primitive with disposable Windows fixtures: create,
identical replay, different-byte refusal, mocked competing creation, retry after a
simulated two-file interruption and preservation of a later edit passed. These are
primitive/sequential simulation checks, not a journaled bootstrap installer, actual
crash/concurrency, directory durability, path-race, Obsidian or host-discovery proof.
Review clarified that equal-byte False on an initial install is a collision, not
ownership. T02b remains PREPARING, NOT DEPLOYED: payload freeze/review, full install
procedure and runtime checks remain open. The reviewer rechecked the corrected
proposal at SHA-256 ee4b2203d1389c8c952df4305bb521a7d9c26bdb51c9233315ad71b6acf88f17;
the collision finding is resolved as documentation only. Session 2 ACKed exclusive
five-template ownership. Its initial sandbox blocker was resolved by the owner's
instruction that all terminals now have full access. Source work can proceed within
the ACKed paths; canonical writes and provider scope remain separate.

### T02b follow-up: prompted route and runtime verification

A fresh ephemeral Codex CLI 0.166.0 probe completed two explicit local read commands
with exit 0: fixture entry/guide and the pinned Obsidian Markdown skill. Its prompt
supplied the toolkit root and requested those reads. Session 3's exact private
handoff handoffs/2026-11-03-bootstrap-discovery-review.md was received and SHA-256
verified as 1605213035b88af36ae527d0e1e400db4ede3f946ecc618ac610a8801a9f87d3.
The review supports explicit prompted reading/interpretation, not automatic AGENTS
injection, cross-project discovery, actual recall, Obsidian rendering or deployment.
The five source hashes match the manifest. Unchanged pre/post fixture hashes were
checked by Main; that claim was not independently established by the review packet.

The exact pending package under private staging/bootstrap-proposal-2026-11-03-source-v1
freezes six runtime modules and five payloads. Manifest SHA-256 is
bfbee88e89239f2074d62715ef05a6f81cad3ea78cadc19dc44cbc5bfca79e5b. The reviewer
matched every size/hash to the package and current source. The helper/five payloads
match prior reviewed freezes; the other five runtime dependencies were matched to
current source, not independently re-reviewed in this slice. Main rehearsed this
self-contained package in a disposable filesystem with five creates and an exact
zero-create replay. State remains PENDING_NOT_AUTHORIZED; no canonical invocation.

Earlier UI attempts only exposed the folder in Explorer or the parent private
workspace. On 2026-11-04 the exact test-vault was open as its own Obsidian vault.
Main observed all five files in reading view in Obsidian 1.15.0: headings, properties,
the index table and inline code rendered; entry-to-index, index-to-guide/log and
guide/log-to-index navigation worked. Dated input/output Markdown hashes match.
Private receipt: staging/bootstrap-verification-2026-11-03/render-verification-2026-11-04.json,
SHA-256 cb90fcfa0e14cea8d64f1bd1309a4ff01c601fb18e2ac7f78764d00a63010341.
These are Main's visual observations, not independent visual reproduction. No
canonical note bodies were inspected or changed. Obsidian CLI remains disabled.

A distinct fresh CLI 0.166.0 startup probe on 2026-11-04 used no tools. It returned
the exact first four nonempty fixture AGENTS.md lines and the required guide/skill
paths, while the expected lines were absent from its prompt. All recorded item
types were agent_message; no incomplete or completed tool item appeared. Main's
check supports startup instruction loading for this CLI and fixture working
directory. It does not establish cross-project discovery, another client, actual
recall or future canonical behavior. The independent readiness evidence review was
received at handoffs/2026-11-04-bootstrap-readiness-review.md: exact returned lines,
no tool items, current fixture/source hashes and artifact consistency checked, with
no required evidence correction. Process/cwd and before/after observations remain
recorded evidence; the reviewer did not independently reproduce the CLI or UI.

The exact frozen package remains unchanged and PENDING_NOT_AUTHORIZED. Read-only
metadata preflight found all five canonical target paths absent. The concrete
one-time request is private staging/bootstrap-proposal-2026-11-03-source-v1/
activation-request-2026-11-04.md. Its dated readiness/render records supplement the
manifest's historical preparation-time pending gates; they grant no permission.
The owner then approved the exact bootstrap and deferred additional AI providers.
Main recorded the visible approval privately and invoked the unchanged frozen
package: five files created, zero recovered on initial invocation, all final hashes
matched; replay created zero and verified five existing payloads. Installed save/
recall local settings hashes were unchanged. Evidence is under private
activations/bootstrap-20261103-v1/authorization.json and
installation-receipt-2026-11-04.json. Historical proposal files stay pending drafts;
the separate real authorization receipt is the authority.

Session 3's handoffs/2026-11-04-bootstrap-install-review.md independently verified
the five exact canonical byte lengths/hashes against manifest and receipt. It did
not witness creation/replay or establish prior absence/settings/unrelated-file state.
Review SHA-256, verified by Main on ACK:
`514bf7940778497aa4ead18247db19d3c374bd8e829dfdf25c1312a2e440de70`.
Authorization/manifest hashes also matched; enrollment remains receipt-reported.
The review does not prove cloud synchronization or canonical host discovery.
Main also ran an approved fresh canonical-cwd startup probe: exact four bootstrap
entry lines returned with expected text absent from the prompt, exit 0 and zero
tool items. No other canonical note was read. T02b is LOCAL INSTALLATION VERIFIED;
cloud sync for these new files and cross-project/other-client behavior are unproved.
Live Obsidian UI was not re-run; exact installed bytes match the rendered fixture.
No existing-note adoption/update, automatic index/log maintenance or managed-corpus
enrollment followed. T05 updates remain disabled; T11's broader wiki gate stays open.

### C1: Scope and interface freeze

- [x] T01/T02 reviewed, both terminal assignments acknowledged; live permissions inactive.

## T03: Save a new note through the existing capture path

- [x] Source complete (synthetic scope). Owner: A. Dependencies: T01. Estimate: 2 hours. Scope: M.

Description: validated staged evidence feeds a small local publisher in a disposable
vault. Freeze its callable result before B connects the existing adapter.

Acceptance:
- [x] An ordinary synthetic capture creates a qualified canonical-style note and
      truthful receipt; absent/revoked/changed policy causes no canonical write.
- [x] Journal and integrity evidence precede mutation; same-filesystem installation
      cannot clobber another writer's newly created file; success verifies final bytes.
- [x] Unsafe paths/links, sensitive input and incomplete prior work fail safely;
      exact replay creates no duplicate note and retains project/session/role identity.

Verification: targeted new-note publication tests, including an independent process
racing to create the destination and interrupted creation. Use temp directories only.
Proposed focused command: python -B -m unittest discover -s tests -p test_publish_memory.py -v.
Likely files (3): scripts/publish_memory.py, tests/test_publish_memory.py,
examples/brain-publication-policy.example.json. B owns later adapter integration.

Result 2026-11-02: 18 focused publication tests pass. B peer-reviewed the publisher;
a fresh independent reviewer confirmed the final recovery fix after an intervening
publication. Content-addressed immutable manifests retain stable transaction identity.
No canonical policy, installed publisher capability or cloud sync was activated.

## T04: Check client access and OneDrive prerequisites early

- [ ] Complete. Owner: B. Dependencies: T01 scope; can overlap T03.
      Estimate: 30-60 minutes. Scope: S.

Description: identify connection/sign-in blockers before investing in extra adapters.

Acceptance:
- [ ] Record the actual ChatGPT surface, local MCP capability and supported invocation
      route using the existing synthetic reader; do not infer access from documentation.
- [ ] Check correct OneDrive account/root mapping, client health and local availability;
      identify cloud verification access and any account action the owner must perform.
- [ ] Record separate PASS/BLOCKED/NOT RUN results; expose no secrets or personal text,
      and do not redirect synthetic profiles or create a second vault.

Verification: synthetic read-only tool call where available, native sync status and
authenticated cloud metadata access. Configuration presence alone is insufficient.
Likely repository file (1): docs/client-compatibility.md; actual config/evidence private.

Metadata preflight 2026-10-31: B documented local clients, sanitized MCP inventory,
OneDrive process and root mapping. A reviewed the report. Actual ChatGPT surface,
client tool calls, native account/health and cloud bytes are NOT RUN/unverified;
T04 stays open for these runtime checks. No configuration or account changes occurred.

Follow-up 2026-11-04: the owner's fresh local Work session discovered brain-recall
from a different cwd and searched the existing approved corpus. Its read40 request
refused because 38 selected lines totaled 8646 characters, over the unchanged8000
limit; Main traced the exact failure without suppressing checks. The source-only
five-line-window instruction fix passed independent review (private
handoffs/2026-11-04-recall-window-review.md, SHA-256
`bd42de74016c8ccb85277c83e039b7f15b1c48c641b7ace8347b9da4fa4b8805`).
Main installed only the reviewed SKILL.md with backup; runtime/settings unchanged.
Five existing adapter tests pass, synthetic size refusal/preservation passes, and
a controlled local live search plus five-line read passes. The owner's subsequent
Work-session retest completed a cited architecture answer. Main verified its exact
recorded turn: explicit updated-skill reload, one search, 11 successful reads of
at most five lines (largest2181 characters), matching note hashes/generation2.
Local app recall passes for this route; app-side save, hosted ChatGPT, native MCP,
automatic background recall and cloud sync remain separately unproved. Private
activations/recall-window-20261104-v1/app-recall-verification.json SHA-256
`7b66b0d3f95c79571893dc5579122b6e3fa8323578c8a146c619522087cb50ba`.
No write commands were observed in the retest; no whole-filesystem baseline was
performed. No grants, policies, canonical notes or bootstrap
templates changed; no native MCP or hosted ChatGPT proof is inferred. See
docs/client-compatibility.md and private activations/recall-window-20261104-v1/.

### C2: New-note save and known prerequisites

- [x] T03 synthetic path passes; T04 metadata preflight identifies unresolved runtime/account checks.

## T05: Preserve existing knowledge through safe updates and recovery

- [ ] Complete. Owner: A. Dependencies: T03. Estimate: 2-3 hours. Scope: M.

Description: add bounded managed-section updates to the same publisher and demonstrate
recoverable failures before any live update capability can activate.

Acceptance:
- [ ] Only enrolled managed sections/allowed metadata change; unrelated bytes,
      privacy and earlier dated decisions survive. Contradictions quarantine.
- [ ] Competing publisher/editor processes cannot cause silent lost updates; recovery
      after journal/write/receipt failures preserves later edits and reports actual commits.
- [ ] Simulated sync conflicts, unavailable files and stale hashes refuse affected
      updates. Unproved exclusion means updates remain disabled, with partial status.

Verification: focused subprocess race and fault-injection tests at meaningful mutation
boundaries, plus conditional restore demonstration in a synthetic vault.
Proposed command: python -B -m unittest discover -s tests -p test_publish_memory.py -v.
Likely files (3): scripts/publish_memory.py, tests/test_publish_memory.py,
docs/brain-save-publication-spec.md.

T05 risk-first feasibility result 2026-11-03: Session 2 ACKed proposed ownership of
scripts/windows_edit_guard.py and tests/test_windows_edit_guard.py, but neither file
was created. Ordered disposable native probes reported that share-zero exclusion
blocks competing writes/rename/replacement and also blocks the guard process's
own os.replace. A handle-based FileRenameInfo control succeeded without the target
guard and failed against the guarded target. A later-edit comparison preserved the
edit in one ordering. None establishes continuous exclusion through atomic commit,
conditional restoration or the full synchronized editor/process matrix.

Frozen private report: handoffs/2026-11-03-t05-feasibility.md, SHA-256
8f50d3375810a3a348d20bb6768db2c4e923838f415f4f0f706681006bff2221.
Reviewer report: handoffs/2026-11-03-t05-feasibility-review.md, SHA-256
ce1a2862f4a6032e243239e785d7a4e52fac49674389f9216f884d2f503ee524.
The reviewer verified the report hash and primary API claims and found no required
correction to the narrow conclusion. Native probe observations remain implementer-
reported, not independently reproduced: no frozen runnable probe/transcript was
provided. The result does not establish that every Windows update design is
impossible. Handle-based/POSIX/oplock alternatives remain research hypotheses until
their real commit protocol and conflicts/recovery are independently demonstrated.
Do not release the guard before replace, substitute in-place writes, or weaken the
existing acceptance bar. T05 stays OPEN and updates disabled; estimates need revision
after a feasible protocol is established. No source/runtime/policy changes resulted.

## T06: Recall authorized newly published knowledge without manual repinning

- [x] Source complete (synthetic scope). Owner: B. Dependencies: T01 frozen contract, T03 committed fixtures.
      Estimate: 2 hours. Scope: M.

Description: reuse the reader's safety/limit conventions for an approved managed
corpus bound to trusted publication receipts, leaving historical fixed grants intact.

Acceptance:
- [x] Search/read returns bounded relevant excerpts with identity, lines, hashes and
      provenance only for the named provider's approved managed corpus.
- [x] A validated publish updates the trusted manifest; a later authorized query sees
      the note without human repinning. Tampering, external edits, revoked scope,
      unselected notes and denied metadata cannot silently expand results.
- [x] A fresh synthetic MCP process recalls a prior saved result without a vault-wide
      model dump; out-of-scope and no-match requests disclose no unrelated material.

Verification: two successive synthetic publications followed by bounded reads,
negative permission tests and real stdio tool calls. Existing reader tests stay green.
Proposed command: python -B -m unittest discover -s tests -p 'test_managed_memory*.py' -v.
Likely files (4): scripts/managed_memory.py, scripts/managed_memory_mcp.py,
tests/test_managed_memory.py, tests/test_managed_memory_mcp.py. Consolidate if simpler.

### C3: Synthetic save-to-recall demonstration

- [x] A saved synthetic note is recalled through real tools in a fresh MCP process; fresh model-session proof is pending.
- [x] T05 is NOT IMPLEMENTED; updates disabled, no live writes.

Result 2026-11-02: bounded reader/MCP negative cases and real stdio calls pass.
A reviewed the reader and killed a citation-limit mutation. A fresh independent
reviewer verified final framework-error redaction, including response/stderr canaries.
The joint roundtrip recalls two successive publications in one fresh MCP process
without changing grant bytes. This is not an authenticated model/client-session test.

## T07: Maintain connected project knowledge and navigation

- [ ] Complete. Owner: A. Dependencies: T02, T05. Estimate: 2 hours. Scope: M.

Description: route eligible claims into managed project/lesson/session notes and
maintain useful connections and navigation using the same safe mutation mechanism.

Acceptance:
- [ ] Deterministic IDs and conservative local matching add valid path-qualified
      wikilinks; ambiguous matches are skipped rather than fabricated.
- [ ] Repeated normalized claims avoid duplicate prose while distinct role/session
      provenance survives; contradictory/superseding claims preserve history.
- [ ] Approved managed indexes/log update recoverably; local matches against denied
      notes never leak content/derived summaries through model-facing output.

Verification: run repeated cross-session capture against seeded synthetic knowledge;
assert valid targets, preserved history/unmanaged bytes and no denied-text canary leaks.
Proposed command: python -B -m unittest discover -s tests -p test_wiki_memory.py -v.
Likely files (4): scripts/wiki_memory.py, scripts/publish_memory.py,
tests/test_wiki_memory.py, tests/test_publish_memory.py.

## T08: Connect explicit Codex save and recall skills

- [x] Complete for approved local create-only scope. Owner: B. Dependencies: T02, T03 callable API, T06.
      Estimate: 1-2 hours. Scope: M.

Description: keep the existing brain-save extraction and add a convenient recall
entry point backed by the shared operations, with no second model/capture session.

Acceptance:
- [x] One brain-save invocation stages and publishes when policy permits, otherwise
      retains v1 behavior; reply truthfully distinguishes saved/updated/linked/exceptions.
- [x] Brain-recall retrieves only scoped relevant evidence; skill instructions remain
      short and refer to detailed contracts rather than loading the whole vault.
- [x] Source packages validate; proposed install/update preserves local settings and
      relevant pinned Obsidian guidance. Installation remains inactive until T11.

Verification: skill-creator validation and a same-thread synthetic save followed by
fresh-session recall; use existing tests plus focused adapter integration cases.
Command: python -B -m unittest discover -s tests -p test_interactive_memory.py -v.
Likely files (5): scripts/save_interactive_memory.py, tests/test_interactive_memory.py,
skills/brain-save/SKILL.md, skills/brain-save/references/packet.md,
skills/brain-recall/SKILL.md.

Result 2026-11-02: SOURCE PACKAGES COMPLETE; subsequent approved installation and
fresh CLI recall are recorded below and in T11. Save integration: 23 tests run, 22 passed, one
existing symlink skip. Recall CLI: five tests pass. Both skills pass skill-creator
validation. A independently reviewed B changes and killed exit-status mutations.
Installed save still has staging-only settings; recall is not installed.

Activation result 2026-11-02: frozen source skills installed with private backups and
fixed settings. Current-session harmless save and fresh installed-skill Codex CLI
recall passed; exact hidden phrase and note/hash citation matched. No second extraction
model or history access was used. Existing-note update/link behavior is not included.

## T09: Expose the same save operation to the second client if needed

- [ ] Complete. Owner: B. Dependencies: T04, T06, T08 frozen interfaces.
      Estimate: 1-2 hours, timebox. Scope: M.

Description: if the actual ChatGPT host needs an MCP save tool, add a thin default-off
adapter to the existing publisher. Prefer direct reuse if T04 proves sufficient.

Acceptance:
- [ ] Explicit save uses the same validated packet, publisher and receipt; no separate
      database, extraction model, unrestricted file tool or transcript discovery.
- [ ] Host configuration fixes scope/project mapping; model input cannot select
      arbitrary filesystem roots. Unsupported session identity stays explicitly unknown.
- [ ] Existing read-only servers remain read-only; write-tool activation and provider
      access require the approved policy. Synthetic tool tests prove the real boundary.

Verification: actual synthetic protocol calls, malformed/unauthorized arguments and
replay checks. If blocked by host access, document the result and do not build a
hosted service merely to meet the sprint deadline.
Proposed command: python -B -m unittest discover -s tests -p test_brain_save_mcp.py -v.
Likely files (3): scripts/brain_save_mcp.py, tests/test_brain_save_mcp.py,
docs/client-compatibility.md; use an existing module if it keeps the boundary clear.

### C4: Complete synthetic core and frozen review handoff

- [ ] T05-T08 acceptance evidence recorded; T09 supported/blocked status explicit.
- [x] Full regression command from plan.md passes; skipped checks remain visible.
- [x] Create-only source hashes, policy example and evidence frozen for independent review.

## T10: Independently review the frozen implementation

- [ ] Complete. Owners: A reviews B; B reviews A, each in a fresh Reviewer session.
      Dependencies: E01/E02, T05-T09; E03 when reviewing the historical pilot.
      Estimate: 1-2 combined hours initially; findings can revise the estimate. Scope: S.

Acceptance:
- [ ] Each reviewer inspects code they did not implement, traces privacy/write/recovery
      boundaries and independently reproduces relevant synthetic acceptance probes.
- [ ] GO/NO-GO names reviewed hashes, scope and unresolved risks; no own-work signoff,
      canonical edits or promotion of reported test results into independent evidence.
- [ ] Fixes return to the appropriate implementer; reviewers recheck affected findings
      without unrelated redesign or repeated full reviews.

Verification: recorded independent commands/results and frozen source identity.
Each reviewer writes only separate private evidence. After the review freeze ends,
A integrates the summary into docs/brain-memory-release.md; no concurrent doc edits.

### C5: Activation decision

- [x] Independent scoped GO for create-only source; updates/linking remain disabled.
- [x] Concrete create-only policy/install proposal prepared for one-time owner approval;
      owner approval recorded and exact create-only scope activated, with no per-note approval inside that scope.

Result 2026-11-02: PARTIAL, create-only scope reviewed. Peer component checks were
followed by a fresh-context read-only reviewer, using fictional fixtures only. Two
required findings (interrupted enrollment recovery and framework validation echo)
were fixed and independently rechecked. Scoped GO covers first-note publication,
bounded enrolled recall and source CLI integration, subject to owner activation.
No GO is claimed for updates/linking, private pilot fidelity, installed clients,
OneDrive, Graphify, OS isolation or full production readiness.

## T11: Install and activate the approved Codex workflow

- [ ] Full gate complete. Local create-only activation PASS; remaining limits below. Owner: A. Dependencies: T04, T10 GO, explicit live-scope approval.
      Estimate: 1 hour. Scope: S.

Acceptance:
- [x] Approved source skill/config installation preserves machine-local settings,
      keeps staging separate and introduces only approved bootstrap/managed files;
      A applies any approved native OneDrive working-set availability changes.
- [x] An existing Codex conversation saves an approved harmless pilot; a fresh session
      recalls it with bounded citations under the named-provider grant. Publish the
      E03 historical pilot only when its source and destination scope are also approved.
- [ ] Replay, disable and scoped rollback are demonstrated without deleting evidence
      or overwriting later edits; unrelated canonical files remain unchanged.

Verification: private pre/post hashes and actual CLI tool events, not installation
presence alone. No account-wide import, hooks or Git push.
Likely files: installed skill/local policy plus approved vault files outside Git;
repository evidence summary in docs/brain-memory-release.md.

Result 2026-11-02: owner explicitly approved the concrete scope. Twelve frozen runtime/
skill files rechecked, four old installed files/settings backed up, both skills and
approved policy/grant pins installed. Private staging marker stayed false/false.
Exactly one fictional canonical pilot saved; identical replay NO_CHANGE/saved0 and
publication-settings disable passed with exact active settings restored. Fresh Codex
CLI0.166.0 discovered brain-recall and returned the hidden phrase/citation via one
completed local reader command. Global configuration unchanged; Windows sandbox
selection was supplied per invocation for the isolated successful probe. B independently
verified only the pilot local bytes/hash. Full-vault unrelated-file pre/post hashing
and canonical restore were not performed; no existing note was enrolled or edited.
The broader T11/release gate remains open alongside T05/T07 and OneDrive proof.

## T12: Verify the pilot reaches OneDrive cloud

- [x] Complete for exact pilot, point-in-time verification. Owner: B, read-only verification. Dependencies: T04, T11.
      Estimate: 30-60 minutes plus observed sync latency. Scope: S.

Acceptance:
- [x] Correct native sync root/account and working-set availability independently
      confirmed; missing sign-in/pinning is handed back to the owner/A, not changed
      by the read-only verifier.
- [x] The approved pilot appears in the correct OneDrive cloud location; compare a
      remote version/download with local bytes and record time/hash privately.
- [x] Pending/errors/cloud-unverified remain explicit; no continuous-sync guarantee
      or green-icon-only cloud verification claim.

Verification: native client status plus authenticated remote evidence; bodies remain
outside model context. This gate stays unchecked if cloud access is unavailable.
Likely repository file (1): docs/brain-memory-release.md, updated by A from B's handoff.

Result 2026-11-02: B confirmed expected local Personal root mapping and running
processes, and independently matched the exact approved pilot local size/hash. Native
health/pause/errors and correct authenticated cloud identity remain unverified. Cloud
comparison BLOCKED: no authenticated connector/browser host/native status surface.
No settings/login change or repeated polling; sync remains UNVERIFIED. Completion
requires exposing native status/account and an authenticated route to that pilot only.

Follow-up 2026-11-02: owner opened Explorer and the authenticated OneDrive website.
A used the existing Chrome UI to find the exact harmless pilot in its expected vault
folder and download it; UI showed Done/2095B. The fresh download target, private
preserved copy and current canonical file match the original SHA-256. Active website
account matches local Personal account by normalized digest; configured root agrees.
Only this pilot was downloaded; no permission/account/sync changes or unrelated notes
opened. Cloud-byte gate PASS for this pilot/time; native global health/pause/errors
and continuous synchronization are not established. Private proof receipt retained.

Final native check 2026-11-02: B independently navigated only the exact pilot
parent in Explorer, observed Available on this device for that file and Backed up
and synced in the read-only Personal OneDrive cloud-storage popup. No note was opened
or settings/account/files changed. Together with A cloud/account/hash proof this
completes T12 at the recorded time, with no continuous-sync guarantee.

Bootstrap follow-up 2026-11-04: Main downloaded exactly four approved root files as
one archive and system/brain.md separately through the owner's existing OneDrive
browser session. Both showed Done. All five sizes/hashes match the approved payload
and current canonical files; before/after local hashes unchanged. Browser account
CID/local Personal account and local vault root match. Independent review verified
the supplied copy artifacts, exact archive members and receipt/metadata pins; browser
origin/account/completion remain Main-observed. Point-in-time five-file cloud byte
check PASS, not continuous sync or current native global health. Receipt SHA-256
`e84a9a07e5f48945968589c7e1653dd17e4f1badbb41c5c0ae41bb8c54e1372a`;
private handoffs/2026-11-04-bootstrap-cloud-review.md SHA-256
`9ea5cc941a26798badd1ef1f9d43714132b520bff9eddd3398f246c2a7b1a93f`.
No uploads, cloud/canonical edits or unrelated note-body access.

## T13: Demonstrate the ChatGPT desktop round trip

- [ ] Complete. Owner: B. Dependencies: T04, T09/T10, T11 approved client scope.
      Estimate: 30-60 minutes. Scope: S.

Acceptance:
- [ ] Actual target ChatGPT desktop surface saves a supplied harmless session summary
      through the shared operation and retrieves it from a fresh authorized session.
- [ ] Cross-client recall observes the same canonical knowledge and privacy policy;
      desktop success is not presented as web/cloud or Claude proof.
- [ ] If unsupported or unauthenticated, exact blocker/workaround is recorded and the
      capability remains pending; no silent hosting, new service or scope expansion.

Verification: real client tool calls and canonical/receipt hashes; no raw chat import.
Likely repository file (1): docs/client-compatibility.md; private host config/evidence.

## T13a: Regular Chat recall and zero-cost connection

- [ ] Complete. Owner: Main; review uses disjoint ownership before delegation.
      Depends on existing managed reader, approved recall specification and an
      authenticated connection proven to add no charges. Scope: one recall surface.

Acceptance:
- [x] Inspect current implementation: the managed MCP server exposes exactly two
      read-only tools over stdio; adding a skill name cannot supply Chat transport.
- [x] Record owner report: ChatGPT Plugins exposes Add custom MCP server.
- [x] Owner approved [recall specification](../docs/chat-recall-spec.md) on
      2026-11-05; source/synthetic work only, live connection remains separately gated.
- [x] Implement and independently review the synthetic OAuth/JSON HTTP source slice.
      Main and reviewer each passed 23 focused tests on the refrozen source; the
      author recorded 242 full-suite tests, 239 passed and three skipped. The CLI
      startup-failure cleanup finding is resolved; no service or tunnel was started.
- [ ] Establish target-account eligibility, a verified connection and $0 additional
      transport/hosting/model cost; do not create keys, subscriptions or a listener
      from documentation-only evidence. Current Secure MCP Tunnel cost is unknown.
- [ ] Test search and five-line read against a disposable synthetic corpus first;
      prove authentication and bounded refusal without a live vault or private packet.
- [ ] Review exact runtime/package/connection scope before live enable; preserve
      current Work/CLI configuration and scope. Record the owner-authorized note
      subset and Chat processing scope instead of reusing a grant implicitly.
- [ ] In fresh regular Chat, discover the installed plugin/skill, perform actual
      search/read and verify the expected ID/hash/lines. A menu entry or Work
      success alone does not complete this task. Stop on managed refusal.
- [ ] Verify removal/disable of only the added connection and preserve later edits.

Verification: synthetic tool/transport and negative-auth probes; frozen review;
then separately authorized regular Chat calls and supplied-artifact comparison.
No API Playground/model calls, additional credits or paid transport for testing.
Potential source files/commands depend on the approved spec and cost-gate result;
keep each implementation slice to at most five files.

Source checkpoint 2026-11-05: independent v2 review
`handoffs/2026-11-05-chat-recall-source-review-v2.md`, SHA-256
`4feed3dd8256a09b4c602bf028871ec236dc4231cfb5c86e34117cb4c5c27a5b`.
Main's unchanged cleanup probe now observes a closed provider and invalid token
after a mocked server failure. This does not describe a running service or tokens
surviving process exit. Full-suite quiet output reports three skips without naming
their individual cases. No new dependency, installed skill or configuration change.

The private `staging/chat-recall-20261105-v1/inactive-review-bundle-v1/` contains
eight runtime source copies and fictional payloads for review. Its disabled policy,
pending grant and incomplete connection are not executable activation inputs.
Actual helper/version/command, installed dependency checks, public origin, client
and exact callback remain unresolved. The supplied interface image confirms OAuth
and disabled advanced settings before URL entry; it proves no live connection.

Inactive bundle byte/metadata audit PASS: 24 listed files and eight runtime source
counterparts match; one synthetic note ID with empty prefixes and a separate denied
canary. Review `handoffs/2026-11-05-chat-recall-inactive-bundle-review.md`, SHA-256
`f862604c1bf7220773bab4dc4ad0548fece4adce8562bf326b7ee0e30c7e7e1a`.
This audit does not authorize execution or establish installed dependencies.

Documentation clarification 2026-11-05: the parent recall specification now names
search-first/returned-ID/initial-five-lines as caller workflow. Fixed grant
membership, 1-40 lines and 8000 characters remain server-enforced; there is no
per-token search-result authorization cache. A known enrolled ID can be read within
the approved grant without prior search. The final three-file source freeze and
v2 review remain unchanged; this is not a new implementation or live authorization.

Helper/runtime verification 2026-11-05: Main downloaded the official standalone
cloudflared 2026.10.7 Windows AMD64 asset, matched its release checksum, observed a
valid Windows signature and ran version/help only. No system installation or
tunnel startup. All 29 locked packages match installed versions; pip check passes.
Against exact lock-hashed PyPI wheels, 1537 installed payload files match; 1576
installed RECORD hashes also match. OSV and version-specific PyPI metadata return
no known advisories at this checkpoint. No package installs/upgrades occurred.
These checks exclude bytecode, extra files and packages outside the lock; they are
not a complete runtime or vulnerability attestation. Native pip-audit was absent;
the direct advisory-query method is recorded. Helper Go dependencies were not
independently audited. Source/contract/bundle pins remain unchanged.

Private evidence: `staging/chat-recall-20261105-v1/verification-v1/`;
report SHA-256 `26538e82f1fba10016fb2156b801aff67a24d86c4c0d7fcb666ce66a84cff1a6`.
Actual launch isolation, client/callback/origin, owner-code handling, recipient
approval and external synthetic/disable proofs remain pending.

Independent supplied-evidence audit PASS: all 40 verification artifact pins and
recorded package/wheel/advisory counts are consistent. Review
`handoffs/2026-11-05-chat-recall-helper-evidence-review.md`, SHA-256
`3a7ba03c46b75ca1fae83e621fd404dc01ad7fb3dda8c9d7ef229d9b49b8084d`.
This reviewer did not independently rerun signature, installed-file or network
queries; actual verification and download provenance remain Main-observed.

Connection preparation follow-up 2026-11-05: exact callback timing is unproved in
the actual UI. A separate discovery-only helper serves public OAuth metadata and
refuses all auth/token/MCP requests without reading bodies or loading notes. Final
source `393f6252...f0c1`, tests `0d8e2a6b...3384`; Main and reviewer focused7/7.
Main's private Host/Origin-removal mutation initially escaped weak assertions;
coordinated test-only correction now catches it (eight subtest assertions fail).
Independent v2 source review SHA-256
`d0e95ce0ad9bc1bf360f04a9fae001a8d0267c548cd103808629f137c3503b94`.
Author full249/246pass/3skip preceded those test-only assertion changes. No actual
discovery service or tunnel started. Earlier OAuth transport freeze is unchanged.

Main's disposable native Windows socket probe used a retained exclusive root socket
and a same-process duplicate supplied to actual Uvicorn. Nine independent competing
bind attempts failed before/during/after server activity; synthetic loopback response
and normal cleanup passed. This is a preliminary mechanism check, not complete
launcher, crash or external cleanup proof. Upstream helper source also initializes
Sentry and captures errors; a disable mechanism or explicitly reviewed diagnostic
recipient scope is required. Actual binary telemetry is unproved.

The bounded metadata-only launcher contract is independently reviewed; implementer
owns only its new launcher/test source slice, with exact schema naming delegated
within the contract. Preparation/Stage1 plan is documented in
[chat-recall-stage1-plan.md](../docs/chat-recall-stage1-plan.md). Runtime/package
review and owner approval are still required before any real helper launch. Stage1
excludes Create/Install/Connect/consent; stop if the UI requires those before showing
the public client/callback. No notes or active recall grant are part of Stage1.

Launcher first freeze remains NO-GO: imported focused14/14 and author full263
with three skips did not establish the literal CLI path. Main and reviewer
reproduced the entrypoint calling a later-defined function; Main also reproduced
an out-of-root synthetic file read before containment refusal. Required corrections
also cover private hold-state identity, actual process creation evidence and the
missing interrupt/collision/redirect/output lifecycle tests. Independent review
`handoffs/2026-11-05-chat-discovery-launcher-review.md` SHA-256
`b29689ede745b74dbcff11deafb13a2679ca1375ba1bbda3aa9cc0dcf34302c0`.
Reviewer paused/released only the launcher two-file freeze; Main explicitly released
that correction batch. Await new hashes before review. Existing discovery/OAuth
freezes stay unchanged, and no real tunnel or Chat connection has been started.

Later checkpoint supersedes that launcher NO-GO for the corrected source: final
launcher `8a8a82d7...06b7`, tests `db300cf6...5e7`; Main and reviewer each ran 30,
29 passed and one native symlink privilege skip. Author full279/275pass/4skip.
Five initial findings were resolved in v2; ready-while-alive handoff was added;
a deadline interleaving now cannot report success without emitting ready. Main's
private reintroduction of the old success predicate is caught by the new regression.
Independent final readiness review SHA-256
`e47c7bc8fca1f9b7b748ae95cc969a80aa0b53100889ce5944ec5d4d4b109b0f`.

The exact Stage1 metadata-only proposal is now prepared and independently audited:
27 payload pins and five toolkit source/test/lock counterparts match. Manifest
`82316daa80b67d5b09767f9c8e9f532df55aa2914d45a8bfbf6a12d0a2cdafd9`,
request `f8370e7c1497bf16c981567464e9a551f1d62f140bce76854c383e89fcfbe02b`;
package review `ea4541abd637b53f39afdaa276a33a462d42b191009e0450e7723c4e1c625a5b`.
Main's exact pending-script preflight returned1 with zero child-launch attempts
and no records. State remains PENDING_NOT_AUTHORIZED; no actual helper/tunnel or
Chat connection has run. Owner approval and independent active-copy comparison
are the next gate. The configured 900-second test exposes metadata only and names
Cloudflare/OpenAI/Sentry, including possible diagnostic/device metadata. It excludes
notes, grants, credentials, actual connection/consent and all recall/save operations.

## T13b: Explicit create-only saving from regular Chat

- [ ] Complete. Owner: Main. Depends on T13a and a separately reviewed save contract.
      This is future work; the existing MCP service remains read-only.

Acceptance:
- [ ] Summarize only the invoking Chat's available context; no other chats, raw
      transcript reads, second model call, background capture or broader export.
- [ ] Reuse the existing private staging and create-only publisher with a fixed
      approved host policy; no caller-selected roots, policies or approval hashes.
- [ ] Demonstrate bounded validation, identity/provenance, duplicate/replay,
      contention, refusal and partial-result reporting on synthetic material.
- [ ] Preserve no-clobber and recovery rules; do not enable T05 updates/linking.
- [ ] After exact live scope review, save one harmless outcome in regular Chat,
      then recall it from a fresh CLI and fresh regular Chat; verify hashes and
      check that note's cloud bytes. Keep earlier batch proof separately scoped.

Verification: meaningful focused synthetic tests, frozen source/package review,
then approved real Chat save-to-recall proof. Additional spending stays zero.

## T14: Timebox the existing Graphify integration

- [ ] Complete or explicitly deferred. Owner: B. Dependencies: C4; T12/T13 priority first.
      Estimate: at most 45 minutes. Scope: S. Optional for initial release.

Acceptance:
- [ ] Verify installed version's actual supported operations against documentation;
      attempt only an explicitly approved synthetic wiki/code sample with safe settings.
- [ ] If deterministic Markdown relationships are supported, prove rebuildable output
      and a related-note query; otherwise record the limitation and retain native
      wikilinks/authorized search without inventing a new graph framework.
- [ ] No external document model processing, private-note indexing, auto-refresh,
      watcher or graph output into canonical knowledge without separate scope approval.

Verification: observed graph/query or explicit NOT SUPPORTED/DEFERRED result with
command/version and no writes to canonical notes. Existing Graphify code proof alone
does not satisfy Markdown-graph integration.
Likely repository file (1): docs/graphify-local-demo.md; generated output stays private.

## C01: Validate the shared workflow in Claude Code when authorized

- [ ] Complete or explicitly deferred. Owner: B. Dependencies: T04, T10 boundary GO,
      T11 and separate Anthropic source/recall/write scope approval.
      Estimate: 1 hour plus account setup if needed. Scope: S. Conditional Day 3.

Acceptance:
- [ ] Verify the client's current documented setup; use the same canonical Markdown
      and toolkit operations with a separate client grant and explicit invocation.
- [ ] Demonstrate a supplied harmless save and fresh-session bounded recall; the
      publisher still enforces identity, policy and safe writes across both clients.
- [ ] No Codex/OpenAI consent is reused as Anthropic consent. Missing authentication,
      unavailable tools or failed probes leave Claude pending rather than claimed working.

Verification: actual authenticated client calls, source/receipt hashes and unchanged
unauthorized files. Client configuration/evidence stays private.
Likely repository file (1): docs/client-compatibility.md; ownership transfers to A for closure.

## T15: Publish an accurate local release status and next actions

- [ ] Complete. Owner: A. Dependencies: T10-T13 results; E04, T14 and C01 outcomes/defer noted.
      Estimate: 30-60 minutes. Scope: M.

Acceptance:
- [ ] User instructions cover the actual save/recall invocation, sync status,
      exceptions, disable/recovery and client availability; current docs agree.
- [ ] Per-capability results distinguish synthetic proof, live proof, pending tasks
      and the known skip. Unfinished items stay unchecked with revised estimates.
- [ ] No private evidence enters Git. Prepare reviewable changes for a later authorized
      commit/push/PR; do not perform repository publication from this task alone.

Verification: inspect final diff/status, check acceptance evidence and links. Rerun
tests only if new changes or unresolved concerns justify it after C4.
Likely files (5): README.md, docs/repository-status.md, docs/brain-save.md,
docs/brain-memory-release.md, docs/client-compatibility.md. A owns final doc integration.

### C6: Release status

- [ ] Ordinary explicit save/link/recall works in the approved live Codex scope.
- [ ] Conflicts/privacy/recovery behavior demonstrated; independent GO retained.
- [x] OneDrive exact pilot cloud match verified at a recorded time; B native status/availability also passed at that time; no continuous-sync guarantee.
- [x] Local app Work-session recall proof recorded separately from Codex CLI;
      explicit skill/command route only, not app-side save or hosted ChatGPT.
- [ ] Graphify outcome explicit.
- [ ] Historical coverage and Claude status recorded separately; private pilot and
      normalized records are not counted as live integrated knowledge.
- [ ] Owner sees completed/partial/blocked capabilities and next work, without routine
      note-by-note review. No unfinished capability is labelled complete.

## T16: Check wiki health without automatic repairs

- [ ] Complete. Owner: unassigned; Main assigns disjoint paths before implementation.
      Dependencies: T02a for source conventions, T05/T07 before enabling repairs.
      Scope: M, at most three source files; no watcher or background task.

Description: add an explicitly invoked read-only health report over a bounded,
authorized wiki subset. Prepare synthetic behavior before any live corpus access.

Acceptance:
- [ ] Synthetic fixtures identify broken links/anchors and orphan candidates, while
      intentional entry points and links outside the authorized subset are qualified
      rather than falsely declared broken. Preserve note identities and provenance.
- [ ] Stale-claim and contradiction candidates cite dated evidence and distinguish
      reported/inferred claims. Never claim semantic validation from structural lint;
      any model-based check needs its own applicable processing scope.
- [ ] Health reports make no canonical edits, enrollment or scope changes; proposed
      fixes go through reviewed T05/T07 behavior and approved scope. Document a
      repeatable manual check after a batch/update, without automatic capture.

Verification: focused synthetic positive/negative fixtures, unchanged-input byte
checks and denied-content canaries in report output. No full-vault scan or personal
indexing is authorized by this task. Live use requires its own bounded input scope.
Proposed files: scripts/wiki_health.py, tests/test_wiki_health.py,
docs/wiki-health.md; reuse existing checks where they cover the behavior.

## T17: One-repository installation and private-state migration

- [x] Complete. Implementation: scripts/install_toolkit.py, scripts/install.ps1, tests/test_installer.py.

Acceptance:
- [x] One reviewed repository release contains the complete runtime, skills,
      pinned dependencies, installer, inert templates and setup documentation.
      Resolve local untracked/modified release content before claiming clone parity;
      no commit or push is authorized by this checklist edit.
- [x] Setup selects the OneDrive vault and generates device-specific settings.
      Personal notes, secrets, grants and recovery state remain outside Git.
- [x] Restore/migrate required enrollment, policy, pointer and journal state from
      a private bundle; detect path/hash drift and preserve enrollment/recovery
      evidence. Do not silently repin approvals or adopt equal-byte files.
- [ ] Test a fresh Windows machine's installation, recall and one create-only save
      with independently checked evidence; distinguish simulated relocation from
      actual second-computer proof. A clone plus synced Markdown is not enough yet.
- [x] Remain within existing storage and ChatGPT allowances; no added paid service.
      Restrict publication to one device at a time until cross-device coordination
      is separately implemented and proved; OneDrive is not a distributed lock.

Verification: 16 focused unit tests in tests/test_installer.py pass; full regression suite (435 tests: 429 passed, 6 platform skips) verified green.

## Evidence ledger

| Task/checkpoint | Status | Commands/evidence reference | Remaining limits |
|---|---|---|---|
| Brownfield baseline | VERIFIED before planning | 96 tests: 95 passed, 1 skipped; tracked tree matches merged main | Live publication/OneDrive/ChatGPT not proved |
| E00 export preflight | VERIFIED 2026-10-31 | Local nested-archive inventory, JSON parse and in-memory normalize across all shards | Attachment/structured references dropped; no intake/synthesis/write |
| E01 | SOURCE COMPLETE | RED/GREEN regressions; 16 focused tests; B independent scoped GO | Not live publication or attachment recovery proof |
| T02 | SYNTHETIC TEMPLATES COMPLETE | B static checks and A source review | Host discovery/rendering/installation NOT RUN |
| T02a | SOURCE REFRESH COMPLETE | Five applied hashes independently matched; static content/link review passed | Reading view/discovery and live bootstrap NOT RUN |
| T02b | APPROVED LOCAL INSTALL / CLOUD COPY VERIFIED | Five exact creates/replay0; independent canonical byte checks; Main startup probe and five cloud downloads with independent artifact comparison | Point-in-time cloud bytes only; cross-project/other-client instruction discovery and crash/race limits remain; no ongoing updates/enrollment |
| E02 | PRIVATE INTAKE COMPLETE | Eight synthetic tests; B scoped GO and cap recheck; real intake/replay hashes agree | Normalized evidence, not synthesized/live knowledge |
| T04 | LOCAL RECALL / POINT-IN-TIME CLOUD PROOF | Native managed MCP search/read in current app and fresh CLI; earlier exact cloud-copy checks | App-side save, hosted ChatGPT and continuous sync not proved |
| Integration regression | PASS 2026-11-02 | 162 tests run: 161 passed, one existing native Windows symlink skip | Synthetic source/protocol proof; no installed-model/cloud claim |
| E03 | EXACT-FIVE LOCAL/CLOUD PILOT PASS | Private fidelity/static/rendering, approved creates/enrollment, native CLI/app recall and exact-five cloud download/hash match | Point-in-time cloud equality only; no full-history claim |
| T01/T03/T06 | SOURCE COMPLETE | Contract freeze, 18 publisher tests, bounded reader/MCP tests and two-publication real stdio roundtrip | Live activation, model proof and cloud remain pending |
| T08 | APPROVED LOCAL CREATE-ONLY PASS | Skills installed; current-session save and blind fresh Codex CLI recall/citation passed | Existing updates/linking and other clients excluded |
| T10 | SCOPED GO | Fresh independent review and final-fix probes on frozen source; release doc lists hashes | Create-only controlled pilot only, subject to owner activation |
| T11 | LOCAL PILOT PASS / FULL GATE OPEN | One new fictional note; NO_CHANGE replay; staging-only disable; fresh installed-reader recall; B local hash check | No full-vault baseline/canonical restore; maintained-wiki acceptance still open |
| T12 | POINT-IN-TIME PILOT PASS | A cloud/local hash and account match; B native Backed up and synced and exact-pilot Available on this device | No continuous-sync or other-client guarantee |
| T05 | FEASIBILITY GATE OPEN / UPDATES DISABLED | Frozen report and scoped API/evidence review; no guard source created | Continuous exclusion through atomic install and independent native reproduction unproved |
| E04, T07/T09/T13-T15, C01 | OPEN | Limits and next actions in release doc | Linking, history expansion and other-client integration pending |
| T16 | OPEN | Explicit bounded wiki-health acceptance added 2026-11-03 | No health implementation or live scan performed |
| Managed MCP local connection | ACTIVE / TWO HOSTS VERIFIED | Reviewed frozen package; source177run/175pass/2platform skips; current-app and fresh-CLI native calls | Existing enrolled corpus only; explicit CLI prompt, current Main app thread; later config drift preserved, exact added block matches |
| E03-H historical importer | APPROVED EXACT-FIVE LOCAL / RECALL / CLOUD PASS | Active-copy review;5creates/gen1, independent canonical bytes, NO_CHANGE replay; native CLI/app recall; five cloud sizes/hashes match approved manifest | Point-in-time cloud evidence only; no existing-note updates/aggregation |
| T17 installer & diagnostics | SOURCE COMPLETE / TESTED | scripts/install_toolkit.py, scripts/install.ps1, tests/test_installer.py: 16 tests pass, full suite 435 tests pass | Fresh second-machine physical verification pending |

## Updates

- 2026-11-10: Implemented single-command installer script (scripts/install_toolkit.py) and PowerShell wrapper (scripts/install.ps1) for T17. Enforces Python >= 3.11, discovers/validates OneDrive Obsidian vault path, validates pinned dependencies against requirements-mcp.lock, initializes local private staging workspace and inert templates (strict no-clobber), and performs comprehensive self-diagnostics. Added tests/test_installer.py with 16 passing tests; full test suite passes (435 tests: 429 passed, 6 skipped). Reconciled repository status and documentation for T15/T17.

- 2026-11-03: New Main acknowledged ownership and reconciled remaining milestones
  using using-agent-skills/planning-and-task-breakdown. Added T02a/T02b and T16,
  retained existing task IDs/completed evidence and clarified historical status
  precedence. This was documentation only; no new runtime tests, installed-setting
  changes, historical-source processing, canonical writes or broader grants.

- 2026-10-30: initial task list created for the owner's revised 1-2 day, two-terminal,
  reuse-first sprint. OneDrive cloud verification is a required completion gate.
- 2026-10-31: revision 2 adds completed E00 inspection, E01-E04 export/wiki tasks,
  conditional C01 Claude validation and the 2-3 day schedule. Initial assignments are
  A=E01 and B=T02; no implementation task was marked complete by this planning edit.
- 2026-10-31: owner authorized continuing parallel implementation. A and B exchanged
  explicit path ownership/ACKs. E01 and T02 source work completed; E02 loader is under
  final boundary verification before private intake. No commit, push or live activation.
- 2026-10-31: E02 actual private intake/replay complete and CE1 passed. T04 metadata
  preflight recorded; runtime proof remains open. E03 bounded source proposal is
  pending authorization; its creation does not grant access or complete compilation.
- 2026-10-31: owner approved the exact E03 packet for this OpenAI conversation; A
  compiled and locally validated five private candidate notes. The grant was recorded
  separately without changing source privacy. No B source access, live publication,
  fresh-session retrieval or OneDrive claim was implied.

- 2026-11-02: A/B continued in parallel with acknowledged ownership and a code freeze.
  Create-only publication, managed recall and source skill integration passed the
  combined 162-test run (161 passed, one existing skip). Fresh independent scoped GO
  followed two verified fixes. Live installs, canonical policies/grants and vault
  changes remain inactive; a concrete create-only activation proposal is prepared.

- 2026-11-02: owner approved the concrete create-only installation/write/recall/metadata
  and harmless pilot scope. A activated frozen skills/runtime with private backups;
  one canonical fictional note, replay, disable and blind fresh Codex CLI recall pass.
  B independently confirmed local pilot hash. Native health/cloud equality remain
  unverified/blocked; no broader provider grant, existing-note update, Graphify or Git action.

- 2026-11-02: after owner opened OneDrive windows, A downloaded only the harmless
  pilot through authenticated Chrome UI. Exact cloud/local/private-copy bytes match;
  active account digest matches local Personal identity. Cloud gate passed for this
  pilot/time. Native global health remains separate; no settings/permissions changed.

- 2026-11-02: B independently completed native Explorer status/availability check
  after foreground handoff. Combined native/account/cloud-byte evidence closes T12
  for the exact pilot at a recorded time. No further OneDrive setup was required.


- 2026-11-04 revision15: official CLI/URI completes exact private E03 reading-view
  checks; independent supplied-artifact audit passes. Reviewed managed MCP package
  is active for the existing approved corpus in current app and fresh CLI. Source
  suite177/175pass/2platform skips; independent focused2/2 pass. Later host-config
  drift outside the exact added server block is preserved; old conditional rollback
  must refuse. Historical import/enrollment and existing-note updates remain open.
  See docs/client-compatibility.md for exact evidence and host limits.


## Historical exact-five cloud verification, 2026-11-05

Main downloaded only the five approved historical notes through authenticated
OneDrive Chrome UI. The project archive contained exactly two approved notes, the
source archive exactly one; engineering and log notes were selected individually.
All five downloaded sizes and SHA-256 hashes match the approved import manifest.
Private receipt: activations/historical-import-20261104-v1/
cloud-verification-2026-11-05-v1/receipt.json, SHA-256
`181eecf37c0e02dddc190655fc47cfb07b5b843cfe25d73df799268eda4dfcc1`.

This closes the exact-five point-in-time cloud-byte gate. Browser origin/account
and download provenance are Main-observed; supplied-artifact independent review
is recorded separately. No continuous-sync, global health or cloud race guarantee
follows. No canonical edits, reimport, config/grant changes or provider expansion
occurred. Existing-note updates stay disabled; app-side save/full round trip,
broader historical import and actual canonical Obsidian rendering remain separate.
Earlier dated cloud-pending statements describe their historical checkpoint.

Independent supplied-artifact review PASS: private
handoffs/2026-11-05-historical-cloud-review.md, SHA-256
`f5d33a274727b2b1e39b798e312fda86589e7e2aa99d62f2d3ba0aca57a59219`. It verifies the receipt/manifest pins,
four raw artifacts, both exact archive member sets and five copies; it does not
independently reproduce browser provenance or live cloud access.

- 2026-11-05 revision21: owner requests regular Chat invocation and confirms the
  custom MCP menu exists. T13a/T13b added; zero additional spending and T17
  portability recorded. No Chat connection or live source/runtime change claimed.

- 2026-11-05 T13a source approval recorded. Main observed Personal Platform Tunnels
  page accessible/no tunnels; no price shown and no tunnel/key created. Free
  temporary Cloudflare transport is documented, but its relay recipient, OAuth
  correctness and Chat interoperability remain unactivated. See
  [synthetic transport contract](../docs/chat-recall-transport-contract.md).


### Stage1 execution checkpoint, 2026-11-05

Owner approved the exact metadata-only proposal; independent active-copy review
passed. Main ran one real 900-second temporary session. Two public discovery GETs
returned expected metadata, and three fictional MCP/auth/token checks refused.
The owner requested read-only screen inspection: a public callback was visible
before Create, with user-defined OAuth client and token auth none selected.
The form displayed a discovery error. UI evidence was recorded after the timer
ended; exact capture time is not independently pinned, so this does not establish
a discovery defect while serving or its cause. No Retry or second launch occurred.

Launcher exited zero with lifetime_elapsed and cleanup complete; owned child
creation identity matches. Subsequent old URL returned HTTP530. All 27 frozen
payloads remain unchanged. Main-recorded evidence is frozen privately; independent
artifact audit is pending. No Create/Connect/consent, notes, actual Chat recall or
saving, account association, config/Git change, or canonical access occurred.
Callback stability and actual authenticated interoperability remain open.


### Stage2 preparation checkpoint, 2026-11-05

Stage1 independent artifact audit passed (private review SHA256
84eefd86c28b00ccc0267d97ca97be5b3d36d016dd8bb98ddb1408453bc23026).
Owner requested preparation/review of a fictional-note authenticated connection.
The draft launcher contract sequences a construction-safe OAuth cleanup fix and
trusted per-operation immutable-fixture guard before the new bounded launcher.
Independent contract recheck is pending; no source release or second launch yet.
A separate two-note fictional fixture is staged with one allowed ID, empty prefixes,
disabled policy and pending grant. No pilot secret or enabled connection was created.
See [synthetic launcher contract](../docs/chat-synthetic-launcher-contract.md).

Contract recheck subsequently PASS on SHA256 a41652d186e0d006c07d1c379eb3ccc4c6c243c5747e88bddced6150dfe4a648
(private review 2960ec6918af573038c7e3a178da7eeadddc6e8da978683b8231977f305d1944).
Main released only HTTP source/tests Phase A for construction cleanup and the
trusted before/after reader guard. New launcher remains on hold until that frozen
source review. Inactive runtime/helper copies and draft scope are prepared; there
is no runnable/approved Stage2 profile, secret or external session.

Stage2 Phase A independently PASS: HTTP4da67315.../test22a77446..., 26 focused tests.
Private review SHA256 2dacefe63823eb6873cb2a9cc2465322820c9e66419a4918bc80a6f39c3dc750.
Main released only new synthetic launcher/tests Phase B; source/local work is ongoing.
No new external session, secret or real memory access.

Stage2 installed-environment clarification independently PASS on contract
64b11ac8a0adaa6a85f79dbae3a0c1596bc50406b7ec1163125a52a57cd304bd
(review f214ffda93b7a940d26edf7a8f0e040e04d20bbc9615de1a06a360b0fe4bac72).
Python/site/stdlib and installed dependencies are trusted pre-launch, not hermetic.
Main's first refresh used PATH global Python and found differences; the exact
pre-existing verified virtual-environment interpreter subsequently matched the
prior executable digest, all29 locked versions/1576 RECORD hashes and pip-check0.
No environment was changed. The final request must select that exact interpreter
by absolute path, and final tests use it. This invokes Python only, not Graphify.
Prior wheel/advisory and same-account/startup limitations remain explicit.

Stage2 Phase B candidate is frozen10f5e381.../db8a2b3a...; Main verified both
implementation/correction pins. Correct publish_memory pin is
bf992f30deb10a7503bd5598e088d349310afafa2e56d4d1a6e1e0ebf3e92bde.
Author reports36focused/318full(4skips); independent source review pending.
Counts alone do not attest exact interpreter. All live gates remain closed.

### Stage2 source PASS and inactive package checkpoint, 2026-11-05

Independent Phase B source/local review PASS, SHA256
5d75c60f82cb30dfab101ef0a7ee34777314e2dc97a50e8f4cb354fd506c247c.
Selected verified interpreter:36launcher/26HTTP/29discovery passed,1native skip.
The full318run/4skips remains author-reported, not independent evidence. CLI proof
uses test-only adapter and local Uvicorn, not real helper/Chat/account proof.

Main prepared an inactive45payload/14source-counterpart package. Manifest
20acd8db9d949684c680210a49ede9fca80bf494ca8aa6d03622aaa5e7f1415c, request
f459a9ed1c4b5a3a0796f5367a6441e518b4af7b088f3f3f9d70418f4e9804c9.
Independent package audit is pending. Exact one-note fictional scope, denied
canary, fixed callback/client, selected interpreter and trusted dependency evidence
are bound; policy disabled, grant/profile pending, connection disabled, no code.
Approval request proposes separately derived active copies and locally generated
43byte pilot code only after exact activation consent. No second tunnel, OAuth
connection, real-note processing, save/write, Git or config change occurred.

### Stage2 preparation complete: ready for exact owner approval

Inactive v2 package review PASS, SHA256 59f64c989370fb2dd164f857f4693332b3881d8c1be9f7bf912e4bbc1ce79f72.
All48payloads/14source counterparts match; all45v1 payloads and old manifest
remain unchanged. The only request correction explicitly enables only the separate
active policy after approval while pending policy stays disabled. Current manifest
075bf49f084a17b00ae432901738e1453db4b6ca41a393760e5ee13413d213ce, current request
d3291ce044c7f2a86ce94fa6e6520037c1e121cb99046f302e456c86a96f58f0.

No credential, active copy or connection exists. Next gate is exact owner consent
for one fictional-only15minute session, $0, Cloudflare/OpenAI/Sentry, followed by
independent active-input comparison. Owner operates Create/install/consent and
stops on callback/discovery/scope mismatch. Real-note access and Chat save remain
separate. Source/fixture proof does not establish actual remote/account behavior.


## T13 app priority: desktop and phone, 2026-11-05

- [ ] Obtain approval for the reviewed fictional-only desktop trial; independently compare active inputs and run the bounded test. Verify actual search and five-line read. Depends on owner approval.
- [ ] Establish phone-app connection availability and verify fictional search/read on the phone. Depends on a working desktop trial and any necessary reviewed scope.
- [ ] Prepare separately approved real-note recall and verify it independently in ordinary desktop and phone chats. Depends on fictional results and exact real-data authorization.
- [ ] Specify, implement and review create-only Chat saving; verify save and subsequent recall on each app under its approved scope. Depends on real recall and a separate save contract.
- [ ] Website-specific testing: deferred at owner request; retain as a future task, not a completion claim.

Checkpoint: record each actual app result and its limits; desktop success does not prove phone behavior. Existing terminal and Work access remain available; existing-note updates stay disabled.


### Stage2 first fictional trial, 2026-11-05

Owner approved the reviewed fictional-only trial and confirmed readiness. Active
metadata passed independent comparison. One authorized launcher invocation exited1
before ready; receipt reports child created, origin null and cleanup complete.
Cause is unknown because raw helper output was not retained. No Chat connection,
OAuth consent, fictional recall or real-note access was established. No automatic
retry; source-only diagnosis and independent artifact review requested.


### T13a startup diagnostic, 2026-11-05

- [x] Implement bounded nonsecret startup diagnostic fields and synthetic failure/cleanup coverage under the reviewed diagnostic contract.
- [x] Independently review frozen source and tests; preserve prior first-attempt evidence.
- [x] Prepare and independently review a concrete fictional-only diagnostic retry proposal.
- [ ] Obtain separate owner approval and independently review active inputs before another external session.

The first attempt cause remains unknown. Desktop and phone ordinary-Chat recall remain unverified.

Diagnostic v2 independent PASS: review SHA256 257c498681f9d21635bf1127cd16866c61a2f29aca303b3ee16ed655469e0416; launcher43/HTTP26/discovery29 passed, one native symlink skip. First failure cause remains unknown. No live retry.

Diagnostic retry package PASS: manifest e23ad266e9b3196a4aa17c892ed3dfac738a6d08a6ad35d2486397c77e622b84, review bb714c0a473d47b873fc75079b8b730c9092fe193b2be6b28707a835e0d5688e. No active copy, credential or retry.

Diagnostic proposal v2 independently PASS, review SHA256 236e478e6ea7faa89d2ba9b7a31084ff011c48ce1b22fc9e7f3ffa195321f967. Runtime checks are point-in-time; repeat before activation and independently review derived active inputs. Await separate owner approval; no retry.


### Diagnostic retry outcome, 2026-11-05

One separately owner-approved fictional-only retry stopped before ready. Main
observed exit1; the final receipt reports output_startup/guard_rejected, guard_failed
true, no recognized origin, EOF true, read_error false, child exit1 before and after
cleanup, and cleanup complete. The specific guard trigger and reason for child exit
are not recorded; their causal relationship is unproved. No Chat connection, OAuth
consent or fictional recall was completed. The recorded child PID was absent in
Main's point-in-time check. No automatic retry. Independent artifact audit and
source-only synthetic diagnosis requested; no real-note scope or saving activated.


### T13a guard-trigger diagnosis

- [ ] Implement and locally test bounded guard-failure categories while preserving acceptance and cleanup.
- [ ] Freeze all four changed source/test files and obtain independent review.
- [ ] Prepare and review an exact new fictional-only test proposal before asking for separate activation approval.

Past helper exit code and guard rejection remain observations without a proven cause. No live retry.


### Guard-diagnostic attempt, 2026-11-05

Owner continued and confirmed readiness. One fictional-only session reached ready;
Main metadata GET checks returned URLError without retained reasons, while a single
unauthenticated MCP request returned401 with challenge. Owner reported OAuth
discovery failure. Per approved stop condition Main stopped the exact owned helper;
launcher exited1 and reported cleanup complete, guard_failure_mask0. Child exit
4294967295 was observed after Main stopped it; do not attribute it to startup.
The old-origin check returned URLError; its cause and global teardown are unproved.
No Create, code entry, consent or recall was completed. Source-only diagnosis and
independent metadata audit requested. No automatic retry.


### T13a OAuth discovery investigation

- [x] Compare official discovery requirements with fictional local server/challenge and reproduce the checker exception mapping locally.
- [x] Implement and independently review a bounded redacted checker for a possible future test.
- [x] Prepare and independently review an exact inactive diagnostic proposal.
- [ ] Obtain separate owner approval, repeat runtime checks and independently review active inputs before a new external session.

Previous remote errors and actual ChatGPT request headers remain unknown; no host/callback restriction is relaxed based on speculation.

Discovery checker v2 independently PASS, review SHA256 68d96d2aec1548ea216b0ac0e6ac2ea81946b9a1b5d8ecfd2a35c2cd49547eea; 22 focused tests passed, one native symlink skip. Exact earlier failure and Chat request remain unknown.

Discovery proposal v4 package review PASS, SHA256 989395938584d12a70b975255ec4f720d8c627ecefd97869697effea8e85b301. Its checker is limited to Main network observations; actual Chat request and prior cause remain unproved.


### Discovery diagnostic attempt, 2026-11-06

Owner continued after the reviewed fictional-only diagnostic was presented and
confirmed readiness. Fresh runtime checks and independent active-input review passed.
One session stopped before ready; Main observed exit1, receipt reported cleanup
complete, guard_failure_mask4 (invalid candidate), no recognized origin and child
running at pre-cleanup poll. The later exit1 does not establish what caused the
invalid candidate or helper exit. No raw output, UI interaction, OAuth consent,
checker invocation or recall occurred. Source-only diagnosis and artifact audit
requested; no automatic retry. Prior sessions and records remain preserved.


### Desktop-first priority, 2026-11-06

- [ ] Complete the next reviewed fictional-note connection diagnostic for ordinary desktop Chat, subject to the separately requested test approval.
- [ ] Verify separately approved real-note recall in ordinary desktop Chat.
- [ ] Design and verify create-only saving in ordinary desktop Chat.
- [ ] Phone and website app verification: deferred for now, not removed.

Terminal/Work workflows are already available. Do not infer ordinary-Chat capability from Work or CLI tests.


### Desktop discovery test: callback mismatch, 2026-11-06

Owner approved one fictional-only session and confirmed readiness. Independent
active-input comparison passed; Main checker observed both metadata responses200,
unauthenticated MCP401 with matching challenge and all required booleans true.
Owner supplied a callback different from the pinned earlier callback. Main stopped
the exact owned helper under the approved stop condition; receipt reports cleanup
complete. No Create, credential entry, consent or recall was observed. Main's
post-stop check returned HTTP530; this is point-in-time evidence only.

This demonstrates the fixed callback cannot be assumed to match a newly opened
form. Exact callback allocation/stability and Chat discovery in that form remain
unproved. Investigate a documented callback approach before proposing any new
external attempt. Preserve old session evidence and do not repin a running server.

Fresh inactive package using owner-reported still-open-form callback passed metadata review 3f61aac289178ea27fb1d89abe5ff4d1cbd2305622896422ad18694d99ee9d42. Await separate owner approval; check callback again after new URL and stop if it differs. No live retry or source change.

### Supervised fictional desktop Chat trial, 2026-11-06

- [x] Implement and independently review bounded ready capture, launcher-owned stop requests, and supervised checker flow using fictional local tests.
- [x] Prepare and independently review a disabled fresh trial package (manifest SHA-256 2f1aab8304ef12cf7c61ca2d5be0ff335fd9735fb42444e75a9f9feb7e7e2985).
- [x] Run the approved grace-window fictional trial (`stage2-grace-20261106-v1`): ready and all seven discovery checks passed; form rotated callback to `m5ruZXOaQs1H`, so the session stopped cleanly before Create (`reason: stop_requested`, `cleanup: complete`).
- [x] Implement and review RFC 9207 OAuth issuer (`iss`) parameter and documented stable callback (`https://chatgpt.com/connector_platform_oauth_redirect`) support in `scripts/chat_recall_http.py` (`3c79f26169eb8ad5eb50de14665890fa260795c43beb0083e405725b9909b72f`) and `tests/test_chat_recall_http.py` (`062eb8007b6f5327c16f510926d3770b76d865ae88b22effacba6841da29a4e6`), with 389 full-suite passes and five platform skips.
- [x] Stage disabled stable-callback trial package `stage2-stable-callback-20261106-v1` (manifest SHA-256 `9f385740155aa16c0f2c92fb3dd0c61e1c254ef1f93ac5d2aa3d884d0fe8328f`, request SHA-256 `03bdc6474d9a11e10f940912ff431fd5c2b316c2d4c97f6e0607021b6bfa24a4`, 71 payloads).
- [x] Complete independent audit of `stage2-stable-callback-20261106-v1` (`handoffs/2026-11-06-stable-callback-package-review.md`, SHA-256 `7b92926ebfa676a883f42bf37183a16c6f43ab8fd87473f28e682f82a05e020b`, PASS: 71 payloads, 18 counterparts, 106 focused tests).
- [ ] Obtain separate owner approval for `stage2-stable-callback-20261106-v1`, derive and independently compare active inputs, then run one fictional-only trial and verify cleanup.
- [ ] Separately verify approved real-memory recall and design Chat-based saving.

Synthetic tests do not establish live Chat compatibility. Form callback and dependency freshness must be checked for the new session; failures stop before UI use. Hard supervisor failure falls back to launcher expiry and blocked synchronous startup can delay stop observation.

### Parallel Track B: T07 connected wiki knowledge and T16 wiki health checker, 2026-11-06

- [x] Implement and freeze T07 core module `scripts/wiki_memory.py` (`48184` bytes, SHA-256 `d17743108b11b6cdbe6190bd2aec66ef0730fb00ab09cfe5af4b74282a6c6d2c`) and `tests/test_wiki_memory.py` (`39145` bytes, SHA-256 `3b6469a5f6604b47681c862d54e111dcc1e4700e5747ef487e454796503a3c3f`) across five RED/GREEN TDD slices (15 tests: 14 passed, 1 Windows symlink privilege skip; `scripts/publish_memory.py` preserved at `bf992f30deb10a7503bd5598e088d349310afafa2e56d4d1a6e1e0ebf3e92bde`).
- [x] Complete independent adversarial review of T07 (`handoffs/2026-11-06-wiki-memory-review.md`, SHA-256 `a82469b3a18a48a769e5712ea44851a8a30e363668db51cfcfe0367a2abdf8da`, PASS with three caught in-memory mutations).
- [x] Implement and freeze T16 read-only wiki health checker `scripts/wiki_health.py` (`27895` bytes, SHA-256 `19b1a874597c8abf1a707d279340d8913b7b1485f72ec680a00fc408bd7934b3`), `tests/test_wiki_health.py` (`25481` bytes, SHA-256 `607e1aecb088105e91f4704c363dfa8598588f9564bbaae484487d5cf3c769ce`), and `docs/wiki-health.md` (`8023` bytes, SHA-256 `db062e5efebbc6f9801541cfef78cd732e8c6c45067e22a2832f183929364539`) across four RED/GREEN TDD slices (9 tests: 9 passed).
- [x] Complete independent adversarial review of T16 (`handoffs/2026-11-06-wiki-health-review.md`, SHA-256 `568085b12a1c07aa2334fb8fac614ba45ce44c37b8ddbb546ab4219ff27b1b6a`, PASS with three caught in-memory mutations).
- [ ] Wire `scripts/publish_memory.py` to T05/T07 after the current `T13a` desktop Chat trial package gate completes or is released, and obtain separate live canonical authorization before enabling updates/linking or live health scans.

Combined repository test suite now totals 413 tests (407 passed, 6 expected Windows symlink privilege skips).


## Security Hardening Tasks (2026-11-10 Audit)

- [x] Issue 1: Pin `chrome-devtools-mcp` dependency version to `@1.12.0` in `.agents/plugins/chrome-devtools/mcp_config.json` to prevent arbitrary untrusted code execution from npm `@latest` tag drift.
- [x] Issue 2: Pin exact dependency versions in `.github/workflows/ci.yml` (`mcp==2.3.0`, `pydantic==2.14.1`, `anyio==4.15.1`, `uvicorn==0.54.0`, `starlette==1.9.0`, `jsonschema==4.26.0`) for deterministic multi-python CI runs across Python 3.11, 3.12, and 3.13.
- [x] Issue 3: Prevent sensitive source references from leaking outside process memory by enforcing that `source_references` strings do not contain absolute paths (drive letters `[a-zA-Z]:` or UNC paths `\\`), root paths, directory traversals (`..`), or local file URIs, protecting provenance metadata across citation and manifest boundaries.

