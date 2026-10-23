# Scoped agent handoff

For the current synthetic-only Codex MCP route, use
[selected-note retrieval](selected-memory-retrieval.md). The candidate recipe below
describes the earlier staging workflow; it does not grant access to published notes.

Start a compatible local agent in this tooling repository. Give it only explicitly
selected candidate notes or a reviewed context packet for its current task. Keep
the live vault, private raw archive, backup and source manifest outside routine access.
Do not attach the private workspace as an unrestricted agent working directory.

Portable Markdown can be read by Codex and other assistants when deliberately
provided. It does not create automatic history synchronization or filesystem access
for ChatGPT Chat/Work or Claude Chat/Work/Code. Connector availability, host filesystem
access, destination permission and actual integration testing remain separate.

The project AGENTS.md and official skills describe behavior; they do not enforce
Windows access restrictions. Same-account unrestricted filesystem agents remain
unisolated. Use selected packets until a real boundary passes its tests. Ordinary
agents propose changes and cannot approve themselves or alter owner governance.

Fresh read-back recipe: with no prior chat context, retrieve the selected candidate
decision and status notes; ask what is canonical, whether a graph connection is
operational, the latest dated project status, and whether publication is permitted.
Verify substantive answers, note IDs, dates and candidate status. Retrieval success
does not imply publisher acceptance or OS isolation. Preserve the output privately.

Official skill source: https://github.com/kepano/obsidian-skills at commit
`3ccff5338ea700537839b21900aa5358a0402c98`. Project-local copies are in
`.agents/skills/obsidian-markdown`, `obsidian-bases`, and `json-canvas`. No Obsidian
CLI or live-vault plugin was enabled. The local format skills contain no vault path.

OpenAI skill documentation checked: https://learn.chatgpt.com/docs/build-skills.
Host support must be observed in a fresh compatible session; copying a skill is
not proof that every ChatGPT/Claude surface discovers it automatically.
