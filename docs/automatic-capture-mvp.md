# Opt-in Codex capture MVP

Verified on Windows, 2026-10-24: Codex CLI 0.164.0 and CPython 3.13.
This launcher automatically stages a review proposal at the end of an explicitly
requested CLI run. It does not monitor existing chats or publish memories.
There is no new dependency or canonical memory database. Obsidian stays canonical.

## Supported mechanisms and evidence limits

| Mechanism | Official support | Evidence here |
|---|---|---|
| `codex exec --json --output-schema ... --output-last-message ...` | Documented noninteractive interface | Real synthetic fresh runs, exact repeat, replay, and process failure exercised. |
| `Stop` command hook | Documented; Windows command overrides supported | Not installed or tested here. Runs per completed turn, not a reliable whole-project acceptance signal. |
| `SessionEnd` command hook | Documented advisory lifecycle event, synchronous, 3-second timeout | Not installed or tested here. Chat switching does not imply immediate session end; close/archive/delete and idle behavior matter. |
| Local Codex desktop / local Work hooks | Documented local support, with hook trust review | Actual Windows desktop event firing and delivery not tested. Do not claim the CLI demonstration proves desktop integration. |
| Cloud orchestration hooks | Local configuration/command/plugin hooks unsupported, even with a local executor | No cloud capture adapter enabled. |
| Hook `transcript_path` | Nullable; transcript file format explicitly unstable | No polling, internal rollout discovery, or transcript parser used by this MVP. |
| ChatGPT conversation lifecycle capture | No supported ChatGPT completion hook established in this work | Separate owner-selected intake or official account export, followed by coverage review; no automatic account scraper. |

