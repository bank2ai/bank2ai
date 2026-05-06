---
title: Chat Agent
sidebar_position: 4
description: An AI chat agent for Digital Banking Channels, Generative UI, RAG over your knowledgebase, deep MCP integration.
---

# Chat Agent

Bancony's Chat Agent is an AI agent designed to run **inside Digital Banking Channels**, web banking, mobile apps, and branch interfaces. It uses the [bank2ai](/docs/specification/overview) tool surface for banking operations and layers a bank-aware UX on top.

## What makes it different

- **Generative UI.** Beyond text, the agent returns rich, structured cards (account snapshots, transaction lists, transfer previews, spending charts) rendered natively by the host channel. Confirmations for transfers happen in real bank-grade UI, not in plain prose.
- **RAG over your knowledgebase.** The agent grounds its answers in your bank's own documentation (fee schedules, product terms, FAQs) using retrieval over a curated index, with citations the user can drill into.
- **Deep bank2ai integration.** Every banking action goes through the standard tool surface, including the [prepare → execute split](/docs/getting-started/concepts#3-transfers-split-into-prepare--execute) for transfers. Compliance and audit live where they should: in your bank2ai server.
- **Channel-aware.** Different channels have different policies (mobile may allow biometrics; branch may require staff confirmation). The Chat Agent surfaces the right confirmation primitives in each.

## Architecture in one picture

```
[ Customer ]
     │
     ▼
[ Digital Banking Channel ]   ← Generative UI rendered natively
     │
     ▼
[ Bancony Chat Agent ]        ← prompt orchestration, RAG, policy
     │
     ▼
[ bank2ai MCP Server ]        ← bank-specific (open lib or enterprise)
     │
     ▼
[ Your bank backend ]
```

Everything below the Chat Agent is bank2ai-standard. That means a bank can run the open-source `bank2ai` reference server, a self-built server, or Bancony's enterprise server underneath, and the Chat Agent works the same way.

## When to consider it

You'd consider the Chat Agent if you want a turnkey AI assistant inside your existing banking channels and don't want to build the orchestration / generative UI / RAG layer in-house.

[Get in touch](./contact) for a demo.
