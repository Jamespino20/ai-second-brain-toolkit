# Specification: regular Chat explicit saving

Module: chat-save. Task: T13b. Date: 2026-11-10.
Status: IMPLEMENTATION DRAFT for owner review under the stated
zero-additional-cost and scope gates. Build order: chat-recall -> chat-save.
Related scope/order: [Chat capabilities](chat-memory-capabilities.md), [Chat recall spec](chat-recall-spec.md).

## Objective and assumptions

The owner can explicitly request Second Brain note staging from an ordinary ChatGPT
Desktop conversation, without switching to Work or running a secondary CLI session,
using an authenticated Model Context Protocol (MCP) tool connection.
Staged notes are create-only candidate proposals placed in private staging; they do
not overwrite existing notes, do not perform automatic vault linking (T05 remains
disabled), and do not modify canonical or historical files without separate authorization.

Assumptions:
- Target client is the owner's ChatGPT account with custom MCP plugins enabled.
- Additional service budget remains hard-capped at $0 beyond the owner's existing ChatGPT Plus plan.
- The transport reuses the same local HTTP ASGI server, OAuth 2.0 PKCE boundary,
  and transport security implemented for chat-recall (T13a).
- Staging reuses the existing private staging infrastructure from `scripts/save_interactive_memory.py`
  and candidate validation/rendering from `scripts/migrate.py`.
- No raw conversation transcripts, model background capture, or multi-chat scanning occurs.

## Cost and connection gate

Hard requirement: $0 additional spending beyond the existing ChatGPT Plus subscription.
- No separately billed model API usage or token credits.
- No third-party paid relays, paid tunnel services, or paid hosting.
- Bounded strictly within the local loopback transport and owner-authorized OAuth 2.0 PKCE session.
- If included usage or connection privileges expire, saving pauses fail-closed.

## Interface and boundaries

The MCP server exposes an explicit create-only tool `save_chat_memory` (and alias `save_memory`)
on `_RedactedServer` in `scripts/chat_recall_http.py`.

### Tool definition: `save_chat_memory` (and `save_memory`)

Tool annotations:
- `readOnlyHint`: `False` (stages new candidate proposals).
- `destructiveHint`: `False` (create-only; strictly no-clobber and no deletion).
- `idempotentHint`: `True` (replaying identical arguments returns cached receipt without side effects).
- `openWorldHint`: `False` (bounded to fixed local private root).

Parameters:
- `title`: `str` (required, 1–120 characters).
  Concise title for the note proposal. Validated against path traversal (`..`), path separators (`/`, `\`),
  control characters, and reserved filesystem characters (`:*?"<>|`).
- `text`: `str | None` (optional, up to 16,384 characters/bytes).
  Primary body content of the note proposal. Must provide either `text` or `summary`.
- `summary`: `str | None` (optional, up to 16,384 characters/bytes).
  Alternative summary content if `text` is omitted.
- `tags`: `list[str] | None` (optional, at most 16 items).
  Topic tags (1–40 alphanumeric/dash/underscore characters each; duplicates rejected).
- `metadata`: `dict[str, str] | None` (optional, at most 16 entries).
  Key-value string pairs (keys 1–40 chars, values 1–200 chars).
- `kind`: `str` (optional, default `'session'`).
  Must match an approved candidate note kind: `'session'`, `'decision'`, `'lesson'`, `'project'`, `'plan'`, or `'reference'`.

### Model-facing output

Successful staging returns a structured result without leaking private filesystem paths:
```json
{
  "status": "STAGED",
  "note_id": "brain-save-0123456789abcdef0123456789abcdef",
  "title": "Architectural decision on caching",
  "sha256": "0123456789abcdef...",
  "proposal": "test-vault/logs/brain-save/chat/abcdef.../0123456789abcdef.md",
  "proposals": 1
}
```

Duplicate replay returns:
```json
{
  "status": "DUPLICATE_SOURCE",
  "note_id": "brain-save-0123456789abcdef0123456789abcdef",
  "title": "Architectural decision on caching",
  "sha256": "0123456789abcdef...",
  "proposal": "test-vault/logs/brain-save/chat/abcdef.../0123456789abcdef.md",
  "proposals": 0
}
```

On any validation error, security tripwire, or IO failure, the tool refuses fail-closed
with `ToolError('MANAGED_SAVE_REFUSED')`. No stack traces, file paths, or private data
are leaked to the caller.

## Guardrails and security

1. **Input sizing and bounds**:
   - Title: 1 to 120 characters, non-empty after trimming.
   - Content: maximum 16 KB (16,384 UTF-8 bytes and characters).
   - Tags: maximum 16 items, each 1–40 chars matching `^[A-Za-z0-9_-]+$`.
   - Metadata: maximum 16 entries, keys 1–40 chars, values 1–200 chars.
2. **Path traversal & character checks**:
   - Titles are strictly forbidden from containing `..`, `/`, `\`, null bytes, control characters, or `:*?"<>|`.
   - Tags and metadata keys must be alphanumeric identifiers.
3. **Privacy heuristics**:
   - `privacy_check()` is applied to `title`, `content`, `tags`, and `metadata` to intercept accidental credential leaks.
4. **No-clobber and locking**:
   - Output paths are checked for symlinks or junctions (`REDIRECTED_OUTPUT`).
   - Exclusive locking (`.lock`) protects concurrent save operations.
   - Archive and candidate files are written with atomic exclusive flags (`xb`), preventing clobbering.
5. **No direct vault overwrites or T05 updates**:
   - Notes are staged under `staging/brain-save/` and rendered into `test-vault/logs/brain-save/chat/` as disposable candidates.
   - T05 linking and update logic is not invoked.
   - External processing remains explicitly denied (`external_processing: False`).
6. **Error redaction**:
   - `_RedactedServer` catches all exceptions during save calls and raises `ToolError('MANAGED_SAVE_REFUSED')`.

## Backend staging architecture

Staging reuses the primitives established in `scripts/save_interactive_memory.py`:
- Private root is strictly derived from the verified grant file (`grant['private_root']`); callers cannot select roots.
- Archive envelope `brain-chat-save-archive-v1` captures the raw input and provenance hash.
- Candidate note conforms to `brain-candidate-v1` metadata verified by `validate_candidate()`.
- Markdown representation is rendered via `render()` with candidate warnings and YAML frontmatter.
- Exact content hash deduplication prevents duplicate proposals.

## Verification and test strategy

Unit tests in `tests/test_chat_save.py` verify:
1. Valid note staging and candidate generation.
2. Idempotent replay returning `DUPLICATE_SOURCE` with 0 proposals.
3. Sizing bounds (16 KB content, 120 character title, 16 tags/metadata).
4. Refusal of traversal sequences (`..`, `/`, `\`) and forbidden characters in titles.
5. Refusal of credentials and sensitive patterns via `privacy_check`.
6. Concurrency lock contention and cleanup.
7. Redaction of all exceptions to `MANAGED_SAVE_REFUSED`.
8. Protocol integration via JSON-RPC over the authenticated MCP route.
