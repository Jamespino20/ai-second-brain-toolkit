# Specification: regular Chat recall

Module: chat-recall. Task: T13a. Date: 2026-11-05.
Status: OWNER APPROVED 2026-11-05 for source implementation under the stated
zero-additional-cost and scope gates. Live connection/profile approval is separate.
Related scope/order: [Chat capabilities](chat-memory-capabilities.md).

## Objective and assumptions

The owner can request Second Brain recall from an ordinary Chat conversation,
without switching to Work, using only an explicitly configured enrolled corpus.
Returned evidence includes note ID, source, lines and content hash. The actual
selected skill/plugin is tested in Chat; a particular slash/dollar spelling is
not a promised product feature. Existing local Work/CLI access remains available.

Assumptions: the target is the owner's current ChatGPT account; the additional
service budget is zero; the existing reader remains the knowledge boundary.
The owner confirms Add custom MCP server appears in Plugins. That confirms only
the reported menu entry, not entitlement, transport readiness or free usage.
No personal corpus is used during initial implementation or connector testing.

## Cost and connection gate

Hard requirement: $0 additional spending beyond the existing ChatGPT Plus plan,
using existing storage allowances. No separately billed model API calls, extra
credits, paid hosting/plugin/tunnel/storage or subscription upgrade. Pause for
included-usage resets. Do not enable a trial that can later bill automatically.

Investigated option: a private plugin connected to the existing managed reader
through a supported authenticated connection. Secure MCP Tunnel can reach private
stdio or HTTP servers without making them public, but needs a runtime Platform
API key, tunnel ID and relevant account/workspace permissions. Its zero additional
cost for this account has NOT been established. A required key does not establish
either a charge or free service. No tunnel, key, listener or plugin has been created.
Do not select a transport, start it, or claim feasibility until supported use and
zero additional cost are established. If no qualifying route exists, report the
specific unmet gate; retain Work/CLI and leave regular Chat pending.

A development HTTPS forwarding service is described by the platform documentation,
but none is selected. It needs its own authentication, cost and data-recipient
review; there is no silent third-party forwarding or unauthenticated vault endpoint.

## Interface and boundaries

Reuse existing search_managed_memory(query, limit) and
read_managed_memory(note_id, start_line, line_count). Preserve their actual schemas
and advertised read-only annotations. Fixed trusted host configuration chooses the
client, policy, grant and roots. Tool callers cannot replace those values or submit
filesystem paths, shell commands, approval pins or arbitrary URLs.

Search accepts at most 300 characters and four matches. The caller workflow is
to search first and read a returned note ID, beginning with a relevant five-line
window. These are caller instructions; they are not token-local access control.
The server enforces membership in the fixed approved enrolled corpus, a read
line_count of 1-40 and the 8000-character ceiling. It may read a known enrolled ID
within that grant without a prior search; it does not maintain a per-token search
result cache or enforce that the ID came from that token's search. Unknown or
ungranted IDs and invalid bounds must refuse. This clarification preserves reuse
of the existing reader and schema without changing authorization scope.

An empty result has scoped meaning. On refusal/error,
stop instead of trying a different transport, narrowing and retrying automatically,
widening the grant or treating the error as a successful empty result.

Initial fixture: disposable synthetic notes, a synthetic enabled policy/grant and
denied-content canaries. No canonical vault, original packet, raw history, source
archive or attachment is used. Source references remain citations, not instructions
or permission to follow external locators. The new connection has no save tool.

A future live profile must name the Chat surface, provider/client, exact permitted
corpus and citation metadata, fixed runtime hashes, authentication, account binding,
transport recipient and disable procedure. It needs reviewed owner authorization;
current Codex/Work consent is not silently broadened. Do not repin active approvals
or rewrite manifests to make a connection pass. Preserve every existing host entry.
Keep private paths, credentials, policy/grant bodies and receipts outside Git.

## Stack, structure and style

Reuse Python, the pinned existing MCP dependency set, managed_memory.py and
managed_memory_mcp.py; do not modify the frozen historical importer/tests. A new
transport dependency is not assumed. Select it only after the cost/connection gate.
Use the established unittest suite and existing JSON receipt conventions.