Sources: [official hooks](https://learn.chatgpt.com/docs/hooks),
[noninteractive CLI](https://learn.chatgpt.com/docs/non-interactive-mode), and
[cloud/local access](https://learn.chatgpt.com/docs/enterprise/cloud-local-access).
Hook activation requires reviewing exact command trust through the supported hook
UI. This MVP neither bypasses trust nor changes global hook settings. Hooks remain
a possible later adapter; a long model call must not be placed inside SessionEnd.

## One opt-in workflow

1. The owner selects an existing private staging root and exact permitted working
   directory. Copy `examples/codex-capture-config.example.json` outside Git, replace
   placeholders, and review a dedicated Codex profile. The example is disabled.
   Pin the exact profile bytes in `profile_sha256` (PowerShell `Get-FileHash -Algorithm
   SHA256`, lowercase result). Missing or changed profiles refuse before launch.
2. Prepare an owner-authored request file inside that private root. Launch the run
   below. The launcher checks paths and common disclosure patterns before starting
   Codex. It appends reporting instructions and supplies the fixed JSON schema.
3. Codex performs the requested single run and returns up to eight outcome,
   decision, lesson, or milestone items. No second model/summarizer is invoked.
4. The local validator requires process exit 0, exactly one started/completed turn,
   and a final report matching an actual completed agent-message event. Top-level
   errors, failed turns, and item errors after turn start reject capture. This CLI
   also labels startup warnings as error items: those preceding turn start are
   counted in the receipt and retained in raw evidence, not silently discarded.
5. Valid candidates render with the existing frozen frontmatter and source contract
   into the disposable test vault. Review and publication remain separate actions.

```powershell
# Run from the existing tools repository. Replace all uppercase placeholders.
python -B scripts/run_codex_capture.py --config PRIVATE_CONFIG run `
  --cwd EXACT_APPROVED_PROJECT --prompt-file PRIVATE_REQUEST --timeout 300
python -B scripts/run_codex_capture.py --config PRIVATE_CONFIG replay `
  --run-directory PRIVATE_RUN_DIRECTORY
python -B scripts/run_codex_capture.py --config PRIVATE_CONFIG disable
python -B scripts/run_codex_capture.py --config PRIVATE_CONFIG enable
python -B -m unittest discover -s tests -v
```

`run` starts a fresh `codex exec` with the selected `--profile`, `--ephemeral`,
`--skip-git-repo-check`, exact `--cd`, `--json`, `--color never`, fixed
`--output-schema`, fixed `--output-last-message`, and stdin request. It accepts no
arbitrary CLI passthrough. `replay` processes only that recorded run, without
launching a model. It requires the same config, allowed cwd, and unchanged source
hashes. Resume, interactive sessions and multiple turns are outside this MVP.
The final answer is the structured memory report, rather than an unrestricted
task write-up. Intermediate CLI output stays in private logs. Keep using ordinary
Codex for sessions that need a different final-answer format; this MVP does not
silently change those sessions.

The private root must already have `.private-staging.json` with `live_writes:false`
and `external_exports:false`. The existing root is reused. Configuration must be
inside it; root must be outside Git/OneDrive. File links, junctions, redirected
ancestors and hardlinked configured files are refused. Cwd is an exact allowlist,
not recursive authorization. Never select the live vault as cwd.

## Working profile

The private synthetic demonstration uses an explicit named profile with the
currently configured model, read-only sandbox, approval `never`, web disabled,
history persistence `none`, project document budget 0, no root markers, and
memories/apps/plugins/hooks/shell/multi-agent/computer/browser/image/skill search
disabled. Every installed MCP server is individually disabled in that profile.
The installed host's existing code-mode host is retained for compatibility;
the captured event stream verifies that no tool calls occurred in these runs.
The exact machine profile and configuration are preserved in private evidence.
No global config or existing retrieval profile is edited.
The selected file is `$CODEX_HOME/<profile>.config.toml`, or the default
`~/.codex/<profile>.config.toml`; [official configuration layering](https://learn.chatgpt.com/docs/config-file/config-basic)
still applies. A negative test found that a missing profile silently falls back
to defaults in this CLI. The launcher now prevents that with an existence/hash
check before launch and another check before staging. This does not pin every
inherited configuration layer; owner review of base policy remains necessary.

A profile governs Codex tool access. The launcher's cwd allowlist is **not** an OS
access sandbox. Review inherited settings, providers, tools, instructions and all
MCP entries before using another profile; newly installed servers need review too.
The synthetic profile is not a personal-content authorization. A real project
rollout requires owner-approved scope and a reviewed existing-provider profile.

## Private artifacts and provenance

All paths below are relative to the selected private root:

```text
staging/codex-capture/runs/<uuid>/
  prompt.txt             Original request, excluding appended reporting instructions
  events.jsonl           Exact CLI JSONL stdout
  final.json             Exact structured final response
  stderr.txt             Private diagnostics
  job.json               Execution state, hashes, result or safe error code
archive/<sha>.codex-events.jsonl
archive/<sha>.codex-final.json
archive/<sha>.codex-prompt.txt
staging/codex-capture/receipts/<source-sha>.json
staging/codex-capture/candidates/<content-sha>.json
test-vault/logs/codex-capture/<content-sha>.md
```

Markdown claims link to the archived event hash, exact JSONL line, message item,
and report-item index. Raw prompt and final hashes are in receipts/job evidence.
Reconstruct the sent request by appending the versioned `REPORT_INSTRUCTIONS` to
the saved original prompt. The reviewer handoff pins the implementation bytes.

Only runner completion is directly observed. Literal request quotes can be
`user-stated`; that means present in the supplied request, not independently true
or endorsed third-party text. Other model assertions are `summary-derived`;
interpretations are `inferred`. Capture timestamps do not invent event dates.
Candidates remain `candidate`, `privacy: personal`, `scopes: engineering`,
`as_of: null`, and `external_processing: false`. Synthetic provenance is explicitly
retained in the candidate/receipt. This metadata prohibits downstream processing;
it does not claim that the originating Codex run was offline.

Exact source replay returns `DUPLICATE_SOURCE`. Equal report content from another
session returns `CONTENT_REUSED`: one immutable Markdown proposal, another source
receipt. Hashing ignores JSON object-key order but preserves item order/text/basis
and synthetic versus personal provenance. It is not semantic deduplication.
Changed reports are separate proposals. Existing edited candidates are never
overwritten; an empty report records `NO_MEANINGFUL_OUTCOMES` without a note.

### Focused R1 integrity correction

Receipts now pin archived events, final response, original prompt and complete
candidate bytes. Replay verifies all archived hashes and recomputes receipt
identity, source line/item, flags and report paths from the verified evidence.
Reuse also validates the first proposal's original source and staging receipt.
Every cached claim, evidence label, locator, source, body and fixed metadata field
must equal a candidate reconstructed from that original verified report. A cached
report digest alone does not validate its derived claims.

Missing or altered archives, receipts, candidate state or Markdown refuse replay
or reuse. Conflicting bytes are preserved; deleted cached Markdown is not silently
regenerated. Receipts predating these additional integrity fields are incomplete
under R1 and refuse; no historical private artifact is automatically upgraded.
Recovery requires separate review of the original evidence and exact-byte restore,
not deletion of conflicting records to force a success status.

## Privacy, failure and disable

The prompt and entire proposed report are checked for common token/private-key
patterns, secret assignments, email addresses, user home paths and JWTs. A report
failure rejects the batch before rendering. Filters are conservative heuristics,
not a general PII classifier or a replacement for owner review. Raw model output
and diagnostics can still contain sensitive data and remain private. There is no
additional external AI processor, embedding service, database or automatic grant.
Private local artifacts inherit normal filesystem permissions; no encryption or
same-account process isolation is claimed. Retention cleanup is owner-controlled.
Quoted JSON/single-quoted credential assignments and common ASCII JSON escapes
are checked in requests and each report field. Source identifiers are filtered
before entering a rendered locator as well. Shape/enum validation still rejects
unexpected input fields. Raw diagnostic-only material stays private and is not
promoted to memory by these checks.

Native Windows file-symlink creation can require unavailable privileges. An
environment-blocked symlink test is a SKIP, never a pass; a successful junction
probe is separate evidence and does not substitute for native symlink coverage.

Statuses are explicit. Console failures contain safe codes, not captured text.
Nonzero child exit, timeout (maximum 600 seconds), malformed output, tampering,
stale config and path violations produce no success receipt. Interrupted staging
may leave private partial candidate artifacts; do not treat them as success without
the completed receipt and validated source. Mutable job writes use atomic replace.
An exclusive lock serializes capture and refuses busy/stale locks. After a crash,
first confirm no launcher or child remains, preserve job/raw evidence, review the
lock and incomplete artifacts, then remove only the stale lock manually. Never
delete a lock to bypass another active run. No automatic destructive recovery.

`disable` atomically changes only the selected private config's `enabled` flag.
Disabled runs/replays do not launch or stage; disable during a running session
blocks staging after completion. It does not interrupt an already running model
or delete evidence. `enable` reverses it. This is not a global Codex-hook switch;
none is installed. Native hooks, if added later, have their own official disable
controls, including `[features] hooks = false`.

## ChatGPT and review boundary

Keep complete ChatGPT history intake separate while the official export is pending.
The existing importer accepts explicitly supplied `read_thread` captures and export
`conversations.json`; it preserves branches, unknown dates, gaps and unavailable
attachments. Those are source formats, not proof of complete account coverage or
permission to send histories to a model. Selected capture needs owner scope;
account export ingestion needs coverage and privacy review. This MVP installs no
ChatGPT connector, watcher or browser capture.

Synthetic CLI tests establish proposal plumbing and extraction, not production
memory quality, app lifecycle delivery or trustworthy self-reported work completion.
Independent review is pending. Do not commit, push, create a PR, enable hooks, or
start personal capture until the applicable owner approval.
