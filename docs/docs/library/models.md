---
title: Models
sidebar_position: 3
description: Pydantic models for every bank2ai input and output shape.
---

# Models

`bank2ai.models` exposes Pydantic models for every shape used in the spec, both the four shared data models (`Account`, `Transaction`, `Category`, `Recipient`) and the request/response shapes for each tool.

For canonical field-by-field documentation, see [Specification → Data models](/docs/specification/models). This page covers what's specific to using the models from Python.

## Shared data models

```python
from bank2ai import Account, Transaction, Category, Recipient
```

These are the types most handlers return. Each is a `BaseModel`:

- `Account`, id, accountNumber, currency, balance; optional typed identifiers `iban` / `bban` / `bic` / `maskedPan`; optional `availableBalance` / `overdraftLimit` / `ownerName` / `product` / `openedDate` / `balanceUpdatedAt`; optional `accountType`, `status`, `usage`, `isWithdrawalAccount`, `isDefaultAccount`. Credit accounts may also carry `statementBalance` / `minimumPaymentDue` / `paymentDueDate` / `statementClosingDate`. Field names follow [Berlin Group PSD2 `accountDetails`](https://www.berlin-group.org/openfinance-downloads) where they overlap.
- `Transaction`, id, description, amount (negative = expense), transaction_date, optional category_id (resolves via `get-categories`).
- `Category`, id, name (localized).
- `Recipient`, id, name, accountNumber, accountNumberType, socialSecurityNumber, optional bankInfo/paymentType/address/isFavorite/description.

## Enums

```python
from bank2ai import (
    AccountType, AccountStatus, AccountUsage,
    TransactionOrder, TransactionDirection,
)
```

- `AccountType`, `Current`, `Savings`, `Credit`, `Loan`, `Other`. Debit and prepaid cards live under `Current`; their attached card is signalled by `Account.maskedPan`.
- `AccountStatus`, `Enabled`, `Blocked`, `Deleted`.
- `AccountUsage`, `Private`, `Business`.
- `TransactionOrder`, `NewestFirst`, `OldestFirst`.
- `TransactionDirection`, `Income`, `Expenses` (required filter on `get-transactions-summary`).

## Tool-response shapes

Some tools return wrapped responses with a `content` field for human-readable status and an optional `item`/`actions` payload:

```python
from bank2ai import (
    TransactionsSummary, TransactionsSummaryGroup, TransactionsSummaryPeriod,
    CreateRecipientResponse,
    TransferPreparedResponse, TransferPreparedItem, TransferAction,
    ExecuteTransferResponse, ExecuteTransferDetail,
    RecipientInfo,
)
```

Use these for type-safe handler return values:

```python
async def create_recipient(*, name, account_number, kennitala) -> CreateRecipientResponse:
    try:
        rec = await acme_api.create_recipient(name, account_number, kennitala)
        return CreateRecipientResponse(
            content=f"Saved {name} as a recipient.",
            item=Recipient(...),
        )
    except DuplicateRecipientError:
        return CreateRecipientResponse(
            content=f"A recipient called '{name}' already exists.",
        )
```

## Returning dicts vs models

Both work. Models give you static typing and validation; dicts are sometimes more convenient when forwarding upstream payloads.

```python
# These are equivalent:
return Account(id="acc-1", accountNumber="…", currency="USD", balance=42.0)
return {"id": "acc-1", "accountNumber": "…", "currency": "USD", "balance": 42.0}
```

Pydantic / FastMCP validates either against the output schema before sending.

## Tolerating unknown fields

Per the [spec](/docs/specification/overview), clients MUST tolerate unknown fields on `Account`, `Transaction`, `Category`, and `Recipient`. If your bank exposes useful extras beyond what the spec defines, feel free to include them, old clients ignore unknowns; future clients can adopt them.
