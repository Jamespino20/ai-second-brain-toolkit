# Components and readiness

Repository preparation changes documentation, exclusions, inert templates and a
portable protocol regression test. It does not enable a model or publish memories.

| Paths | Status | Evidence / remaining work |
|---|---|---|
| `scripts/selected_memory.py` | Operational synthetic retrieval | Fixed manifest/client/path/hash checks, bounded reads and source citations. Canonical mode is fixture-tested; live access needs separate consent. |
| `scripts/selected_memory_mcp.py` | Operational local stdio | Search/read only; deterministic protocol test. Earlier two fresh Codex CLI sessions succeeded. No fresh model sessions run for repository preparation. |
| `scripts/read_memory.py`, `memory_mcp.py` | Legacy operational preview | Exactly four historical unpublished notes; retained for compatibility. Private transport remains disabled for model sessions. |
| `scripts/migrate.py` | Experimental local importer and draft workflow | Synthetic parsing/replay/provenance/branch/draft/FTS tests. No account-completeness or blocked-publisher acceptance claim. |
| `scripts/capture_codex.py` | Explicit local snapshot helper | Stable supplied rollout bytes, dialogue extraction and evidence archive tested. Not automatic capture or a running session hook. |
| `scripts/run_codex_capture.py`, `capture_outcomes.py` | Opt-in CLI capture MVP | Supported JSON/schema interface; synthetic fresh-session extraction, repeats, replay, failure, unauthorized paths and disable exercised. Proposals only. Native/desktop hooks not installed or tested. See automatic-capture-mvp.md. |
| `scripts/backup.py` | Operational local snapshot helper | Synthetic bytes, hidden files, directories and restore checked. Source-path/root hardening and cloud independence are not generally certified. |
| `scripts/source_report.py` (local, ignored) | Account-specific legacy helper; excluded | Contains historical assumptions and private taxonomy. Preserved locally, not part of the proposed repository. |
| `config.example.json`, `examples/` | Inert templates | No credentials or real grant. Policy JSON is not parsed by the scripts. |
| `requirements-mcp.lock` | Existing pinned MCP dependency subset | Windows/CPython 3.13 closure derived from the existing Graphify lock. No package changes. |
| `docs/requirements-graphify.lock` | Optional pinned Graphify environment | Existing 0.9.92 demo pin, not a latest-version or vulnerability audit. |
| `.agents/skills/` | Vendored Obsidian format references | Markdown, Bases, Canvas. Pinned upstream and MIT notice retained. Skill discovery depends on host support. |
| `.codex/skills/graphify/` | Vendored experimental code skill | Upstream automation suggestions do not override AGENTS.md. No hook or watcher is enabled. |
| `tests/` | Portable synthetic regression suite | Core tests use stdlib. MCP protocol test runs when the optional dependency is installed; otherwise explicitly skips. |
| `docs/` | Maintainer guides and historical demo notes | Historical results are dated; private event logs and machine-specific profiles remain outside Git. |

The blocked custom Memory Manager is not implemented by these helpers. Automatic
background session capture, lifecycle write governance, attachment intake, complete-history
coverage, Claude adapters and authenticated Claude retrieval remain incomplete.
Read-only live retrieval and personal/background capture require separate scope and
approval; publishing this toolkit does not authorize either milestone.

## Layout retained

```text
.agents/skills/         Obsidian format references
.codex/skills/graphify/  Upstream manual code-intelligence skill
scripts/                Local Python tools and read-only MCP transport
tests/                  Synthetic tests, no personal fixture content
examples/               Placeholder configuration examples
docs/                   Contracts, status, provenance and procedures
THIRD-PARTY-LICENSES/    Preserved upstream license/notice texts
requirements-mcp.lock   Optional MCP dependency pin
config.example.json     Inert policy illustration
AGENTS.md               Agent scope and operating boundaries
README.md               Entry point
THIRD_PARTY.md           Attribution and pinned source roles
```

Private workspaces, notes, exports, source inventories, backups, grants, runtime
environments, local settings and test evidence are not repository contents.
