# Chat memory capabilities

Status: owner-requested integration, 2026-11-05; runtime not implemented or enabled.
This records the recall-first/save-second sequence the owner asked to proceed with.
Technical implementation and activation requirements remain reviewable separately.

| Module ID | User-visible capability | Depends on |
|---|---|---|
| chat-recall | Regular Chat retrieves only explicitly enrolled, permitted memory with citations | Existing managed reader; verified authenticated zero-additional-cost connection |
| chat-save | Regular Chat explicitly stages and publishes eligible new engineering memory | chat-recall connection proof; existing create-only publisher; separate save contract |

Build order: chat-recall -> chat-save. Existing local Work/CLI access is retained.
Transport is a boundary of chat-recall, not a second knowledge store or new model.

Hard budget: $0 additional charges beyond the owner's existing ChatGPT Plus plan.
No API model usage, extra credits, paid hosting/tunnel/plugin/storage, or plan upgrade.
A route with unknown pricing does not pass. API-key authentication alone does not
prove that a service costs money or that it is free. Wait when included usage ends.

The owner confirms Add custom MCP server is available in Plugins. Exact account
permissions, connection method and cost still need evidence before activation.
No current live grant is widened merely by recording these tasks.

The [chat-recall specification](chat-recall-spec.md) is the first draft for review.
chat-save will receive its own specification after the recall path is proven.
T17's one-repository installer/private-state migration remains a deferred milestone,
not a prerequisite for source-only Chat research. See [task ledger](../tasks/todo.md).
