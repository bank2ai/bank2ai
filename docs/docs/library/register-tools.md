---
title: register_tools
sidebar_position: 2
description: register_tools wires bank2ai tools onto a FastMCP app, pass handlers for the subset you implement.
---

# `register_tools`

```python
from bank2ai import register_tools
```

`register_tools(app, *, get_accounts=None, get_transactions=None, get_transaction=None, get_categories=None, get_transactions_summary=None, get_recipients=None, create_recipient=None, prepare_transfer=None, execute_transfer=None)` registers bank2ai MCP tools on a [FastMCP](https://github.com/jlowin/fastmcp) `app`, dispatching each call to the handler you provide. Tools whose handler is omitted are not registered, so a server can expose only the subset of the spec it implements.

## Signature

```python
def register_tools(
    app: FastMCP,
    *,
    get_accounts:             Handler | None = None,  # → AccountList
    get_transactions:         Handler | None = None,  # → TransactionList
    get_transaction:          Handler | None = None,  # → GetTransactionResponse
    get_categories:           Handler | None = None,  # → CategoryList
    get_transactions_summary: Handler | None = None,  # → TransactionsSummary
    get_recipients:           Handler | None = None,  # → RecipientList
    create_recipient:         Handler | None = None,  # → CreateRecipientResponse
    prepare_transfer:         Handler | None = None,  # → PrepareTransferResponse
    execute_transfer:         Handler | None = None,  # → ExecuteTransferResponse
) -> None
```

`Handler` is `Callable[..., Awaitable[Any]]`. Each handler receives keyword arguments matching the tool's input schema (using snake_case parameter names). Pass only the handlers you want to expose, the corresponding tools are registered, and the rest are skipped.

## Handler contract

| Tool | Handler keyword arguments |
| --- | --- |
| [`get-accounts`](/docs/specification/tools/get-accounts) | `only_withdrawal_accounts: bool`, `account_type: Literal["Current","Savings","Credit","Loan","Other"] \| None`, `status: Literal["Enabled","Blocked","Deleted"] \| None`, `usage: Literal["Private","Business"] \| None` |
| [`get-transactions`](/docs/specification/tools/get-transactions) | `count: int \| None`, `order: Literal["NewestFirst","OldestFirst"]`, `verbosity: Literal["minimal","standard","full"]`, `start_date: str \| None`, `end_date: str \| None`, `description: str \| None`, `category_ids: list[str] \| None`, `account_ids: list[str] \| None`, `min_amount: float \| None`, `max_amount: float \| None`, `cursor: str \| None` |
| [`get-transaction`](/docs/specification/tools/get-transaction) | `transaction_id: str`, `account_id: str \| None` |
| [`get-categories`](/docs/specification/tools/get-categories) | _(none)_ |
| [`get-transactions-summary`](/docs/specification/tools/get-transactions-summary) | `direction: Literal["Income","Expenses"]`, `group_by: Literal["none","category","month","both"]`, `start_date: str \| None`, `end_date: str \| None`, `category_ids: list[str] \| None`, `account_ids: list[str] \| None`, `min_amount: float \| None`, `max_amount: float \| None` |
| [`get-recipients`](/docs/specification/tools/get-recipients) | `name: str` |
| [`create-recipient`](/docs/specification/tools/create-recipient) | `name: str`, `account_identifier: AccountIdentifier`, `national_id: NationalId \| None`, `nickname: str \| None`, `bic: str \| None`, `default_description: str \| None`, `idempotency_key: str \| None` |
| [`prepare-transfer`](/docs/specification/tools/prepare-transfer) | `debtor_account_id: str`, `creditor: Party`, `amount: float`, `currency: str`, `rail: Rail`, `local_instrument: str \| None`, `requested_execution_date: str \| None`, `remittance_information: RemittanceInformation \| None`, `end_to_end_id: str \| None`, `description: str \| None`, `idempotency_key: str \| None` |
| [`execute-transfer`](/docs/specification/tools/execute-transfer) | `transfer_intent_id: str`, `idempotency_key: str \| None` |

## Example

Handlers are optional, pass only the ones you implement. Here's a minimal server that exposes just `get-accounts`:

```python
from fastmcp import FastMCP
from bank2ai import AccountList, register_tools

app = FastMCP("acme-bank")

async def get_accounts(*, only_withdrawal_accounts, account_type, status, usage):
    rows = await acme_api.list_accounts()
    if only_withdrawal_accounts:
        rows = [r for r in rows if r.is_withdrawal]
    if account_type:
        rows = [r for r in rows if r.type == account_type]
    if status:
        rows = [r for r in rows if r.status == status]
    if usage:
        rows = [r for r in rows if r.usage == usage]
    return AccountList(items=[to_bank2ai_account(r) for r in rows])

register_tools(app, get_accounts=get_accounts)

if __name__ == "__main__":
    app.run()
```

To expose the full surface, define the other eight handlers and pass them as additional keyword arguments, `register_tools(app, get_accounts=..., get_transactions=..., …)`.

## Response envelopes

The MCP spec requires `structuredContent` to be a JSON object, so every bank2ai tool wraps its result in an envelope. Handlers return the envelope directly, so additional metadata (`nextCursor`, `actions`, `code`, …) can grow over time without breaking the tool contract.

### List envelopes

List-returning tools wrap their results under an `items` field. The envelope leaves room for pagination and aggregation metadata alongside the array.

| Tool | Response model | Wire shape |
| --- | --- | --- |
| `get-accounts` | `AccountList` | `{ "items": Account[] }` |
| `get-transactions` | `TransactionList` | `{ "items": Transaction[], "nextCursor": string \| null }` |
| `get-categories` | `CategoryList` | `{ "items": Category[] }` |
| `get-recipients` | `RecipientList` | `{ "items": Recipient[] }` |

### Single-item envelopes

Mutating tools and single-object reads wrap their result under an `item` field alongside a human-readable `content` status string. Recoverable errors populate `content` (and the structured `code`) and leave `item` absent; the tool call itself still succeeds.

| Tool | Response model | Wire shape |
| --- | --- | --- |
| `get-transaction` | `GetTransactionResponse` | `{ "content": string, "item": Transaction \| null }` |
| `create-recipient` | `CreateRecipientResponse` | `{ "content": string, "item": Recipient \| null, "code": string \| null }` |
| `prepare-transfer` | `PrepareTransferResponse` | `{ "content": string, "item": PreparedTransfer \| null, "actions": TransferAction[], "code": string \| null }` |
| `execute-transfer` | `ExecuteTransferResponse` | `{ "content": string, "item": ExecutedTransfer \| null, "code": string \| null }` |

### Aggregate envelope

`get-transactions-summary` is structurally different: it returns a `summary` array of grouped rows plus the `period` covered and an overall `total`, rather than the `items` / `item` pattern.

| Tool | Response model | Wire shape |
| --- | --- | --- |
| `get-transactions-summary` | `TransactionsSummary` | `{ "summary": TransactionsSummaryGroup[], "period": { "startDate": string, "endDate": string }, "total": number }` |

## What `register_tools` does *not* do

- **It does not authenticate.** Your handlers are responsible for resolving credentials and rejecting unauthenticated calls. See [Writing handlers](./writing-handlers) for patterns.
- **It does not validate against the spec.** FastMCP validates each call against the tool's input schema; the schema itself is defined by `register_tools`. To verify a server registers the full surface, use the [drift test pattern](./testing).
- **It does not transform your data.** Handlers must return values shaped like the response model. Returning model instances or shape-compatible dicts both work.
