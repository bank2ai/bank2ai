---
title: Changelog
sidebar_position: 2
description: Notable changes to the bank2ai specification and library.
---

# Changelog

The spec and the Python library version independently. This page tracks notable changes for each.

For the authoritative version field, see [`specs/bank2ai.json`](https://github.com/bank2ai/bank2ai/blob/main/specs/bank2ai.json).

## Specification

### 0.6.0, Draft

- **Breaking:** `transactions-summary` reworked its grouping. `group_by` accepts `none`, `category`, `month`, or `both` (replacing `category` / `group` / `month` / `merchant`). `TransactionsSummaryGroup` drops the opaque `group` field in favour of explicit nullable `category` and `month` fields, populated according to the requested `group_by`.

### 0.5.0, Draft

- **Breaking:** `transactions-summary` is always scoped to a single direction. The `direction` input is now required and accepts `Income` or `Expenses`; the `Both` option has been removed. Callers that need both sides should call the tool twice.

### 0.4.0, Draft

- **Breaking:** `spending-summary` renamed to `transactions-summary`. Inputs now include `direction` (`Income` / `Expenses` / `Both`), `account_ids`, `min_amount`, and `max_amount`, mirroring the `get-transactions` filter set. The `SpendingSummary*` models are renamed to `TransactionsSummary*`.

### 0.3.0, Draft

- **Breaking:** dropped the `type` (`Income` / `Expenses` / `Savings`) input from `get-transactions`; income/expenses scoping now goes through the signed `min_amount` / `max_amount` bounds.

### 0.2.0, Draft

- Added optional `min_amount` and `max_amount` inputs to `get-transactions`. Bounds are applied against the signed transaction amount (negative = expense, positive = income).

### 0.1.0, Draft

- Initial draft, derived from the Python reference implementation.
- Tools: `get-accounts`, `get-transactions`, `get-categories`, `spending-summary`, `recipients-by-name`, `create-recipient`, `transfer-money-icelandic`, `execute-transfer`.
- Four shared models: `Account`, `Transaction`, `Category`, `Recipient`.
- Authentication declared out of scope.
- A previously specified bank2ai-defined `authenticate` tool was removed.

## Python library (`bank2ai`)

### 0.3.0

- **Breaking:** the wire-level tool name `transactions` was renamed to `get-transactions` to align with `get-accounts` and `get-categories`. The `register_tools` handler keyword (`get_transactions=`) is unchanged; only MCP clients calling the tool by name need to update.

### 0.2.0

- **Breaking:** the MCP tool surface moved from `bank2ai.mcp` to `bank2ai.tools`. Update imports accordingly.
- Every `register_tools` handler keyword argument is now optional, tools whose handler is omitted are not registered, so a server can expose only the subset of the spec it implements.
- Tool outputs follow the MCP convention of wrapping list results under an `items` key (`AccountList`, `CategoryList`, `RecipientList`, `TransactionList`).
- `get-transactions` gains pagination via `cursor` plus a `next_cursor` on `TransactionList`.
- `get-transactions` accepts an `account_ids` list (replacing the earlier single `account_id`) so callers can filter across multiple accounts in one call.

### 0.1.0

- Initial release.
- Pydantic models for every bank2ai shape.
- `register_tools(app, ...)` wiring the spec's tools onto a FastMCP app.

## Versioning policy

`bank2ai.json` follows [SemVer](https://semver.org/):

- **Major**, breaking changes (removing tools, renaming inputs/outputs, tightening required fields, changing semantic meaning).
- **Minor**, additive changes (new tools, new optional inputs, new optional output fields).
- **Patch**, description / metadata edits with no behavioural impact.

The Python package version moves independently of the spec version.