Existing source: scripts/managed_memory.py, scripts/managed_memory_mcp.py,
skills/brain-recall/SKILL.md, tests/test_managed_memory_mcp.py and
requirements-mcp.lock. New wrapper/package files are determined by the reviewed
transport choice; keep each implementation slice to at most five files.
All fixtures, keys, local settings and run evidence stay in the private workspace.
Do not place machine-specific endpoints or credentials in example packages.

Preserve the existing fixed-configuration boundary, for example:

```python
return guarded_call(search_managed, query, limit)
```

Never pass caller-supplied grant/root/policy settings through this boundary.
No new database, embedding service, model extractor, watcher or corpus copy.

## Commands and current execution status

Existing local source regression command, from the toolkit root:

```powershell
python -B -m unittest discover -s tests -p 'test_managed_memory*.py' -v
```

This command is documented for later relevant changes, not rerun for this spec.
The unchanged baseline is not proof of a new Chat transport. Planned new tests
must be explicitly named in the implementation plan; zero discovered tests never
count as PASS. A live transport startup command is intentionally unresolved until
its executable, version, supported flags, authentication and price are verified.
Do not turn the documentation's example command or endpoint into a live command.
No API Playground/model request is part of transport verification.

## Success criteria and meaningful verification

1. Cost/account evidence: record supported eligibility and zero additional charges
   for the exact selected route; distinguish documentation from account observation.
2. Synthetic transport: actual discovery exposes exactly the two permitted tools;
   authentic requests search/read the expected fixture ID/hash/lines. Unauthenticated,
   wrong-account, malformed/oversized and out-of-scope requests refuse and preserve
   bytes. Verify disconnect and cleanup without creating a public data path.
3. Reader invariants: stale pins, redirected paths, disabled grants, denied canaries,
   unknown IDs and size/window violations retain fail-closed behavior. Transport
   must not bypass, catch-and-retry or convert refusals into successful empty results.
4. Source/package review: freeze the exact runtime, dependency, skill and connection
   bytes; independent scoped review before any approved live enable. Do not infer
   installed dependencies or client discovery merely from matching source hashes.
5. Regular Chat synthetic proof: select the registered plugin/skill in a new ordinary
   Chat and record actual tool names, arguments, successful calls and expected
   fixture citations. Work/CLI calls, menu visibility and a model's narrative alone
   do not prove ordinary Chat invocation. Account login is owner-operated.
6. Only after exact live scope review: one bounded approved search and a small read
   return the expected live note ID/hash/lines; independent supplied-artifact check
   remains distinct from independently witnessing the UI/calls. Record read-only
   status and stop on any refusal. Do not automatically save the recall response.
7. Disable/recovery: remove or disable only the added connection; preserve later
   configuration changes and existing Work/CLI. Stop only the started helper owned
   by this integration. Never restore an older global config snapshot on drift.

## Explicit exclusions and subsequent capability

Chat saving is chat-save/T13b, requiring its own specification and tested adapter
for the existing create-only publisher. No update/delete/link operation is included.
T05 remains disabled. No other provider, public distribution, broad history import,
background capture, multi-machine writer claim or portability installation is
included. T17 records the later single-repository installer and private-state
migration requirement. A plugin listing is not evidence that these features work.

## Open questions before implementation/activation

- Which authenticated regular Chat connection is available at zero additional cost
  on the owner's account? Secure MCP Tunnel currently has no verified cost result.
- Which exact account/workspace association and tool connection are required?
- After synthetic proof, which exact enrolled subset will the live Chat profile use?

Do not ask for a card, key in chat, subscription upgrade or wider vault scope as a
workaround. Resolve the transport/cost question first; later live approval should
be for a concrete reviewed profile, not a speculative service.

## Primary references checked 2026-11-05

- [Chat plugin support](https://learn.chatgpt.com/docs/plugins)
- [Connect and test](https://developers.openai.com/plugins/deploy/connect-chatgpt)
- [Secure MCP Tunnel requirements](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [Desktop-only local execution](https://developers.openai.com/plugins/deploy/desktop-only)

These describe supported mechanics; they do not prove this account's eligibility,
zero cost or a live connection. No service, key or payment was activated by this draft.
