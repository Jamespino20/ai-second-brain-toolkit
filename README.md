# AI Second Brain Toolkit

Local tools for importing evidence, drafting reviewable Markdown and retrieving
explicitly selected notes. The existing Obsidian vault remains the canonical memory
store. This repository contains reusable code, synthetic tests, inert configuration
examples and attributed format skills; personal notes and histories stay outside Git.

## Current capabilities

| Component | Status and limits |
|---|---|
| Selected Markdown reader + stdio MCP | Operational on synthetic fixtures; returns paths, lines, hashes and references. Two fresh Codex CLI sessions were demonstrated before repository preparation. |
| Canonical/live retrieval | Implemented mode tested with synthetic files only. Personal-note model access still requires exact per-file, per-provider owner consent. |
| Legacy four-note preview reader | Operational locally for its historical unpublished-preview format; not the current canonical-note integration. |
| Explicit importer / rollout capture | Local parsing, byte archives, branch/date provenance and disposable drafts tested. No watcher or automatic session capture. |
| Opt-in CLI outcome capture | Fresh synthetic `codex exec` runs stage source-linked proposals automatically; repeat/replay, failures and disable tested. Desktop/native hooks remain inactive and untested. See [capture MVP](docs/automatic-capture-mvp.md). |
| Full ChatGPT history import | Parser exists; complete account import remains pending the official export and coverage review. |
| Backup helper | Synthetic snapshot/restore tested; no independent cloud or account-level recovery guarantee. |
| Graphify | Optional experimental code intelligence; pinned 0.9.92 AST-only synthetic demo. No personal-document indexing. |
| Claude Code | Same stdio interface documented; authenticated Claude retrieval remains untested. |
| Memory Manager / automatic writes | Blocked or unimplemented; never enabled by this repository. |

See [component inventory](docs/repository-status.md) and
[read-only retrieval](docs/selected-memory-retrieval.md) for exact boundaries.

## Install and verify

Windows with CPython 3.13 is the tested environment. Core import/reader tests use
the standard library. No installation command connects a vault or a model.

~~~powershell
py -3.13 -m venv .venv
& .\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
~~~

For the optional local MCP transport, install the existing pinned dependency set:

~~~powershell
& .\.venv\Scripts\python.exe -m pip install --index-url https://pypi.org/simple --require-hashes -r requirements-mcp.lock
& .\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
~~~

Without MCP, the protocol test reports SKIP. With MCP, it exercises the real stdio
transport using disposable synthetic notes. The lock targets Windows/CPython 3.13;
other platforms and a fresh installation were not validated during this preparation.
Graphify has a separate [installation and pinned lock](docs/graphify-local-demo.md).
An existing `.venv-graphify` can run these tests without reinstalling anything.

## Configure deliberately

Start with [inert examples](examples/README.md). Put actual paths, grants, selected
note hashes and client configuration in a private directory outside this repository.
The policy-only `config.example.json` is documentation, not a settings file consumed
by the scripts. The MCP reader takes its fixed grant through environment variables;
the model cannot supply a new corpus path through its tools.

Codex synthetic retrieval is demonstrated through an explicit opt-in profile;
automatic loading in every desktop session is not established. Claude Code uses the
same stdio server with its own client-specific grant and configuration. These local
connections still send returned excerpts to the chosen model if enabled. A private
GitHub repository, a read-only annotation and content publication approval do not
grant model access or provide OS isolation against same-account processes.

## Reference first, review before publication

Reuse established formats and interfaces before adding mechanisms. Preserve source
identities, unknown dates, branch history, truncation and attachment gaps. Keep
current implementation truth in project repositories and reviewed memory in Obsidian.
Graphify graphs and demo indexes are derived, disposable aids.

References: [Obsidian Skills](https://github.com/kepano/obsidian-skills),
[Graphify](https://github.com/Graphify-Labs/graphify), and the
[Claude memory setup reference](https://github.com/lucasrosati/claude-code-memory-setup).
Pinned provenance, retained licenses and the distinction between reference and copied
material are listed in [THIRD_PARTY.md](THIRD_PARTY.md).

No publisher, background capture, external processing, GitHub upload or live-vault
write is activated by setup. Keep raw conversations, backups, credentials and runtime
outputs outside Git even for private repositories. See the
[publication procedure](docs/github-publication.md) before any first commit or push.
