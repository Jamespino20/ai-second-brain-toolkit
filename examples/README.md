# Inert configuration examples

These files contain placeholders and do not configure an integration automatically.
Do not copy real note text, user paths, secrets or approval grants back into Git.

- `selected-memory-grant.example.json`: pending synthetic grant with no selected
  notes. Copy outside Git, select only synthetic test Markdown, calculate exact
  sizes/hashes, and record actual owner approval. Live personal notes require a
  separate per-client external-processing approval and canonical grant.
- `codex-mcp.example.toml`: disabled server entry. Replace executable/script paths
  and grant/pin outside this repository; place it in an explicitly chosen private
  Codex profile. The tested host needs its existing code-mode host for tool discovery.
- `claude-mcp.example.json`: uninstalled stdio server object. Import only after
  separate Claude authorization, using a grant whose client is `claude-anthropic`.
- `codex-capture-config.example.json`: disabled opt-in launcher configuration;
  copy to the existing private staging root and review exact cwd/profile first.
- `capture-output.schema.json`: strict structured final report shape supplied to
  `codex exec`; bounds, provenance and privacy are validated locally as well.
  Neither file installs a hook or grants personal-content access. See
  [capture MVP](../docs/automatic-capture-mvp.md).

Templates are syntax-checked, not substitutes for the private working profile or
fresh-session test evidence. Read [the reader contract](../docs/selected-memory-retrieval.md)
for the settings, bounds, revocation and limits of the application allowlist.
