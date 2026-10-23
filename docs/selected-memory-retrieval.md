# Selected Markdown retrieval

This small reader extends the earlier demonstration without relaxing the historical
four-note unpublished-preview reader. Markdown stays in its source vault. There is
no secondary memory database, embeddings, Graphify document processing, watcher,
Obsidian community plugin, automatic discovery, or publication operation.

The synthetic configuration and run evidence are machine-specific and remain in
the private workspace. Only synthetic material is currently approved for model
retrieval. The installed MCP dependency is reused from the existing isolated
Graphify environment; nothing new needs to be installed.

## Supported connection

Use local stdio MCP. Configure an absolute Python executable, `-B`, and the absolute
path of `scripts/selected_memory_mcp.py`. The server receives only these settings:

- `SECOND_BRAIN_GRANT`: absolute path of the fixed owner-reviewed grant JSON.
- `SECOND_BRAIN_GRANT_SHA256`: exact SHA-256 of that JSON, pinned separately.
- `SECOND_BRAIN_CLIENT`: `codex-openai` or `claude-anthropic`, matching the grant.
- `PYTHONDONTWRITEBYTECODE=1` and `PYTHONIOENCODING=utf-8`.

The server advertises exactly `search_selected_memory(query, limit=4)` and
`read_selected_memory(note_id, start_line=1, line_count=20)`. It returns source
paths, relative paths, SHA-256, line numbers, original source references and
Obsidian open URIs. A read is limited to 40 lines / 8,000 characters; search returns
up to four excerpts. Source references and wikilinks are not followed automatically.
An extra path argument accepted/ignored by the MCP SDK cannot expand the corpus.

## Grant format

```json
{
  "schema": "selected-memory-readonly-v1",
  "source_kind": "synthetic",
  "client": "codex-openai",
  "root": "<absolute disposable test-vault subdirectory>",
  "owner_authorization": {
    "state": "approved",
    "reference": "<actual owner instruction authorizing this synthetic test>",
    "personal_content_external_model_approved": false
  },
  "notes": [{
    "id": "rehearsal",
    "path": "decisions/rehearsal.md",
    "sha256": "<exact file hash>",
    "size": 123,
    "source_references": ["synthetic://fixture/rehearsal"]
  }]
}
```

Select 1 to 16 exact Markdown files. No globs or folder expansion. Synthetic roots
must be under `test-vault`; each synthetic note must have `privacy: "synthetic"`
in its YAML frontmatter. Changing any selected byte invalidates all results until
review/repinning. Linked paths, hardlinks, traversal, alternate streams, duplicate
IDs and case-insensitive duplicate paths are rejected. Ordinary OneDrive cloud
reparse points are distinguished from namespace redirection; no sync changes occur.

## Persistent Codex sessions

Current Codex supports named profile files at
`~/.codex/<profile-name>.config.toml`, selected with `--profile <profile-name>`.
Use a dedicated opt-in synthetic profile rather than relying on untrusted project
config discovery. This keeps the existing global defaults and trust settings intact.
The tested private profile includes the two-tool allowlist, required MCP startup,
read-only sandbox, no memories, no shell, no hooks/plugins/apps, and disabled
unrelated configured MCP servers. Its existing code-mode host stays enabled because
this CLI needs it for tool discovery. Tool read-only annotations alone are not a
security boundary.

Launch from a clean directory outside the live vault. Do not combine the profile
with `--ignore-user-config`: on the tested CLI this also bypassed the named profile.
Do not use `--strict-config` against the current shared desktop config: the CLI
rejects an unrelated app-owned field. Neither condition warrants rewriting the
desktop configuration. Normal profile loading is the tested route.

The evidence must show fresh thread IDs, actual MCP calls, the expected synthetic
answers/citations, successful turn completion, and unchanged source hashes. Exit
zero or a configured server entry alone is not retrieval proof. CLI proof does not
establish automatic loading in the current desktop chat or every arbitrary session.

## Later canonical-note authorization

Do not enable this during the synthetic phase. Before live model retrieval:

1. The owner names the precise notes, target provider/client and purpose. Publication
   approval is separate. Explain that selected excerpts sent through local MCP still
   enter that provider's model context and may appear in its session history.
2. The owner explicitly approves external processing of those personal note bytes,
   including a narrow exception to existing `external_processing: false` metadata.
   That metadata stays unchanged and remains the default for all other uses.
3. Locally record only approved relative paths, sizes and hashes in a new private
   grant with the canonical vault as `root`, `source_kind: "canonical"`, an actual
   approval reference, and `personal_content_external_model_approved: true`.
   The boolean records human consent; an agent cannot create consent by setting it.
4. Pin the grant hash in a separate opt-in profile for that provider. Do not copy
   notes to a second store. Keep startup disabled until the approved grant and
   exact scope have been checked. Do not automatically include START-HERE,
   source-register, referenced files, raw history, backups, or attachments.
5. Test retrieval and compare source hashes without changing live notes. Grant or
   note edits invalidate pins. Widening scope or updating hashes requires review;
   do not silently refresh. Revoke by disabling the server and marking the grant
   revoked; old pins also fail when its bytes change.

This reader is an application-level allowlist. It is not an ACL/firewall boundary
against unrestricted same-Windows-account agents. Shell-disabled sessions reduce
exposure through other tools but do not establish hostile-process isolation. A
strict OS boundary would require a separately constrained identity/process setup;
none is claimed or configured here.

## Claude Code reuse

Claude Code supports the same stdio command and environment. Use a distinct grant
with `client: "claude-anthropic"`; Codex consent never authorizes Anthropic. Prefer
`claude mcp add-json --scope local second_brain_synthetic '<server-object>'` in the
chosen project. Its local scope is stored under that project's path in
`~/.claude.json`, outside version control. The server object contains `type:
"stdio"`, absolute `command`, `args`, and the same `env` keys. A private JSON example
is supplied with the run evidence; the same synthetic note files can be reused.

Claude project scope instead uses `.mcp.json` and requires project server approval;
user scope applies across projects. Claude Code MCP is separate from the chat-only
Claude Desktop configuration. Check `/mcp`, then request an actual source-linked
answer in a new session. This machine's Claude Code runtime/authentication has not
been tested or installed by this task. Do not claim Claude integration from the
Codex test or a valid JSON example.

## Verification

```powershell
& .\.venv-graphify\Scripts\python.exe -B -m unittest discover -s tests -v
```

The tests cover stale notes/grants, authorization/client mismatch, personal content
mislabeled synthetic, path attacks, hardlinks, unselected content, read bounds and
unchanged bytes. Canonical-mode tests use synthetic fixtures only. Protocol tests
and fresh-model evidence are stored privately, never pushed with this repository.
Complete ChatGPT-history import remains a separate task pending the official export.

Official references:

- https://learn.chatgpt.com/docs/extend/mcp?surface=cli
- https://learn.chatgpt.com/docs/config-file/config-advanced
- https://code.claude.com/docs/en/mcp
- https://obsidian.md/help/Linking%2Bnotes%2Band%2Bfiles/Internal%2Blinks
