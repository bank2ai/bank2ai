---
title: register_tools
sidebar_position: 2
description: register_tools wires bank2ai tools onto a FastMCP app, pass handlers for the subset you implement.
---

# `register_tools`

```python
from bank2ai import register_tools
```

`register_tools(app, *, get_accounts=None, get_transactions=None, get_categories=None, get_spending_summary=None, search_recipients=None, create_recipient=None, prepare_transfer=None, execute_transfer=None)` registers bank2ai MCP tools on a [FastMCP](https://github.com/jlowin/fastmcp) `app`, dispatching each call to the handler you provide. Tools whose handler is omitted are not registered, so a server can expose only the subset of the spec it implements.

## Signature

```python
def register_tools(
    app: FastMCP,
    *,
    get_accounts:         Handler | None = None,  # → AccountList
    get_transactions:     Handler | None = None,  # → TransactionList
    get_categories:       Handler | None = None,  # → CategoryList
    get_spending_summary: Handler | None = None,  # → SpendingSummary
    search_recipients:    Handler | None = None,  # → RecipientList
    create_recipient:     Handler | None = None,  # → CreateRecipientResponse
    prepare_transfer:     Handler | None = None,  # → TransferPreparedResponse
    execute_transfer:     Handler | None = None,  # → ExecuteTransferResponse
) -> None
```

`Handler` is `Callable[..., Awaitable[Any]]`. Each handler receives keyword arguments matching the tool's input schema (using snake_case parameter names). Pass only the handlers you want to expose, the corresponding tools are registered, and the rest are skipped.

## Handler contract

| Tool | Handler keyword arguments |
| --- | --- |
| [`get-accounts`](/docs/specification/tools/get-accounts) | `only_withdrawal_accounts: bool`, `account_type: Literal["Current","Savings","Credit"] \| None` |
| [`get-transactions`](/docs/specification/tools/get-transactions) | `count: int \| None`, `type: Literal["Any","Income","Expenses","Savings"]`, `order: Literal["NewestFirst","OldestFirst"]`, `start_date: str \| None`, `end_date: str \| None`, `description: str \| None`, `categories: list[str] \| None`, `account_ids: list[str] \| None`, `cursor: str \| None` |
| [`get-categories`](/docs/specification/tools/get-categories) | _(none)_ |
| [`spending-summary`](/docs/specification/tools/spending-summary) | `group_by: Literal["category","group","month","merchant"]`, `start_date: str \| None`, `end_date: str \| None`, `categories: list[str] \| None` |
| [`recipients-by-name`](/docs/specification/tools/recipients-by-name) | `name: str` |
| [`create-recipient`](/docs/specification/tools/create-recipient) | `name: str`, `account_number: str`, `kennitala: str` |
| [`transfer-money-icelandic`](/docs/specification/tools/transfer-money-icelandic) | `amount: float`, `recipient_ssn: str`, `recipient_account_number: str`, `description: str`, `withdrawal_account_number: str`, `currency: str` |
| [`execute-transfer`](/docs/specification/tools/execute-transfer) | `withdrawal_account_id: str`, `recipient_account_number: str`, `amount: float`, `description: str` |

## Example

Handlers are optional, pass only the ones you implement. Here's a minimal server that exposes just `get-accounts`:

```python
from fastmcp import FastMCP
from bank2ai import AccountList, register_tools

app = FastMCP("acme-bank")

async def get_accounts(*, only_withdrawal_accounts, account_type):
    rows = await acme_api.list_accounts()
    if only_withdrawal_accounts:
        rows = [r for r in rows if r.is_withdrawal]
    if account_type:
        rows = [r for r in rows if r.type == account_type]
    return AccountList(items=[to_bank2ai_account(r) for r in rows])

register_tools(app, get_accounts=get_accounts)

if __name__ == "__main__":
    app.run()
```

To expose the full surface, define the other seven handlers and pass them as additional keyword arguments, `register_tools(app, get_accounts=..., get_transactions=..., …)`.

## Response envelopes

The MCP spec requires `structuredContent` to be a JSON object, so list-returning tools use an envelope model with an `items` field. Handlers return the envelope directly, this leaves room to add `nextCursor`, `total`, or other pagination metadata later without breaking the tool contract.

| Tool | Response model | Wire shape |
| --- | --- | --- |
| `get-accounts` | `AccountList` | `{ "items": Account[] }` |
| `get-transactions` | `TransactionList` | `{ "items": Transaction[], "nextCursor": string \| null }` |
| `get-categories` | `CategoryList` | `{ "items": Category[] }` |
| `recipients-by-name` | `RecipientList` | `{ "items": Recipient[] }` |

Single-object tools (`spending-summary`, `create-recipient`, `transfer-money-icelandic`, `execute-transfer`) return their natural response model.

## What `register_tools` does *not* do

- **It does not authenticate.** Your handlers are responsible for resolving credentials and rejecting unauthenticated calls. See [Writing handlers](./writing-handlers) for patterns.
- **It does not validate against the spec.** FastMCP validates each call against the tool's input schema; the schema itself is defined by `register_tools`. To verify a server registers the full surface, use the [drift test pattern](./testing).
- **It does not transform your data.** Handlers must return values shaped like the response model. Returning model instances or shape-compatible dicts both work.
