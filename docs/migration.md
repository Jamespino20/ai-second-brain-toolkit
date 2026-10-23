# Session-to-memory migration

Ingest evidence locally; do not bulk-copy chats into permanent memory. A full raw
archive stays private, outside the vault and repository and outside ordinary search.
Do not put API keys, passwords, or recovery credentials into drafts or the vault.

For every source, record original session ID/title/date/link where available,
speaker, message/turn/node identity, capture date, exact-byte hash, capture method,
original/excerpt/summary status, branch/page limits, attachment limits, and privacy.
Never use capture time as an unknown event date. User statements, assistant claims,
reported tests and independently observed outcomes are different evidence classes.

Draft small records using the frozen metadata: schema_version, id, kind,
review_state, created, updated, as_of, privacy, scopes, sources, supersedes. The
staging JSON also contains claims with evidence classifications and exact locators.
New material defaults to personal with external processing denied. The lightweight
staging checks are not the blocked manager's schema validator or a security boundary.

Review in this order: meaningful decisions and current blockers; dated project
milestones; reusable engineering lessons; owner-stated working preferences; learning
and personal facts only with appropriate source/privacy review. Do not promote an
assistant inference into a biographical fact or a user preference.

Deduplicate by original source ID plus immutable content hash. Preserve distinct
events, branches, pages and revisions. Semantic overlap prompts review; it never
authorizes an automatic merge. Status updates carry applicability dates and explicit
replacement links; keep earlier status as history rather than silently editing it.

Use the approved folders. Project repositories remain authoritative for current
implementation. `projects/` holds rationale/status/repository pointers; `logs/` holds
short session records; `permanent/` holds reviewed reusable knowledge. Raw histories
stay outside all of these. `inbox/` in the live vault remains manager-controlled;
ordinary agents submit candidates to the external private staging location.

## Smallest missing-source action

- For one placeholder answer: open that named original conversation, copy only the
  missing user/assistant exchange to a local UTF-8 text/Markdown file with role labels,
  session link, and date if shown. Supply that local file for explicit adapter intake.
- For an unsupported Codex history: provide its local session export, or its final
  report plus the exact owner request. A report is an excerpt, not the whole session.
- For broad account coverage: obtain the owner's ChatGPT data export locally and
  point intake at `conversations.json`. Do not upload the account ZIP to a repository
  or external processor. A generic account export is not guaranteed to include every
  workspace/provider/attachment. Compare exported IDs against the private manifest.
- For Claude Chat/Work/Code: no connection is implied. Supply only the selected
  owner-exported conversations/session files; inspect the format before adding an adapter.
- Attachments are missing unless their actual bytes are separately supplied and
  verified. A path or placeholder is not attachment content.

Review exact contents before any live use. Today the minimum next step is source
completion or content review, not another architecture assessment. A future manual
owner placement of exact new files is a separate action; it does not certify the
blocked publisher, supersession, isolation or OneDrive concurrency behavior.
