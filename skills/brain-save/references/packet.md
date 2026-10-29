# Adapter input

JSON, maximum 32 KB. Exactly these top-level fields:

```json
{
  "schema": "brain-save-context-v1",
  "role": "reviewer",
  "coverage": "visible-context",
  "items": [{
    "kind": "test",
    "text": "The focused test command reported one failure; no fix was applied.",
    "status": "reported-failed",
    "actor": "this-session",
    "support": "visible-tool-output",
    "references": ["visible python unittest command: exit 1"]
  }],
  "artifacts": ["tests/test_example.py"]
}
```

- role: planner, implementer, reviewer, mixed, unknown.
- coverage: visible-context, compacted-context; full transcript is never asserted.
- kind: decision, work, test, lesson, blocker, next-action, review.
- status: reported-completed, reported-passed, reported-failed, proposed, blocked, unknown.
- actor: this-session, other-session, unknown.
- support: visible-tool-output, visible-user-message, artifact, inference, unsupported.
- references: 1–4 strings per item, up to 400 characters; text at most 1,200 characters.
- artifacts: 0–8 safe relative project text/source paths. No credentials, .git/.codex, external paths or transcript files. Leave empty if unnecessary.

Use proposed for next actions and unexecuted tests. Reported results require visible support. Planners/reviewers cannot claim completed implementation work by this-session; use decision/review or attribute other-session correctly. A reviewer may report tests actually run in this reviewer conversation. All supplied conversation claims remain summary-derived (or inferred); local file hashes are independently checked separately. If roles change substantially, use mixed and preserve actor distinctions. Source references are annotations, not a promise that a whole transcript was archived or independently authenticated.
