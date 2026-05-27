---
title: Core concepts
sidebar_position: 4
description: The five ideas you need to read the rest of the docs, the standard, the surface, the prepare→execute pattern, auth-out-of-scope, and the marketplace.
---

# Core concepts

Five ideas underpin everything else.

## 1. Bank2ai is a contract, not a framework

Bank2ai is an [open specification](/docs/specification/overview): a set of named MCP tools with fixed input/output JSON Schemas, plus four shared data models (`Account`, `Transaction`, `Category`, `Recipient`).

The Python library is a *reference implementation* of that contract. Implementations in any language are welcome, track the JSON Schemas in [`specs/bank2ai.json`](https://github.com/bank2ai/bank2ai/blob/main/specs/bank2ai.json).

## 2. The tool surface

Every compliant server registers these tools, with these names:

| Tool | What it does |
| --- | --- |
| [`get-accounts`](/docs/specification/tools/get-accounts) | List accounts and cards. |
| [`get-transactions`](/docs/specification/tools/get-transactions) | List transactions, with filters and a verbosity cap. |
| [`get-transaction`](/docs/specification/tools/get-transaction) | Look up a single transaction by id (audit / reconciliation entry point). |
| [`get-categories`](/docs/specification/tools/get-categories) | List the bank's transaction categories. |
| [`get-transactions-summary`](/docs/specification/tools/get-transactions-summary) | Aggregated income or expenses, optionally grouped by category, month, or both. |
| [`get-recipients`](/docs/specification/tools/get-recipients) | Find saved payment recipients by partial name. |
| [`create-recipient`](/docs/specification/tools/create-recipient) | Save a new recipient. |
| [`prepare-transfer`](/docs/specification/tools/prepare-transfer) | **Prepare** a transfer on any supported rail. Does not execute. |
| [`execute-transfer`](/docs/specification/tools/execute-transfer) | Execute a previously prepared transfer by `transferIntentId`. |

Servers MAY add vendor-specific tools but MUST NOT alter the names, inputs, or outputs of the tools above.

## 3. Transfers split into prepare → execute

Money movement is split into two tools on purpose:

1. The agent calls `prepare-transfer` to **validate** inputs and surface a structured preview to the user (amount, creditor, debtor account, rail, fees / FX / Confirmation of Payee when applicable). The server returns a `transferIntentId`.
2. Only after the user confirms in their UI does the client call `execute-transfer` with that `transferIntentId` (and nothing else).

This keeps the AI agent on a safe rail: it can never spend money without explicit human confirmation, and the amount / creditor / debtor / rail are immutable between prepare and execute. Servers reject expired or unknown intents with a structured `code` (`intent_expired` or `intent_not_found`).

## 4. Authentication is out of scope

Bank2ai does not define how a server authenticates. Each server obtains credentials however suits its backend (an inbound MCP `access_token`, server-configured API credentials, OAuth) and gates every bank2ai call on having valid credentials.

This isn't a gap; it's a deliberate choice. Banks already have identity systems, and forcing one on top of MCP would be wrong. See [Specification → Authentication](/docs/specification/overview#4-authentication) for the patterns reference implementations use.

## 5. The marketplace

A spec is only as useful as the surface area it covers. The [bank2ai marketplace](/docs/marketplace/overview) is a registry of:

- **MCP servers** that implement the bank2ai surface for a specific bank or fintech, and
- **agent skills** built on top (budgeting helpers, transfer assistants, statement explainers, …).

Entries are packaged as [Claude Code plugins](https://docs.claude.com/en/docs/claude-code/plugin-marketplaces), so installing a bank or skill is a single `/plugin install` away, and any client speaking the same plugin format can consume the registry.
