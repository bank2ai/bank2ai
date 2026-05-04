---
title: Quickstart
sidebar_position: 3
description: Stand up a Bank2AI MCP server in under five minutes.
---

# Quickstart

Stand up a Bank2AI MCP server, point a client at it, and watch it answer "what did I spend on groceries last month?".

## 1. Install

```bash
pip install bank2ai fastmcp
```

## 2. Write a server

Create `server.py`. Start with stub handlers — Bank2AI ships shared schemas, you only supply the data:

```python
from fastmcp import FastMCP
from bank2ai import (
    Account,
    Category,
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
    return ACCOUNTS

async def get_categories():
    return CATEGORIES

# Stubs for the rest — return empty lists / friendly errors until you wire them up.
async def get_transactions(**kwargs): return []
async def get_spending_summary(**kwargs): return {"summary": [], "period": {"start_date": "2024-01-01", "end_date": "2024-01-31"}, "total": 0}
async def search_recipients(**kwargs): return []
async def create_recipient(**kwargs): return {"content": "Not implemented yet."}
async def prepare_transfer(**kwargs): return {"content": "Not implemented yet.", "actions": []}
async def execute_transfer(**kwargs): return {"content": "Not implemented yet."}

register_tools(
    app,
    get_accounts=get_accounts,
    get_transactions=get_transactions,
    get_categories=get_categories,
    get_spending_summary=get_spending_summary,
    search_recipients=search_recipients,
    create_recipient=create_recipient,
    prepare_transfer=prepare_transfer,
    execute_transfer=execute_transfer,
)

if __name__ == "__main__":
    app.run()
```

## 3. Run it

```bash
python server.py
```

You now have an MCP server speaking the full Bank2AI tool surface — eight tools, all with their schemas validated by FastMCP and Pydantic.

## 4. Try it from a client

The fastest way is to point [Claude Desktop or Claude Code at it](/docs/guides/connect-claude). Or use the `bank2ai-demo` reference client:

```bash
git clone https://github.com/bank2ai/bank2ai
cd bank2ai
uv sync
uv run --package bank2ai-demo python -m bank2ai_demo.client
```

## Next steps

- Replace the stubs with real backend calls — see [Writing handlers](/docs/library/writing-handlers).
- Read the [Specification](/docs/specification/overview) to understand the contract.
- Walk through the [real-bank guide](/docs/guides/wrap-a-real-bank) to see a real bank wired up.
- Plan how your server will [authenticate against your backend](/docs/specification/overview#4-authentication).
