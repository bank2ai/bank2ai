---
title: register_tools
sidebar_position: 2
description: register_tools wires the eight Bank2AI tools onto a FastMCP app.
---

# `register_tools`

```python
from bank2ai import register_tools
```

`register_tools(app, *, get_accounts, get_transactions, get_categories, get_spending_summary, search_recipients, create_recipient, prepare_transfer, execute_transfer)` registers all eight Bank2AI MCP tools on a [FastMCP](https://github.com/jlowin/fastmcp) `app`, dispatching each call to the handler you provide.

## Signature

```python
def register_tools(
    app: FastMCP,
    *,
    get_accounts:         Handler,  # → list[Account]
    get_transactions:     Handler,  # → list[Transaction]
    get_categories:       Handler,  # → list[Category]
    get_spending_summary: Handler,  # → SpendingSummary
    search_recipients:    Handler,  # → list[Recipient]
    create_recipient:     Handler,  # → CreateRecipientResponse
    prepare_transfer:     Handler,  # → TransferPreparedResponse
    execute_transfer:     Handler,  # → ExecuteTransferResponse
) -> None
```

`Handler` is `Callable[..., Awaitable[Any]]`. Each handler receives keyword arguments matching the tool's input schema (using snake_case parameter names).

## Handler contract

| Tool | Handler keyword arguments |
| --- | --- |
| [`get-accounts`](/docs/specification/tools/get-accounts) | `only_withdrawal_accounts: bool`, `account_type: Literal["Current","Savings","Credit"] \| None` |
| [`transactions`](/docs/specification/tools/transactions) | `count: int \| None`, `type: Literal["Any","Income","Expenses","Savings"]`, `order: Literal["NewestFirst","OldestFirst"]`, `start_date: str \| None`, `end_date: str \| None`, `description: str \| None`, `categories: list[str] \| None` |
| [`get-categories`](/docs/specification/tools/get-categories) | _(none)_ |
| [`spending-summary`](/docs/specification/tools/spending-summary) | `group_by: Literal["category","group","month","merchant"]`, `start_date: str \| None`, `end_date: str \| None`, `categories: list[str] \| None` |
| [`recipients-by-name`](/docs/specification/tools/recipients-by-name) | `name: str` |
| [`create-recipient`](/docs/specification/tools/create-recipient) | `name: str`, `account_number: str`, `kennitala: str` |
| [`transfer-money-icelandic`](/docs/specification/tools/transfer-money-icelandic) | `amount: float`, `recipient_ssn: str`, `recipient_account_number: str`, `description: str`, `withdrawal_account_number: str`, `currency: str` |
| [`execute-transfer`](/docs/specification/tools/execute-transfer) | `withdrawal_account_id: str`, `recipient_account_number: str`, `amount: float`, `description: str` |

## Example

```python
from fastmcp import FastMCP
from bank2ai import register_tools

app = FastMCP("acme-bank")

async def get_accounts(*, only_withdrawal_accounts, account_type):
    rows = await acme_api.list_accounts()
    if only_withdrawal_accounts:
        rows = [r for r in rows if r.is_withdrawal]
    if account_type:
        rows = [r for r in rows if r.type == account_type]
    return [to_bank2ai_account(r) for r in rows]

# … define the other seven handlers …

register_tools(
    app,
    get_accounts=get_accounts,
    # …
)

if __name__ == "__main__":
    app.run()
```

## What `register_tools` does *not* do

- **It does not authenticate.** Your handlers are responsible for resolving credentials and rejecting unauthenticated calls. See [Writing handlers](./writing-handlers) for patterns.
- **It does not validate against the spec.** FastMCP validates each call against the tool's input schema; the schema itself is defined by `register_tools`. To verify a server registers the full surface, use the [drift test pattern](./testing).
- **It does not transform your data.** Handlers must return values shaped like the response model. Returning model instances or shape-compatible dicts both work.
