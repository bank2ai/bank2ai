---
title: Writing handlers
sidebar_position: 4
description: Patterns for plugging Bank2AI handlers into a real bank backend.
---

# Writing handlers

A handler is an async function that turns Bank2AI tool inputs into Bank2AI outputs. The library doesn't care how you do it — call REST APIs, query a database, hit a GraphQL endpoint, mock everything for tests. This page collects the patterns we've seen work.

## Pattern: stateless handlers calling a backend client

The simplest shape — and what the reference [real-bank guide](/docs/guides/wrap-a-real-bank) uses. Handlers are top-level async functions; backend state lives in a client passed via closure.

```python
from bank2ai import Account, register_tools
from fastmcp import FastMCP

def make_app(api: AcmeBankClient) -> FastMCP:
    app = FastMCP("acme-bank")

    async def get_accounts(*, only_withdrawal_accounts, account_type):
        rows = await api.list_accounts()
        if only_withdrawal_accounts:
            rows = [r for r in rows if r.can_withdraw]
        if account_type:
            rows = [r for r in rows if r.type == account_type]
        return [_to_bank2ai_account(r) for r in rows]

    # … other handlers (all optional) …

    register_tools(app, get_accounts=get_accounts, ...)
    return app
```

Every keyword argument to `register_tools` is optional, so during development you can register only the handlers you've written — unimplemented tools are simply not exposed.

## Pattern: per-request authentication

Handlers can read MCP context to forward an inbound bearer token, or call into a server-side auth flow. Use FastMCP's `Context` parameter:

```python
from fastmcp import Context

async def get_accounts(ctx: Context, *, only_withdrawal_accounts, account_type):
    token = ctx.request_context.access_token  # forwarded MCP access token
    api = AcmeBankClient(token=token)
    return await _list_accounts(api, only_withdrawal_accounts, account_type)
```

If your backend requires an exchange (e.g. email/password → session token), do the exchange once at server startup and refresh as needed. See the [real-bank guide](/docs/guides/wrap-a-real-bank) for a worked example.

## Pattern: mapping backend shapes to Bank2AI

Banks rarely expose the exact Bank2AI shape on the wire. Write small mappers and unit-test them — your spec compliance lives or dies in those mappers.

```python
def _to_bank2ai_account(row: AcmeAccountRow) -> Account:
    return Account(
        id=row.id,
        name=row.display_name,
        accountNumber=row.formatted_number,
        currency=row.currency,
        balance=row.balance,
        availableBalance=row.available_balance,
        overdraftLimit=row.overdraft or 0,
        isWithdrawalAccount=row.kind in {"checking", "savings"},
        isDefaultAccount=row.is_primary,
        accountType={"checking": "Current", "savings": "Savings", "credit": "Credit"}[row.kind],
    )
```

## Pattern: prepare → execute for transfers

The two-step transfer flow exists so the user can confirm a structured preview before money moves. A reasonable implementation:

1. `prepare_transfer` — validate everything (amount, recipient, source account), then return a `TransferPreparedResponse` with a populated `item` and a short, idempotent token (e.g. a UUID) embedded somewhere your `execute_transfer` can recognize. Cache the prepared transfer server-side keyed by that token.
2. `execute_transfer` — look up the prepared transfer by `(withdrawal_account_id, recipient_account_number, amount)` (or by the token if your client surfaces it) and call your backend's transfer API. Return an `ExecuteTransferResponse` with the bank-issued receipt.

Reject `execute_transfer` calls with no matching preparation. This is the single most important safety property of the surface — don't shortcut it.

## Pattern: returning user-facing errors

For *unrecoverable* failures, raise `ToolError` (or let your client raise an MCP error). For *user-facing* conditions ("Insufficient funds", "Invalid recipient"), return a successful response with a `content` field that explains the situation:

```python
return TransferPreparedResponse(
    content="Insufficient funds in your default account.",
    actions=[],  # no preview surfaced
)
```

This keeps the AI client conversational instead of forcing it to interpret protocol errors.

## What not to do

- **Don't reshape responses.** If the spec says `accountNumber`, your output must say `accountNumber` — not `account_number`, not `iban`. The library and FastMCP enforce this; don't fight it.
- **Don't add a Bank2AI-defined `authenticate` tool.** Earlier drafts of the spec described one; it has been removed. Authentication is a server concern.
- **Don't trust client-supplied `withdrawal_account_id` blindly.** Re-resolve the account on the server side and check it belongs to the authenticated user.
