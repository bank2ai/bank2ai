---
title: Quickstart
sidebar_position: 3
description: Stand up a Bank2AI MCP server in under five minutes.
---

# Quickstart

Stand up a Bank2AI MCP server, point a client at it, and watch it answer "what did I spend on groceries last month?".

## 1. Install

```bash
uv add bank2ai fastmcp
```

## 2. Write a server

Create `server.py`. Bank2AI ships shared schemas — you only supply handlers for the tools you implement. Every handler is optional, so you can start with a couple and grow into the full surface:

```python
from fastmcp import FastMCP
from bank2ai import (
    Account,
    AccountList,
    Category,
    CategoryList,
    register_tools,
)

app = FastMCP("my-bank")

ACCOUNTS = [
    Account(
        id="acc-1",
        accountNumber="1234-56-789012",
        currency="USD",
        balance=4250.00,
        accountType="Current",
        isWithdrawalAccount=True,
        isDefaultAccount=True,
    ),
]

CATEGORIES = [
    Category(id="cat-groceries", name="Groceries"),
    Category(id="cat-transport", name="Transportation"),
]

async def get_accounts(*, only_withdrawal_accounts: bool, account_type):
    return AccountList(items=ACCOUNTS)

async def get_categories():
    return CategoryList(items=CATEGORIES)

register_tools(
    app,
    get_accounts=get_accounts,
    get_categories=get_categories,
)

if __name__ == "__main__":
    app.run()
```

Tools whose handler is omitted are simply not registered. Add `get_transactions`, `get_spending_summary`, `search_recipients`, `create_recipient`, `prepare_transfer`, and `execute_transfer` as you implement them.

## 3. Run it

```bash
python server.py
```

You now have an MCP server exposing the two Bank2AI tools you implemented, with their schemas validated by FastMCP and Pydantic.

## 4. Try it from a client

The fastest way is to point [Claude Desktop or Claude Code at it](/docs/guides/connect-claude). Or use the `bank2ai-demo` reference client:

```bash
git clone https://github.com/bank2ai/bank2ai
cd bank2ai
uv sync
uv run --package bank2ai-demo python -m bank2ai_demo.client
```

## Next steps

- Add handlers for the remaining tools — see [Writing handlers](/docs/library/writing-handlers).
- Read the [Specification](/docs/specification/overview) to understand the contract.
- Walk through the [real-bank guide](/docs/guides/wrap-a-real-bank) to see a real bank wired up.
- Plan how your server will [authenticate against your backend](/docs/specification/overview#4-authentication).
