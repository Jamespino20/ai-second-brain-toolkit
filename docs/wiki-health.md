# Bounded read-only wiki health check (`scripts/wiki_health.py`)

Status: T16 source and synthetic verification slice. No watcher, background job,
full-vault directory scan, model-based semantic validator, or automatic repair is
authorized or enabled by this tool.

## Purpose and scope boundaries

`scripts/wiki_health.py` runs an explicitly invoked, read-only structural lint pass
over an owner-approved, hash-pinned subset of Markdown notes (`wiki-health-manifest-v1`).
It reports:

1. **Broken internal links** (`broken_links`) within the authorized subset or declared
   `subset_prefixes`.
2. **Missing heading anchors** (`missing_anchors`) when a link targets an authorized
   note (or the same note via `[[#Heading]]`) whose ATX headings do not match the
   requested anchor.
3. **Orphan candidates** (`orphan_candidates`) for notes in the authorized subset that
   receive zero incoming links from other authorized notes in the subset.
4. **Qualified entry points** (`entry_points`) so intentional entry/navigation notes
   (`AGENTS.md`, `CLAUDE.md`, `index.md`, `log.md`, `system/brain.md`, nested
   `*/index.md`, or manifest entries with `"entry_point": true`) are recorded as
   `intentional_entry_point` rather than falsely flagged as orphans.
5. **Qualified external links** (`external_links`) for links pointing outside the
   authorized subset (`status: "external_to_subset"`,
   `qualification: "unverified_outside_subset"`). Unselected files are never opened,
   probed, or `stat`-checked on disk.
6. **Structural contradiction and stale-claim candidates**
   (`contradiction_candidates`, `stale_claim_candidates`) extracted from structured
   claim lines or YAML frontmatter claim fields, preserving source note identity,
   line number, SHA-256, `source_references`, ISO date (or `"unknown"`),
   `claim_basis` (`reported`, `inferred`, `quoted`, `observed`, or `unspecified`),
   and `actor`/`role` (`owner`, `assistant`, `reviewer`, etc.).

Every report sets `"analysis_kind": "structural-lint"` and
`"semantic_validation": false`. Structural lint checks link targets, heading slugs,
and explicit claim key-value markers only; any future model-based semantic check
requires its own separately approved processing scope.

## Callable and CLI interface

### Python callable

```python
from wiki_health import check_wiki_health

report = check_wiki_health(
    manifest_path="/abs/path/to/health-manifest.json",
    manifest_sha256="<64-hex-sha256>",
    client="codex-openai",
    as_of_date="2026-11-06",  # optional YYYY-MM-DD reference date for stale_after checks
)
```

### Command-line invocation

```powershell
python -B scripts/wiki_health.py `
  --manifest "C:\path\to\private\health-manifest.json" `
  --manifest-sha256 "<64-char-lowercase-hex-sha256>" `
  --client codex-openai `
  --as-of-date 2026-11-06
```

- Exit code `0`: manifest and all selected notes passed integrity validation; JSON
  report (`wiki-health-report-v1`) is written to `stdout`.
- Exit code `2`: fail-closed refusal (manifest/note hash drift, unauthorized client
  or owner state, path traversal, symlink/junction/reparse point, hardlink, duplicate
  JSON key, or oversized file); structured refusal reason is written to `stderr`.

## Manifest schema (`wiki-health-manifest-v1`)

```json
{
  "schema": "wiki-health-manifest-v1",
  "source_kind": "synthetic",
  "client": "codex-openai",
  "root": "C:/path/to/test-vault/synthetic",
  "owner_authorization": {
    "state": "approved",
    "reference": "synthetic-t16-check",
    "purpose": "wiki-health-structural-lint",
    "personal_content_external_model_approved": false
  },
  "subset_prefixes": [
    "projects/alpha/"
  ],
  "notes": [
    {
      "id": "index",
      "path": "index.md",
      "size": 142,
      "sha256": "<64-hex-sha256>",
      "source_references": [
        "synthetic://fixture/index"
      ]
    }
  ]
}
```

