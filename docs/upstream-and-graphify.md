# Established references; no architecture restart

This records original reference review and historical Graphify preparation. See
[current component status](repository-status.md) for what is implemented now.

| Reference | Reuse here |
|---|---|
| [Lucas Rosati setup](https://github.com/lucasrosati/claude-code-memory-setup) | Consolidated atomic knowledge, separate concise session history, selective context, explicit import staging |
| [Obsidian Skills](https://github.com/kepano/obsidian-skills) | Pinned upstream Markdown/Bases/Canvas format skills; MIT notice retained |
| [Graphify](https://github.com/Graphify-Labs/graphify) | Optional local code graph; derived and rebuildable |

Lucas reference commit inspected: `62d0d0992c2aa6c553f60fc31a2b6afb24653e3c`.
Obsidian skill commit: `3ccff5338ea700537839b21900aa5358a0402c98`.
Graphify HEAD observed: `86c57be8204673c2a1b9849a3292a7dd3ab373d8`.
Do not import upstream folder structure, automatic hooks or broad vault permissions.
No upstream performance/token-saving claim was independently tested here.

## Graphify preparation — historical plan before the local demo

Update, 19 October 2026: Graphify 0.9.92 is now installed in an isolated environment.
Manual synthetic-code extraction, repository queries and local MCP protocol tests
passed. See [the implemented local demo](graphify-local-demo.md) for exact commands,
the separate reviewed-note reader and the unconfigured model-session integration.

Use an isolated environment outside OneDrive. The upstream distribution is named
`graphifyy`; the command is `graphify`. Upstream defaults have changed, so inspect the
pinned CLI and its current help before executing an extraction. The headless CLI
uses subcommands; slash-command options are not interchangeable with terminal flags.

For a later disposable smoke test:

1. Pin a reviewed Graphify release/commit and its dependencies in a local environment.
2. Copy only synthetic `.py` or `.ts` source files into an empty code-only input folder.
   Never point extraction at this private workspace, transcripts, documents or live vault.
3. Verify installed `graphify --help` and `graphify extract --help` against the pin.
   The inspected CLI implements `--code-only`; for this pin the intended smoke
   command is `graphify extract <SYNTHETIC_CODE_DIR> --code-only --no-cluster --out <DISPOSABLE_OUT>`.
   This command has not been executed here. Select the version's deterministic
   AST-only/no-semantic path. Do not assume
   `--no-cluster` alone guarantees no external calls across releases.
4. Run extraction with output in an external disposable cache. Remove model API keys
   from that process and deny network at the host boundary for the actual local-only
   proof. Confirm nodes/edges and a known function/import from synthetic source.
5. Record exact version, inputs/output hashes, command, network boundary and outcome.
   If any prerequisite is unavailable, record SKIP rather than a graph success.

Do not register a watcher, commit hook, global MCP integration, cloud service or
symlink into the live vault. Never use `--deep` or semantic document extraction on
private material without exact destination/content approval. Graphs remain disposable
code navigation aids; they are not canonical memory or publisher acceptance evidence.

Earlier migration-stage graph status: NOT INSTALLED / NOT RUN. That local index was
SQLite FTS over four explicitly selected Markdown candidates, not Graphify.
