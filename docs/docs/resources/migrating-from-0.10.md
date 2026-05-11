---
title: Migrating from 0.10
sidebar_position: 3
description: Side-by-side guide for upgrading a bank2ai client or server from spec 0.10.0 to 0.11.0.
---

# Migrating from 0.10 to 0.11

The 0.11 release is a breaking vocabulary alignment that profiles every model against an upstream standard (PSD2 / ISO 20022 / Berlin Group / FDX), introduces a polymorphic transfer surface, and pins down a uniform safety contract across mutating tools. This page is a side-by-side map of what changes and how to update.

## Field naming: snake_case → camelCase

Every model field on the wire is camelCase in 0.11. The only places snake_case survives are Python tool handler kwargs (bridged to wire by `register_tools`) and the `TransactionsSummary*` filters.

| 0.10 (snake_case) | 0.11 (camelCase) |
| --- | --- |
| `Transaction.transaction_date` | `Transaction.bookingDate` (also adopts the ISO 20022 / Berlin Group name) |
| `Transaction.category_id` | `Transaction.categoryId` |
| `Transaction.amount_in_currency` | `Transaction.originalAmount` |
| `Transaction.currency` (FX-only) | `Transaction.originalCurrency` |
| `TransactionsSummaryGroup.category_id` / `total_amount` / `transaction_count` / `average_amount` | `categoryId` / `totalAmount` / `transactionCount` / `averageAmount` |
| `TransactionsSummaryPeriod.start_date` / `end_date` | `startDate` / `endDate` |

## Transaction shape

```jsonc
// 0.10
{
  "id": "tx_001",
  "description": "Monthly Salary",
  "amount": 4500.00,
  "transaction_date": "2024-03-15",
  "category_id": "cat_income"
}

// 0.11 — required fields
{
  "id": "tx_001",
  "accountId": "acc_checking_001",  // now required: links to Account.id
  "description": "Monthly Salary",
  "amount": 4500.00,
  "bookingDate": "2024-03-15"
}
```

- `id` is now required (was optional).
- `accountId` is a new required field linking each transaction to its `Account`.
- `status` is optional and defaults to `"Booked"` when omitted (profile of Berlin Group `bookingStatus`).
- `counterpartyName` is a new optional best-effort merchant / counterparty display string.

### New optional ISO 20022 fields

Servers populate what they have; the None-omitting serializer drops the rest, so an empty server costs zero bytes.

| Field | Profile | When to populate |
| --- | --- | --- |
| `valueDate` | ISO 20022 `ValueDate` | Settlement date if it differs from `bookingDate` |
| `categoryRaw` | bank-native | When `categoryId` was mapped from a more specific raw label |
| `counterparty` | typed `Party` | When more than just `counterpartyName` is known |
| `transactionCode` | ISO 20022 `BankTransactionCode` (`domain` / `family?` / `subFamily?`) | When the bank exposes the taxonomy |
| `remittanceInformation` | ISO 20022 `RemittanceInformation` | When remittance info is not just a duplicate of `description` |
| `endToEndId` | ISO 20022 end-to-end identifier | When the rail carries one |
| `merchantCategoryCode` | ISO 18245 MCC (4 digits) | Card transactions on rails that expose the MCC |

### Verbosity caps how many optional fields land

`get-transactions` now takes a `verbosity` parameter (`minimal` | `standard` | `full`, default `standard`) that caps the optional fields each Transaction may carry. Servers MAY still omit anything they don't have, even at `full`.

```jsonc
// minimal — required only plus counterpartyName
{ "id", "accountId", "description", "amount", "bookingDate", "counterpartyName?" }

// standard (default) — adds the Berlin-Group-style fields
{ ..., "status?", "categoryId?", "originalCurrency?", "originalAmount?" }

// full — adds every optional ISO 20022 field
{ ..., "valueDate?", "categoryRaw?", "counterparty?", "transactionCode?",
       "remittanceInformation?", "endToEndId?", "merchantCategoryCode?" }
```

### `get-transaction` (singular) for detail-on-demand

```python
# Audit / reconciliation flow: lookup by id, always at full verbosity
response = await client.call_tool(
    "get-transaction",
    {"transaction_id": "tx_001"},
)
```

## Categories: canonical id taxonomy

Servers SHOULD use one of the 14 canonical `Category.id` values when a category maps cleanly:

```
Income, Transfer, Groceries, DiningAndEntertainment, Transport, Housing,
Utilities, Shopping, Health, Travel, Subscriptions, Fees, Cash, Other
```

