# Graphify and read-only preview retrieval

Historical report for the 19 October 2026 demonstration. Approval, backup and
integration status below describes that run, not the current project state. See
[current component status](repository-status.md) and
[selected-note retrieval](selected-memory-retrieval.md) for the later implementation.

Verified on Windows / CPython 3.13, 19 October 2026. This is a disposable local
demonstration, not Memory Manager, publication, or full lifecycle acceptance.

## Installation

Official upstream: https://github.com/Graphify-Labs/graphify
The distribution is `graphifyy`, not similarly named PyPI packages.
The official README permits pip installation; use a dedicated environment:

```powershell
python -m venv .venv-graphify
& .\.venv-graphify\Scripts\python.exe -m pip install --index-url https://pypi.org/simple 'graphifyy[mcp]==0.9.92'
& .\.venv-graphify\Scripts\python.exe -m pip check
```

`requirements-graphify.lock` records the exact installed dependency versions and
official wheel hashes. For an equivalent fresh environment:

```powershell
& .\.venv-graphify\Scripts\python.exe -m pip install --index-url https://pypi.org/simple --require-hashes -r docs\requirements-graphify.lock
```

The official project setup command is:

```powershell
& .\.venv-graphify\Scripts\graphify.exe install --project --platform codex
```

On this pin that command also writes an AGENTS.md block and a PreToolUse hook.
Those automatic additions were removed after the observed installation; the
upstream project skill and reference files remain under `.codex/skills/graphify/`.
Do not blindly rerun the installer and reactivate automation. The current repository
AGENTS.md explicitly restricts Graphify to manual, supplied code-only inputs.
Upstream licenses and notice are retained under THIRD-PARTY-LICENSES/.

## Manual code-only extraction and repository queries

Point these commands only at an explicitly approved synthetic development repository.
Never use the private workspace, transcripts, reviewed notes, or live vault as input.

```powershell
$env:GRAPHIFY_BACKEND = 'none'
$env:GRAPHIFY_NO_AUTO_REFRESH = '1'
$env:GRAPHIFY_QUERY_LOG_DISABLE = '1'
& .\.venv-graphify\Scripts\graphify.exe extract $demoRepo --code-only --no-cluster --max-workers 1 --out $demoOutput
$graphFile = Join-Path $demoOutput 'graphify-out\graph.json'
& .\.venv-graphify\Scripts\graphify.exe query 'submit_order' --graph $graphFile --budget 1200
& .\.venv-graphify\Scripts\graphify.exe path 'run_demo' 'total_price' --graph $graphFile
& .\.venv-graphify\Scripts\graphify.exe affected 'total_price' --graph $graphFile
```

The actual demo used a sparse child environment without provider credentials and
a Python audit guard that blocks outbound sockets and non-Python/git subprocesses.
The guard self-test rejected a deliberately attempted external DNS lookup. Windows
asyncio loopback socketpairs are allowed for local MCP stdio operation. This is
application-level instrumentation, not a firewall or hostile-process OS isolation.
No elevated permissions or network settings were changed.

Observed graph: four Python files, eight nodes, thirteen edges; one synthetic
Markdown document excluded. Verified call path:
`run_demo -> submit_order -> total_price`. Reverse-impact traversal includes
`submit_order`, `run_demo`, and their importing modules. Every edge is AST-derived
and carries source file/line evidence. No clustering or semantic extraction ran.

## Four-note retrieval, separate from Graphify

The corrected reviewed preview is the corpus; the earlier test-vault candidates and
SQLite demo index are historical. The source Markdown and approval dates are not
changed. No Markdown is given to Graphify or a semantic model.

```powershell
& .\.venv-graphify\Scripts\python.exe -B scripts\read_memory.py --manifest $previewManifest --manifest-sha256 $approvedManifestHash --query 'H-04'
```

This local lexical reader validates the exact manifest hash and all four file hashes
before returning excerpts, note IDs, line numbers, source references and approval
state. It accepts no arbitrary file-reading or write operation. Changed manifests,
changed notes, path escapes, and unapproved material are refused. Unselected files
are never scanned. It has no network client, model call, index write or publication
operation. This read-only API is not an ACL boundary against same-account processes.

Optional local protocol transport:

```powershell
$env:SECOND_BRAIN_PREVIEW_MANIFEST = $previewManifest
$env:SECOND_BRAIN_PREVIEW_SHA256 = $approvedManifestHash
& .\.venv-graphify\Scripts\python.exe -B scripts\memory_mcp.py
```

It advertises only `search_staged_memory`. A deterministic MCP client tested all four
notes plus a no-match query, and a publication tool call was rejected. The Graphify
MCP separately passed graph_stats, query_graph and shortest_path calls on synthetic
code. These are real protocol calls; no new Codex model session was launched.

Machine-specific MCP configuration is in ignored `.codex/config.toml`. The private
memory server is intentionally disabled for model sessions because external
processing permission is absent. The synthetic graph entry allows only read tools.
Codex 0.160.1 accepted the exact entries via invocation overrides; automatic
project-file discovery was not established by `codex mcp get`. No global MCP or trust
configuration was changed. Do not claim an active desktop integration until a fresh
approved session actually loads and calls it.

Private demo evidence and the exact machine commands stay in the separate private
workspace. No raw material, private note text, or private path is committed here.

## Checks and deliberately pending work

```powershell
& .\.venv-graphify\Scripts\python.exe -B -m unittest discover -s tests -v
```

The ten migration regressions plus six read-only retrieval checks passed. This does
not accept H-04 or any publisher/access-isolation requirement. Independent off-disk
backup and live publication approval remain pending. Watchers, automatic capture,
external model integration, Graphify document semantics and automatic rebuilds stay
disabled. The live vault is not accessed by this demonstration.