### Security and validation guarantees

- **No directory scan**: only the exact `notes` array in the hash-verified manifest is
  opened. Maximum `256` notes per manifest; maximum `128000` bytes per note; maximum
  `1048576` bytes for the manifest.
- **No symlink, junction, reparse, or hardlink traversal**: reuses
  `selected_memory.checked_path` across every path component and requires
  `st_nlink == 1` on regular files.
- **Synthetic vs canonical isolation**:
  - `source_kind: "synthetic"` requires `test-vault` in the root path and
    `privacy: "synthetic"` in every selected note's YAML frontmatter.
  - `source_kind: "canonical"` requires
    `owner_authorization.personal_content_external_model_approved === true`.
- **Pre/post read verification**: the manifest and every selected note's bytes are
  re-verified before returning the report so concurrent mutations fail closed.

## Report schema (`wiki-health-report-v1`)

| Field | Type | Description |
| --- | --- | --- |
| `schema` | `"wiki-health-report-v1"` | Fixed report schema identifier |
| `mode` | `"read-only-wiki-health"` | Read-only execution mode |
| `analysis_kind` | `"structural-lint"` | Explicit non-semantic lint marker |
| `semantic_validation` | `false` | Never claims semantic or factual truth |
| `canonical_side_effects` | `"none"` | No canonical or private files are modified |
| `repairs_applied` | `0` | Health checker performs zero automatic edits |
| `repair_routing` | `"T05/T07 reviewed workflows required"` | Required route for any follow-up fix |
| `authorized_note_count` | `int` | Count of hash-verified notes inspected |
| `notes` | `list[dict]` | Full citations (`note_id`, `path`, `relative_path`, `sha256`, `source_references`, `obsidian_uri`) |
| `broken_links` | `list[dict]` | Missing targets within the subset and missing anchors on authorized targets |
| `missing_anchors` | `list[dict]` | Links whose target note is in the subset but lacks the `#heading` anchor |
| `orphan_candidates` | `list[dict]` | Non-entry-point subset notes with `incoming_link_count == 0` |
| `entry_points` | `list[dict]` | Intentional entry points qualified with `intentional_entry_point` |
| `external_links` | `list[dict]` | Links outside the subset qualified with `external_to_subset` / `unverified_outside_subset` |
| `contradiction_candidates` | `list[dict]` | Conflicting structural claims grouped by `subject`, preserving `claim_basis` and `actor` |
| `stale_claim_candidates` | `list[dict]` | Claims superseded by newer dated claims, explicit `superseded_by`, or `stale_after` |

## Repeatable manual workflow after a batch or update

Run a health check manually after a reviewed batch or note update without enabling
any background watcher or automatic capture:

1. **Pin the authorized subset**: in the private workspace (outside Git and outside
   the vault), record the exact `wiki-health-manifest-v1` JSON listing only the
   approved notes for the check, along with each file's byte size and SHA-256.
2. **Compute the manifest pin**: record the SHA-256 of the manifest file.
3. **Invoke `scripts/wiki_health.py` explicitly**: run the CLI command above and
   inspect the JSON output in the terminal or redirect it to a private receipt file
   outside the vault.
4. **Review findings with provenance**:
   - Check `broken_links` and `missing_anchors` against the cited `note_id`, `line`,
     and `sha256`.
   - Confirm `external_links` are expected cross-scope references (not errors unless
     the target scope is separately enrolled and checked).
   - Inspect `contradiction_candidates` and `stale_claim_candidates` using their
     recorded `date`, `claim_basis` (`reported` vs `inferred`), and `actor` fields.
5. **Route any proposed repairs through T05/T07**:
   - Do **not** edit canonical notes directly from an automated health check.
   - Any proposed link fix, index/hub addition, or existing-note claim update must go
     through the reviewed T05 (contextual linking / hub maintenance) or T07
     (controlled existing-note update and conflict handling) workflow under an
     explicitly approved write policy and scope.