Non-canonical ids remain valid for server-specific extensions; clients MUST treat any `Category.id` as opaque.

## Recipient shape

```jsonc
// 0.10
{
  "id": "rcpt_001",
  "name": "Jane Doe",
  "accountNumber": "5678-90-123456",
  "accountNumberType": "Domestic",
  "bankInfo": "Demo Bank",
  "paymentType": "Domestic",
  "socialSecurityNumber": "123-45-6789",  // required
  "isFavorite": true,
  "description": "Friend"
}

// 0.11
{
  "id": "rcpt_001",
  "name": "Jane Doe",
  "accountIdentifier": {  // typed, replaces accountNumber + accountNumberType
    "type": "accountNumber",
    "accountNumber": "5678-90-123456",
    "country": "US",
    "routing": "021000021"
  },
  "nationalId": {  // typed, optional (replaces required socialSecurityNumber)
    "value": "123-45-6789",
    "country": "US",
    "type": "ssn"
  },
  "nickname": "Friend",
  "isFavorite": true
}
```

- `accountNumber` + `accountNumberType` collapse into the typed `accountIdentifier` discriminated union with four variants: `iban`, `bban`, `accountNumber`, `alias`.
- `socialSecurityNumber` (required) becomes `nationalId` (optional, typed object). `type` is an opaque label (`kennitala`, `ssn`, `cpr`, `personnummer`, `cpf`, `other`); bank2ai does not validate the value.
- Dropped: `bankInfo`, `paymentType`, `address`, `description`. Added: `nickname`, `bic`, `defaultDescription`, `lastUsedAt`.
- The `RecipientInfo` Python base class is removed.

### `create-recipient` inputs

```python
# 0.10
await client.call_tool("create-recipient", {
    "name": "Jane Doe",
    "account_number": "5678-90-123456",
    "kennitala": "010190-1234",
})

# 0.11
await client.call_tool("create-recipient", {
    "name": "Jane Doe",
    "account_identifier": {
        "type": "bban",
        "bban": "0133-26-007890",
        "country": "IS",
    },
    "national_id": {
        "value": "010190-1234",
        "country": "IS",
        "type": "kennitala",
    },
    "nickname": "Friend",  # optional
    "idempotency_key": "client-recipient-001",  # optional
})
```

## Transfer surface: prepare-transfer is polymorphic; execute-transfer is intent-id-only

```python
# 0.10 — Icelandic-specific tool, execute takes the full details again
prepared = await client.call_tool("prepare-transfer-icelandic", {
    "amount": 100.0,
    "recipient_ssn": "010190-1234",
    "recipient_account_number": "0133-26-007890",
    "description": "Lunch share",
})
await client.call_tool("execute-transfer", {
    "withdrawal_account_id": "acc_checking_001",
    "recipient_account_number": "0133-26-007890",
    "amount": 100.0,
    "description": "Lunch share",
})

# 0.11 — polymorphic prepare-transfer with rail; execute takes only the intent id
prepared = await client.call_tool("prepare-transfer", {
    "debtor_account_id": "acc_checking_001",
    "creditor": {
        "name": "Jón Jónsson",
        "accountIdentifier": {
            "type": "bban",
            "bban": "0133-26-007890",
            "country": "IS",
        },
        "nationalId": {
            "value": "010190-1234",
            "country": "IS",
            "type": "kennitala",
        },
    },
    "amount": 100.0,
    "currency": "ISK",
    "rail": "domestic-IS",
    "description": "Lunch share",
})
intent_id = prepared["item"]["transferIntentId"]
await client.call_tool("execute-transfer", {"transfer_intent_id": intent_id})
```

The `Rail` enum ships with `domestic-IS`, `sepa`, `sepa-instant`, `swift`; servers MAY register more values via vendor extensions.

`prepare-transfer-icelandic` stays registered as a deprecated alias that maps the legacy inputs onto the polymorphic tool internally, so old clients keep working unchanged. Plan to call `prepare-transfer` directly in new code.

### `PreparedTransfer` envelope

