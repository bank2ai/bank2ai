---
title: Changelog
sidebar_position: 2
description: Notable changes to the bank2ai specification and library.
---

# Changelog

The spec and the Python library version independently. This page tracks notable changes for each.

For the authoritative version field, see [`specs/bank2ai.json`](https://github.com/bank2ai/bank2ai/blob/main/specs/bank2ai.json).

## Specification

### 0.14.0, Draft

- **Breaking, `get-transactions` `verbosity` collapsed to two levels.** The middle `standard` tier is removed and `minimal` becomes the default. `minimal` carries `id`, `accountId`, `description`, `amount`, `date`, `categoryId`, and `originalCurrency` / `originalAmount` (populated only on FX entries) — the fields an LLM typically needs to answer everyday questions, with the merchant / counterparty name read off `description`. `full` allows every optional ISO 20022 / Open Finance audit field on top. Servers MAY still omit any optional field even at `full` when they don't have it.
- **Migration.** Callers passing `verbosity="standard"` or relying on the previous `standard` default need to pick a tier: stay on the new `minimal` default for list rendering, or pass `verbosity="full"` when the agent actually needs ISO 20022 / SEPA / card metadata. The `get-transaction` (singular) tool is unchanged and remains the canonical audit / reconciliation entry point.

### 0.13.0, Draft

- **Breaking, `Transaction.bookingDate` renamed to `Transaction.date`.** The field carries the booking date when `status` is `Booked` (formerly `bookingDate`; profile of ISO 20022 / Berlin Group `bookingDate`) and the authorisation / point-of-sale date when `status` is `Pending`. Previously, pending entries had to either fabricate a `bookingDate` or be dropped — neither is correct. `date` is always populated, so clients can sort and chart by it without branching on `status`. The spec narrative documents the deliberate divergence from ISO 20022 naming.
- **`transactionDate` semantics tightened.** Still optional, still the Open Finance `transactionDate` (card swipe / authorisation date), but populated only on `Booked` card entries where it differs from the posting `date`. On `Pending` entries the authorisation date lives on `date` itself, so `transactionDate` MUST be omitted there. Servers MUST also omit it when equal to `date`, as before.
- **Migration.** Rename every wire-level `bookingDate` to `date` (request handlers, fixtures, sort keys, filters); rename every reference in handler code that constructs `Transaction(...)` from `bookingDate=` to `date=`. The drift test catches anything missed on the server side; clients reading `tx['bookingDate']` need a one-line rename.

### 0.12.0, Draft

- **Transaction overhauled to cover account *and* card transactions in one shape**, aligned with Open Finance / Berlin Group `cardTransactions`. New optional fields: `transactionDate` (when the swipe / authorisation happened, distinct from `bookingDate` posting), `maskedPan` (which card was used), `proprietaryBankTransactionCode` (bank-proprietary code when the ISO 20022 `transactionCode` isn't exposed). New SEPA / audit fields: `mandateId`, `creditorId`, `purposeCode` (ISO 20022 ExternalPurposeCode), `entryReference` (Berlin Group stable booking-system reference), `additionalInformation` (free-form bank text not fitting the typed fields).
- **New `PostalAddress` component** (profile of ISO 20022 `PostalAddress24`): `streetName`, `buildingNumber`, `postCode`, `townName`, `countrySubDivision`, `country`, `addressLine`. Hung off `Party.postalAddress`, so for card transactions the Open Finance `cardAcceptorAddress` (`townName`, `country`, `postCode`, `streetName`) flows in on `Transaction.counterparty.postalAddress`.
- **Verbosity ladder rebalanced** so the standard payload carries the fields an LLM typically needs to answer everyday questions — `transactionDate`, `maskedPan`, `merchantCategoryCode`, `originalCurrency` / `originalAmount`, and the typed `counterparty` (with merchant address) — without forcing a `full` follow-up call. Deep ISO 20022 / SEPA metadata (`valueDate`, `transactionCode`, `remittanceInformation`, `endToEndId`, `mandateId`, `creditorId`, `purposeCode`, `entryReference`, `additionalInformation`, `proprietaryBankTransactionCode`, `categoryRaw`) stays at `full`.
- **Breaking, `Transaction.counterpartyName` removed.** The merchant / counterparty display name lives on `Transaction.counterparty.name` from `standard` verbosity onwards. At `minimal` verbosity the merchant name is read off `Transaction.description`, which for most bank entries already embeds it; servers that want to expose only the name keep using `description` and omit the typed counterparty.

### 0.11.0, Draft

- **Breaking, vocabulary alignment.** The whole spec migrates to camelCase model field names, matching the PSD2 / ISO 20022 conventions the spec profiles. `Transaction.transaction_date` becomes `bookingDate`, `category_id` becomes `categoryId`, the `currency` / `amount_in_currency` FX pair becomes `originalCurrency` / `originalAmount`. The `TransactionsSummary*` models migrate in the same pass (`total_amount` → `totalAmount`, etc.). Tool input parameter names stay snake_case (Python kwargs; bridged to wire by `register_tools`). See [Migrating from 0.10](./migrating-from-0.10.md).
- **Breaking, Transaction shape.** `id` is now required (previously optional). New required `accountId` links each transaction to its `Account`. New optional `status` (`Booked` | `Pending` | `Information`; defaults to `Booked` when omitted) profiles Berlin Group `bookingStatus`. New optional `counterpartyName`. Seven new optional ISO 20022 metadata fields: `valueDate`, `categoryRaw`, `counterparty` (typed `Party`), `transactionCode` (ISO 20022 `BankTransactionCode`), `remittanceInformation`, `endToEndId`, `merchantCategoryCode`. Servers populate what they have; the None-omitting serializer drops the rest.
- **`get-transactions` gains a `verbosity` parameter** (`minimal` | `standard` | `full`, default `standard`) capping how many optional fields each Transaction may carry. Servers MAY omit any optional field even at `full` if they don't have it.
- **New `get-transaction` (singular) tool** for the audit / reconciliation entry point: returns a single Transaction at full verbosity, including all ISO 20022 metadata the server can populate.
- **Canonical `Category.id` taxonomy published.** Servers SHOULD use one of the 14 canonical ids (`Income`, `Transfer`, `Groceries`, `DiningAndEntertainment`, `Transport`, `Housing`, `Utilities`, `Shopping`, `Health`, `Travel`, `Subscriptions`, `Fees`, `Cash`, `Other`) when a transaction maps cleanly. Non-canonical ids remain valid for server-specific extensions.
- **Breaking, Recipient rebuilt** on the typed `AccountIdentifier` discriminated union (`iban` / `bban` / `accountNumber` / `alias` variants, profiled from ISO 20022 `AccountIdentification4Choice`) and the typed `nationalId` sub-object. Dropped: `accountNumber`+`accountNumberType` pair, required `socialSecurityNumber`, `bankInfo`, `paymentType`, `address`, `description`, and the unused `RecipientInfo` base class. Added: `nickname`, `bic`, `defaultDescription`, `lastUsedAt`.
- **Breaking, `create-recipient` migrated** to typed inputs: `account_identifier`, `national_id` (typed object with opaque `type` label), `nickname`, `bic`, `default_description`. Replaces the previous `account_number` + `kennitala` kwargs.
- **New polymorphic `prepare-transfer` tool** for transfers on any supported rail (`Rail` enum: `domestic-IS`, `sepa`, `sepa-instant`, `swift`, plus vendor extensions). Inputs take a typed creditor `Party`, instructed amount + currency, the rail, and optional rail-specific bits (`local_instrument`, `requested_execution_date`, `remittance_information`, `end_to_end_id`, `description`). Returns a `PreparedTransfer` with `transferIntentId`, `expiresAt`, and slots for fees / FX / Confirmation of Payee / warnings / estimated settlement plus a validated `summary` echo.
- **Breaking, `execute-transfer` takes only `transfer_intent_id`** (and an optional `idempotency_key`). The intent's amount, creditor, debtor, and rail are immutable: any change requires a fresh `prepare-transfer` call. New `ExecutedTransfer` shape (`transactionId` linking back to `Transaction.id`, `TransferExecutionStatus` enum, optional `rejectionReason`, `executedAt`).
- **`prepare-transfer-icelandic` is removed.** Use `prepare-transfer` with `rail=domestic-IS` instead. The polymorphic tool covers the same flow with a single shape.
- **Safety contract documented in §5a.** Idempotency keys (optional, ≤128 chars, per-`(tool, caller)` scoping with ≥24h dedup window) accepted on every mutating tool. Intent expiry contract (5 min default) with structured `code: "intent_expired"` on execute against expired intent. Immutable amount / recipient / debtor / rail binding between prepare and execute. Structured Confirmation of Payee on rails that support payee verification.
- **Recoverable-error envelopes carry a structured `code` field.** Canonical values: `intent_not_found`, `intent_expired` on `execute-transfer`; `missing_creditor_identifier`, `insufficient_funds`, `invalid_account`, `invalid_recipient` on the prepare paths. Unknown codes MUST be treated as opaque.
- **`Account.balances` typed array added** for servers that expose multiple balance types (`ClosingBooked`, `Expected`, `InterimAvailable`, `ForwardAvailable`, `NonInvoiced`). Top-level `balance` / `availableBalance` remain required as derived shortcuts; servers MUST keep them consistent with the corresponding `balances` entries when both are present.
- **Field omission rule promoted to the spec preamble** and the "Profile of:" convention introduced in §3. Servers SHOULD omit optional fields whose values are null, empty, or equal to a documented default; clients MUST tolerate missing optional fields and unknown additional fields.

### 0.10.0, Draft

- `Account` overhauled with the standard banking properties most issuers expose, with field names following [Berlin Group PSD2 `accountDetails`](https://www.berlin-group.org/openfinance-downloads) where they overlap. New optional fields: typed identifiers `iban` / `bban` / `bic` / `maskedPan`, plus `ownerName`, `product`, `status`, `usage`, `openedDate`, `balanceUpdatedAt`. Credit accounts may also carry `statementBalance`, `minimumPaymentDue`, `paymentDueDate`, and `statementClosingDate` so an agent can answer "what do I owe and when?" without a second call.
- `AccountType` extended with `Loan` and `Other`. Debit and prepaid cards live under `Current`; their attached card is signalled by `Account.maskedPan`.
- `get-accounts` gains optional `status` and `usage` filters; `account_type` accepts the new enum values.

### 0.9.0, Draft

- **Breaking:** categories are referenced by id, not name. `Transaction.category` (string name) becomes `Transaction.category_id`; `TransactionsSummaryGroup.category` becomes `category_id`. The `categories` input on `get-transactions` and `get-transactions-summary` is renamed to `category_ids` and now takes `Category.id` values from `get-categories`. `Category.name` is unchanged and remains the only place a category's localized name lives.

### 0.7.0, Draft

- **Breaking:** tool names overhauled for consistency. `transactions-summary` → `get-transactions-summary`, `recipients-by-name` → `get-recipients`, `transfer-money-icelandic` → `prepare-transfer-icelandic`. Reads now use `get-<plural>`; writes stay verb-noun. Handler kwargs match: `search_recipients` → `get_recipients`, `prepare_transfer` → `prepare_transfer_icelandic`.

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

### 0.5.0

- **Breaking:** tracks spec 0.12.0–0.14.0. `Transaction.bookingDate` is renamed to `Transaction.date` and always populated (booking date when `Booked`, authorisation date when `Pending`). `Transaction.counterpartyName` is removed — read the merchant / counterparty name off `Transaction.description` at `minimal` verbosity, or `Transaction.counterparty.name` from `full`.
- **Breaking:** `get-transactions` `verbosity` is now `Literal["minimal", "full"]` with `minimal` as the default. The previous `standard` tier is gone; callers relying on the standard payload should pass `verbosity="full"` when they actually need ISO 20022 / SEPA / card metadata.
- Transaction expanded to cover card transactions in one shape: new optional fields `transactionDate`, `maskedPan`, `proprietaryBankTransactionCode`, `mandateId`, `creditorId`, `purposeCode`, `entryReference`, `additionalInformation`. New `PostalAddress` component hung off `Party.postalAddress`, so card-transaction `cardAcceptorAddress` flows in on `Transaction.counterparty.postalAddress`.
- `register_tools` gains an `output_schemas: Literal["inline", "discovery", "off"]` keyword (default `"inline"`). In `"discovery"` mode the bank2ai tools omit `outputSchema` from `tools/list` and a companion `describe-tools` tool is registered so clients can fetch schemas on demand. In `"off"` mode schemas are suppressed without the companion tool.
- Internal: `bank2ai.models` and `bank2ai.tools` are reorganized into domain submodules (`accounts`, `transactions`, `recipients`, `transfers`, `identity`). Public imports (`from bank2ai import …` and `from bank2ai.models import …`) are unchanged.

### 0.4.0

- **Breaking:** tracks spec 0.11.0. Tool handler kwargs change shape on the mutating tools: `create-recipient` takes `account_identifier` and `national_id` (replacing `account_number` and `kennitala`), `prepare-transfer` is new with a typed `creditor` Party, `execute-transfer` takes only `transfer_intent_id` (replacing `withdrawal_account_id`, `recipient_account_number`, `amount`, `description`). Every mutating tool also accepts an optional `idempotency_key`.
- **Breaking:** Pydantic model field names migrate to camelCase across `Transaction`, `TransactionsSummaryGroup`, `TransactionsSummaryPeriod`, `TransferAction` etc. Renamed models: `TransferPreparedItem` → `PreparedTransfer`, `ExecuteTransferDetail` → `ExecutedTransfer`. New envelope `PrepareTransferResponse` replaces the previous `TransferPreparedResponse` and gains a `code` field; `CreateRecipientResponse` and `ExecuteTransferResponse` likewise gain `code`.
- **Breaking:** dropped the unused `RecipientInfo` base class.
- New public types: `AccountIdentifier` (discriminated union) and its four variants (`IbanIdentifier`, `BbanIdentifier`, `AccountNumberIdentifier`, `AliasIdentifier`), `AliasType`, `NationalId`, `NationalIdType`, `Party`, `TransactionCode`, `TransactionStatus`, `RemittanceInformation`, `Rail`, `TransferFee`, `TransferFx`, `ConfirmationOfPayee`, `ConfirmationOfPayeeStatus`, `TransferWarning`, `TransferWarningSeverity`, `TransferSummary`, `TransferExecutionStatus`, `Balance`, `BalanceType`, `GetTransactionResponse`, and the `CANONICAL_CATEGORY_IDS` constant.
- New `register_tools` handler kwargs: `get_transaction` (singular) and `prepare_transfer` (polymorphic).

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
