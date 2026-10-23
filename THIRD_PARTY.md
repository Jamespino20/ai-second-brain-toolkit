# Third-party references and copied material

This toolkit is an independent project. It is not an official Obsidian or Graphify
product and does not claim endorsement by those projects.

| Source | Reused content | Pin and retained terms |
|---|---|---|
| [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) | `.agents/skills/obsidian-markdown`, `obsidian-bases`, `json-canvas` and their references | Commit `3ccff5338ea700537839b21900aa5358a0402c98`; `THIRD-PARTY-LICENSES/obsidian-skills-MIT.txt` retains the copyright and MIT text. |
| [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) | `.codex/skills/graphify` and its references, installed by the existing project setup | Distribution `graphifyy==0.9.92`; upstream HEAD observed during original review `86c57be8204673c2a1b9849a3292a7dd3ab373d8`. Apache-2.0, MIT and NOTICE texts retained in `THIRD-PARTY-LICENSES/graphify-*`. The observed HEAD is provenance, not a claim every wheel asset was byte-identical to that commit. |
| [lucasrosati/claude-code-memory-setup](https://github.com/lucasrosati/claude-code-memory-setup) | Design/reference reading only: selective context and separate knowledge/session history | Commit inspected `62d0d0992c2aa6c553f60fc31a2b6afb24653e3c`. No source files vendored from this reference. |

Upstream copied skill and license bytes are preserved during repository preparation.
Local AGENTS.md restrictions take precedence over optional installation, watchers,
hooks, external processing or write suggestions in upstream skill documentation.

Python packages are declared dependencies, not vendored binaries. Their individual
licenses continue to apply when installed. Lockfiles retain the existing wheel pins;
this preparation does not certify vulnerability-free dependencies or portability
outside the tested environment.

No license for the toolkit's original code has been selected by this preparation.
The copied third-party license texts do not automatically license the whole toolkit.
Choose an original-code license separately before offering broader reuse rights.