```jsonc
{
  "content": "A transfer has been prepared. ...",
  "item": {
    "transferIntentId": "intent_...",
    "expiresAt": "2024-03-15T08:35:00Z",  // 5 min default
    "fees": [{ "amount": 0.50, "currency": "EUR", "description": "SEPA fee" }],
    "fx": { /* present on cross-currency transfers */ },
    "confirmationOfPayee": {
      "status": "match"  // or close-match | no-match | unavailable
    },
    "warnings": [],
    "summary": {
      // validated, normalised echo of the inputs
      "debtorAccount": { /* Account snapshot */ },
      "creditor": { /* Party */ },
      "amount": 100.0,
      "currency": "ISK",
      "rail": "domestic-IS",
      "endToEndId": "e2e_...",  // always populated; server-generated if not provided
      "description": "Lunch share"
    }
  }
}
```

## Safety contract on mutating tools

Every mutating tool (`create-recipient`, `prepare-transfer`, `prepare-transfer-icelandic`, `execute-transfer`) accepts an optional `idempotency_key` (≤128 chars). Servers SHOULD return the original response for repeat calls with the same key within at least 24 hours. The key is scoped per `(tool, caller)`; two unrelated callers cannot collide.

The mutating-tool response envelopes (`CreateRecipientResponse`, `PrepareTransferResponse`, `ExecuteTransferResponse`) carry an optional structured `code` field on recoverable errors. Canonical values: `intent_not_found`, `intent_expired`, `missing_creditor_identifier`, `insufficient_funds`, `invalid_account`, `invalid_recipient`. Unknown codes MUST be treated as opaque.

`execute-transfer` rejects expired intents with `code: "intent_expired"`; the intent's `expiresAt` is 5 minutes after `prepare-transfer` by default. The intent's amount, creditor, debtor, and rail are immutable — any change requires a fresh `prepare-transfer` call.

## Account: typed `balances` array (additive)

```jsonc
{
  "id": "acc_checking_001",
  "balance": 5420.50,           // required, derived shortcut for ClosingBooked
  "availableBalance": 5420.50,  // optional, derived shortcut for InterimAvailable
  "balances": [                  // new, optional
    { "type": "ClosingBooked",    "amount": 5420.50, "currency": "USD", "asOf": "2024-03-15T08:30:00Z" },
    { "type": "InterimAvailable", "amount": 5420.50, "currency": "USD", "asOf": "2024-03-15T08:30:00Z" }
  ]
}
```

The top-level scalars stay as derived shortcuts; servers MUST keep them consistent with the corresponding `balances` entries when both are present. Servers that only have the scalars omit `balances` and the None-omitting serializer drops it from the wire payload.

## Field omission and tolerance

The spec preamble now documents the lean-payload rule explicitly: servers SHOULD omit optional fields whose values are null, empty, or equal to a documented default; clients MUST tolerate missing optional fields and unknown additional fields. The Python reference implementation does this automatically via the `_Bank2aiModel` base class. Required fields are unaffected.

## Checklist for updating a server

1. Bump `bank2ai` dependency to `>=0.4.0`.
2. Migrate model field names to camelCase in any handler that constructs `Transaction` or `TransactionsSummary*` objects.
3. Make `Transaction.id` and `Transaction.accountId` populated on every transaction your server emits.
4. Update `create-recipient` handler signature: `account_identifier`, `national_id`, `nickname`, `bic`, `default_description`, `idempotency_key` (replacing `account_number` and `kennitala`).
5. Add a new `prepare_transfer` handler with the polymorphic signature; keep `prepare_transfer_icelandic` as a thin alias that delegates internally.
6. Replace your `execute_transfer` handler to take only `transfer_intent_id` (and optional `idempotency_key`); add a short-lived intent store keyed by `transferIntentId`.
7. (Optional) Map your bank's category labels onto the canonical `CANONICAL_CATEGORY_IDS` taxonomy.
8. (Optional) Populate `Transaction` optional fields (`status`, `counterparty`, `transactionCode`, ...) and `Account.balances` from your upstream data when available.

## Checklist for updating a client

1. Read Transaction fields with the new camelCase names (`bookingDate`, `categoryId`, `originalCurrency`, `originalAmount`).
2. When listing transactions, set `verbosity` to `minimal` for compact UIs, leave it at `standard` for general use, or use `full` only when the agent actually needs ISO 20022 metadata.
3. Use `get-transaction` (singular) for detail / audit views rather than asking for `verbosity: "full"` on a list.
4. For new transfer flows, call `prepare-transfer` with a typed `creditor` `Party` and a `rail`; the response's `transferIntentId` is the only thing `execute-transfer` needs.
5. Generate an `idempotency_key` per logical user action (e.g., one UUID per "send money" press) and pass it on every mutating call.
6. Branch on the structured `code` field on recoverable errors rather than parsing `content`.
