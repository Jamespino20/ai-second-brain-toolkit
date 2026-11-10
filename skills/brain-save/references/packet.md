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

## Optional host publication settings

The five-field packet stays unchanged. Policy paths, hashes, destinations, grants and
manifest pointers must never be packet fields or model-chosen arguments.

An independently approved host configuration may add `publication_policy` and
`publication_policy_sha256` to the installed skill's existing `local.json`. Preserve
`python`, `adapter`, `private_root` and other local settings. This source package does
not install the update, edit local settings or grant canonical writes.

When both optional values are absent, use the existing staging command unchanged.
If exactly one is supplied, report incomplete settings; do not invent a pin or
silently omit the configured publication request. With both present, append
`--policy $settings.publication_policy --policy-sha256 $settings.publication_policy_sha256`
to the same adapter invocation. The adapter imports the publisher only after staging.

The output keeps the actual staging receipt at top level and adds `publication` only
when requested. Duplicate-stage receipts still allow a previously unpublished proposal
to be published. Publication success/NO_CHANGE/DISABLED exit 0; REFUSED, BUSY, PARTIAL
or QUARANTINED exit 2. Staging failure keeps the original safe-error behavior. On a
publication failure after staging, retain stdout's staging receipt and nested result;
do not replace it with a claim that staging failed or nothing was written.

Publication counts represent confirmed work. PARTIAL with PUBLICATION_STATE_UNCERTAIN
and zero confirmed saves does not establish zero actual writes. Do not retry conflicts
or change policy to force success. Publication is local with sync UNVERIFIED; recall
requires its separate client/provider grant. Canonical operations currently support
only the publisher's implemented scope, not automatic updates or linking by implication.
