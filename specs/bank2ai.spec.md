# Bank2ai MCP Specification

> **Version:** 0.1.0, draft, derived from the Python reference implementation.
> **Companion artifact:** [`bank2ai.json`](./bank2ai.json), canonical input/output JSON Schemas.

Bank2ai connects digital banking data and operations with AI agents. The language of banking (accounts, transactions, transfers, bill payments, recipients, loans, savings) is universally identical, and bank2ai is the open standard that lets banks, fintechs, and AI builders collaborate on a single shared vocabulary instead of each reinventing one.

This document defines that vocabulary as a [Model Context Protocol](https://modelcontextprotocol.io) tool surface that any bank can expose so AI agents (and through them, end customers) can read accounts and transactions, look up recipients, run spending summaries, and prepare/execute transfers, using the same tool surface across every bank.

Compliant servers and the agent skills built on top of them are distributed through the [bank2ai marketplace](../README.md#marketplace), which is packaged as a [Claude Code plugin marketplace](https://docs.claude.com/en/docs/claude-code/plugin-marketplaces) and consumable from any client that speaks the same plugin format.

The contract has two parts:

1. The **tool surface**, a set of named MCP tools whose input and output JSON Schemas are fixed by the spec.
2. The **shared data models** (`Account`, `Transaction`, `Category`, `Recipient`) used inside tool inputs and outputs.

Authentication is intentionally outside the spec: servers obtain credentials however suits their backend (a bearer token from the inbound MCP `access_token`, server-configured API credentials, OAuth, etc.) and gate calls accordingly. See [§4](#4-authentication) for the rationale.

> **About RFC 2119 keywords.** *MUST*, *SHOULD*, *MAY* are used per [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119).

## 1. Tool surface

A bank2ai server MAY register any subset of the following tools. Tools that are registered MUST use these exact names and the input/output shapes defined in [`bank2ai.json`](./bank2ai.json) under `tools[].inputSchema` and `tools[].outputSchema`.

| Name                       | Purpose                                                            |
| -------------------------- | ------------------------------------------------------------------ |
| `get-accounts`             | List bank accounts and cards, optionally filtered by type or by withdrawal-eligibility. |
| `get-transactions`         | List transactions, with filters for account, date range, signed amount range, categories, free-text search, and result count. Supports cursor-based paging via `cursor` / `nextCursor`. |
| `get-categories`           | List the bank's transaction categories.                            |
| `get-transactions-summary` | Aggregated transactions, scoped to either income or expenses (required `direction`). Group by `none`, `category`, `month`, or `both`; each row reports the corresponding `category_id` and/or `month`. Filters mirror `get-transactions`: account, date, amount, category ids. |
| `get-recipients`           | Look up saved payment recipients by partial name match.            |
| `create-recipient`         | Save a new recipient for future transfers.                         |
| `prepare-transfer-icelandic` | **Prepare** a domestic Icelandic transfer; validates inputs and returns details for confirmation. Does **not** execute. |
| `execute-transfer`         | Execute a transfer that the user has already confirmed.            |

Servers MAY also register additional, vendor-specific tools, but they MUST NOT alter the names, inputs, or outputs of the tools above.

> **Why "prepare → execute"?** Splitting transfers into two tools keeps the AI agent on a safe rail: the agent gathers details, the user confirms in their UI, and only then is `execute-transfer` called. Servers SHOULD reject `execute-transfer` calls that don't correspond to a recently prepared transfer.

## 2. Lifecycle

A typical bank2ai session looks like this:

1. The MCP client connects and calls `tools/list`. The server returns the bank2ai tools it has registered (any subset of those listed in §1).
2. The client calls bank2ai tools as the user requests them. The server resolves credentials internally (see §4) and rejects calls it cannot authenticate.
3. On a transfer, the client calls `prepare-transfer-icelandic` first to validate, surfaces the prepared details to the user, and only invokes `execute-transfer` after explicit confirmation.

## 3. Shared data models

The schemas in `bank2ai.json` under `models{}` define the canonical shapes for:

* **`Account`**, id, accountNumber, currency, balance, optional availableBalance, overdraftLimit, isWithdrawalAccount, isDefaultAccount, accountType (`Current` | `Savings` | `Credit`).
* **`Transaction`**, id, description, amount (in the user's default currency, negative = expense), transaction_date (ISO 8601), category_id (resolves via `get-categories`), optional currency and amount_in_currency for transactions originally made in a different currency.
* **`Category`**, id, name (localized).
* **`Recipient`**, id, name, accountNumber, accountNumberType (`Domestic` | `IBAN` | `SWIFT`), socialSecurityNumber, optional bankInfo, paymentType, address, isFavorite, description.

Servers MAY return additional fields on these objects; clients MUST tolerate unknown fields. Servers MUST NOT omit fields marked `required` in the schemas.

## 4. Authentication

Bank2ai does not define an authentication protocol. How a server obtains the credentials it needs to talk to its backend is an implementation detail; servers MUST gate every bank2ai tool call on having valid credentials and MUST surface authentication failures as MCP errors.

Common approaches used by reference implementations:

* **Inbound bearer token.** A token attached to the MCP request (`access_token`) is forwarded to the bank backend. Best when the MCP client is already authenticated against the bank's identity provider.
* **Server-configured credentials.** The server reads credentials from its environment (e.g. `BANK2AI_*_EMAIL` / `BANK2AI_*_PASSWORD`) and exchanges them for a backend session token, refreshing as needed.
* **Demo / no-auth.** Servers backed by hardcoded data MAY skip authentication entirely.

Servers MUST NOT register a bank2ai-defined `authenticate` tool, earlier drafts of this spec described one and it has been removed.

## 5. Error model

* Servers SHOULD return MCP `ToolError` (or equivalent protocol-level error) for unrecoverable failures, including authentication failures.
* For recoverable user-facing conditions (e.g. "Insufficient funds", "Invalid recipient"), servers SHOULD return a successful tool call whose response model includes a human-readable `content` field describing the problem. `prepare-transfer-icelandic` and `create-recipient` model this explicitly.

## 6. Localization

* Currencies are ISO 4217 (`USD`, `ISK`, `EUR`, …). `Account.balance` and `Account.availableBalance` are in the account's `currency`. `Transaction.amount` is normalized to the user's default currency so clients can render transaction lists without per-row currency conversion; when the transaction was originally made in a different currency, `Transaction.currency` and `Transaction.amount_in_currency` preserve the original. Clients SHOULD omit the currency symbol on transaction amounts unless the user explicitly asks which currency a transaction is in.
* Dates are ISO 8601 (`YYYY-MM-DD`).
* Category names are localized server-side. Clients MUST treat category names as opaque user-facing strings and use `Category.id` for programmatic identity; filtering MUST go through the `category_ids` parameter on `get-transactions` / `get-transactions-summary`, and `Transaction.category_id` resolves to the matching `Category` from `get-categories`.

## 7. Backwards compatibility

The spec versioning policy lives in [`README.md`](./README.md). Notable additive-change rules:

* Adding a new optional tool input is a **minor** bump.
* Adding a new optional output field is a **minor** bump; clients MUST tolerate unknown fields.
* Adding a new tool is a **minor** bump.
* Removing or renaming anything, or making a previously optional field required, is a **major** bump.

## 8. Reference implementations

* [`examples/demo`](../examples/demo), full surface backed by hardcoded data; useful for client conformance testing without a real bank.

