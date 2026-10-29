# Save from the current Codex conversation

In an existing local Codex conversation, send:

```text
$brain-save
```

Codex extracts up to eight essential decisions, work/test reports, lessons, blockers,
review observations and next actions from its available context, then invokes the
local adapter once. No separate Codex/model session, handoff copy or transcript
export is involved. The reply gives STAGED, DUPLICATE_SOURCE,
NO_MEANINGFUL_OUTCOMES or a safe refusal code and, when applicable, the proposal path.

## Install once

The user-scoped installation applies across projects without editing project
settings or global config. This machine's existing `~/.agents/skills` junction
points to `~/.codex/skills`; these are the same installation, not two copies.
The source package is in `skills/brain-save` so it does not create a duplicate
project-scoped skill with the same name.

```powershell
$tools = Join-Path $env:USERPROFILE 'Documents\AI-Second-Brain-Tools'
$skill = Join-Path $env:USERPROFILE '.agents\skills\brain-save'
if (Test-Path -LiteralPath $skill) { throw 'Already installed; inspect before replacing' }
Copy-Item -LiteralPath (Join-Path $tools 'skills\brain-save') -Destination $skill -Recurse
$settings = @{
    python = 'C:\Python313\python.exe'
    adapter = Join-Path $tools 'scripts\save_interactive_memory.py'
    private_root = Join-Path $env:USERPROFILE 'Documents\AI-Second-Brain-Private'
}
[IO.File]::WriteAllText((Join-Path $skill 'local.json'), ($settings | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
```

This installation was performed and tested during implementation. `local.json`
contains machine-specific paths and stays outside Git. The private root must
already have the existing `.private-staging.json` marker denying live writes and
external exports. No package installation or new database is required.

The skill has `allow_implicit_invocation: false`: it runs only on explicit mention.
Codex normally detects skill changes; if an existing session does not list it, use
`/skills` or explicitly mention the installed SKILL.md path once. Some clients need
a reload/restart for discovery. This does not authorize reading session histories.

## Roles, evidence and parallel sessions

- Infer planner/implementer/reviewer/mixed/unknown from the current task; do not
  relabel another session's implementation as this reviewer's work. Reviewers may
  report tests they actually ran and completed review observations.
- Only visible context is summarized. Compacted/truncated context is labeled;
  neither mode claims full transcript fidelity. Tool/message references are kept
  when available, with readable context locators otherwise. Never fabricate IDs.
- Host-provided CODEX_THREAD_ID/CODEX_SESSION_ID are used opportunistically, not
  treated as an authenticated public API. Their match to the actual thread was
  verified in the disposable test. Without them, the adapter creates an explicitly
  labeled invocation ID; it does not invent a real thread ID, and cross-invocation
  deduplication cannot be promised in that fallback.
- Project, session and role scope the immutable saves. Parallel roles/sessions
  have separate paths; same-scope identical source returns DUPLICATE_SOURCE with
  zero new proposals. Changed context/artifact bytes create a new candidate.
- Conversation claims remain summary-derived or inferred, including model reports
  of visible commands. The adapter independently hashes only selected safe project
  artifacts; this proves current bytes, not authorship, execution or correctness.
  It does not manufacture a CLI completion receipt for an interactive summary.

The adapter reuses existing privacy filtering, frozen candidate validation and
Markdown rendering. Suspect inputs fail before archival/rendering, including quoted
JSON credential assignments. Do not include raw dialogue, secrets, personal contact
details, personal absolute paths or unrelated information. Filtering is heuristic;
it does not make raw personal context safe by itself.

## Staging, review and disable

All data stays under the configured private root:

```text
archive/<hash>.brain-save-context.json
staging/brain-save/<project>/<session-role>/<hash>/candidate.json
staging/brain-save/<project>/<session-role>/<hash>/receipt.json
test-vault/logs/brain-save/<project>/<session-role>/<hash>.md
```

The archive is the exact normalized summary packet and artifact hashes, **not the
conversation transcript**. Candidates keep `review_state: candidate`, personal
privacy, engineering scope and `external_processing: false`. No publisher, indexer,
capture watcher or connector is invoked. Missing/tampered cached evidence is refused,
not repaired silently. Existing renderer boilerplate still says demonstration;
that generic label does not turn real session summaries into synthetic evidence.

Review the returned Markdown and references. Accept/reject outside the immutable
records; publication still needs separate approval. To stop, simply do not invoke
the skill. For removal, move only the installed brain-save folder out of the skill
search path after saving needed settings; staged proposals remain private.

## Host permissions and desktop

The current session needs a local execution tool and permission to write the
configured staging folder. A strict Planning/read-only session may need a narrowly
scoped write approval, or may be unable to stage until the host permits it. The
skill never bypasses that boundary, enables shell tools, or starts another model.
The former no-tool pilot profiles deliberately disable capabilities needed here.
OneDrive project roots/internal Codex directories and credential/history artifacts
are refused by this adapter. Normal local project folders are supported.

In the Codex desktop local project workflow, use its skill selector/explicit skill
mention when available. ChatGPT-style composers may use `@` selection instead of
CLI `$` syntax. The desktop terminal runs the same CLI invocation. CLI same-thread
behaviour was tested; this change does not claim a Windows desktop UI interaction
test, automatic desktop-session capture, or cloud-only execution support.

## Future hooks — assessed, not enabled

Official local Stop/SessionEnd hooks could later append small local event records.
Stop is turn-oriented; SessionEnd is advisory and may fire only after close/archive
or idle, not immediately on chat switching. Hook transcript_path may be null and
its file format is unstable. A hook alone cannot recover model reasoning or turn
an incomplete transcript into verified memory. A future adapter would need separate
authorization, lightweight bounded writes, privacy handling and deduplication;
none was installed here. Do not run a long model extraction from SessionEnd.

Sources: [official skills](https://learn.chatgpt.com/docs/build-skills),
[official hooks](https://learn.chatgpt.com/docs/hooks).

## Verification

```powershell
& .\.venv-graphify\Scripts\python.exe -B -m unittest discover -s tests -v
```

The implementation run completed 96 tests: 95 passed, one native Windows symlink
case skipped for unavailable creation privilege. A real disposable CLI conversation
ran a synthetic review in turn one, then received only `$brain-save` on turn two
of the same thread. Its generated proposal preserved reviewer identity, an actual
failed test result and a proposed/unimplemented fix. No fixture files changed.
Private transcripts/evidence, machine paths and local settings are outside Git.
