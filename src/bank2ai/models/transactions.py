"""Transactions, categories, and the aggregated summary envelope.

Categories live here because they exist only to classify transactions.
"""

import datetime as _dt
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .base import _Bank2aiModel
from .identity import Party


class TransactionStatus(str, Enum):
    """Booking status of a transaction, per Berlin Group PSD2 `bookingStatus`.

    `Booked` is the default a client should assume when servers omit
    `Transaction.status`.
    """

    Booked = "Booked"
    Pending = "Pending"
    Information = "Information"


class TransactionCode(_Bank2aiModel):
    """ISO 20022 BankTransactionCode taxonomy.

    Three-level hierarchy (`domain` / `family` / `subFamily`). Servers
    MAY emit only `domain` if that is all the bank exposes; the deeper
    levels are populated when known.
    """

    domain: str = Field(
        description="Top-level transaction domain (e.g., `PMNT` for payments).",
        examples=["PMNT", "CASH", "ACMT"],
    )
    family: Optional[str] = Field(
        default=None,
        description="Mid-level family (e.g., `RCDT` for received credit transfers).",
        examples=["RCDT", "ICDT"],
    )
    subFamily: Optional[str] = Field(
        default=None,
        description="Sub-family (e.g., `SALA` for salary, `SUBS` for subscription).",
        examples=["SALA", "SUBS", "UPMT"],
    )


class RemittanceInformation(_Bank2aiModel):
    """Free-text and/or structured remittance information for a transaction.

    Profile of: ISO 20022 `RemittanceInformation`. Servers SHOULD populate
    this only when remittance info is genuinely present and not just a
    duplicate of `Transaction.description`.
    """

    unstructured: Optional[str] = Field(
        default=None,
        description="Free-text remittance line (e.g., the SEPA `RemittanceInformation/Unstructured` field).",
    )
    creditorReference: Optional[str] = Field(
        default=None,
        description=(
            "Structured creditor reference, typically an ISO 11649 RF-prefixed "
            "reference. The reference is opaque to bank2ai; servers pass it "
            "through as the bank exposes it."
        ),
        examples=["RF18539007547034"],
    )


class Transaction(_Bank2aiModel):
    """Financial transaction with date, amount and metadata.

    Profile of: ISO 20022 `EntryDetails2`, Berlin Group PSD2
    `transactions` array element, and Open Finance card transactions
    (`cardTransactions`). One shape covers both account and card
    transactions: the `_card` family of fields (`transactionDate`,
    `maskedPan`, counterparty.postalAddress, `merchantCategoryCode`,
    `proprietaryBankTransactionCode`) is populated for card entries,
    the `_sepa` family (`mandateId`, `creditorId`, `purposeCode`,
    `endToEndId`, `remittanceInformation`) for credit-transfer /
    direct-debit entries. Servers MAY omit any optional field; the
    `_Bank2aiModel` base drops `None` keys on the wire so every
    row stays lean for LLM consumption while a full audit view is
    available via `get-transaction`.

    `date` carries the most relevant time-anchor for the entry: the
    booking date when posted, the authorisation date for pending
    card authorisations. This diverges from ISO 20022 / Berlin Group
    field naming (`bookingDate`) on purpose — keeping a single,
    always-populated date field is friendlier for LLM consumption and
    means pending entries don't need a fabricated booking date.
    """

    id: str = Field(description="Unique transaction identifier (server-scoped).")
    accountId: str = Field(
        description="References the `id` of the `Account` this transaction belongs to.",
    )
    description: str = Field(
        description="Transaction description, merchant name or recipient name",
    )
    amount: float = Field(
        description=(
            "Transaction amount in the user's default currency "
            "(negative for expenses, positive for income). "
            "Clients SHOULD render this without a currency symbol unless "
            "the user has explicitly asked which currency a transaction is in."
        ),
    )
    date: _dt.date = Field(
        description=(
            "Primary date for this transaction, ISO 8601 (YYYY-MM-DD). "
            "For `Booked` entries this is the date the transaction "
            "posted to the account (formerly `bookingDate`; profile of "
            "ISO 20022 / Berlin Group `bookingDate`). For `Pending` "
            "authorisations — where no booking date exists yet — this "
            "is the authorisation / point-of-sale date (Open Finance "
            "`transactionDate`). Always populated so clients can sort "
            "and chart by `date` without branching on `status`."
        ),
    )
    status: Optional[TransactionStatus] = Field(
        default=None,
        description=(
            "Booking status. If omitted, clients SHOULD treat the transaction "
            "as `Booked`."
        ),
    )
    categoryId: Optional[str] = Field(
        default=None,
        description="Category id (the `id` field from get-categories which also has category name).",
    )
    transactionDate: Optional[_dt.date] = Field(
        default=None,
        description=(
            "Card swipe / authorisation date for `Booked` card "
            "entries where it differs from the posting `date` (Open "
            "Finance `transactionDate`). Servers SHOULD omit when "
            "equal to `date`, and MUST omit on `Pending` entries — for "
            "those, the authorisation date is carried by `date` itself."
        ),
    )
    maskedPan: Optional[str] = Field(
        default=None,
        description=(
            "Masked Primary Account Number of the card used for the "
            "transaction. Useful for distinguishing which physical / "
            "virtual card a charge belongs to when the same account "
            "has multiple cards attached. Servers MUST mask the middle "
            "digits."
        ),
        examples=["411111xxxxxx1111", "525412******3241"],
    )
    originalCurrency: Optional[str] = Field(
        default=None,
        description=(
            "ISO 4217 currency code of the original transaction, present only "
            "when the transaction was made in a currency other than the user's "
            "default. Pair with `originalAmount` to recover the original amount."
        ),
        pattern="^[A-Z]{3}$",
        examples=["EUR", "GBP", "JPY"],
    )
    originalAmount: Optional[float] = Field(
        default=None,
        description=(
            "Transaction amount in `originalCurrency` (negative for expenses, "
            "positive for income). Present only when `originalCurrency` is set."
        ),
    )
    merchantCategoryCode: Optional[str] = Field(
        default=None,
        description=(
            "ISO 18245 Merchant Category Code (4 digits). Card-payment "
            "entries SHOULD carry this when the acquirer exposes it; "
            "useful for spend analytics and merchant classification."
        ),
        pattern=r"^\d{4}$",
        examples=["5411", "5812"],
    )
    counterparty: Optional[Party] = Field(
        default=None,
        description=(
            "Typed counterparty record carrying the merchant or "
            "counterparty name and any structured detail the bank "
            "exposes (account identifier, BIC, national id, address). "
            "At `minimal` verbosity this is suppressed and clients "
            "fall back to `description`, which for most entries "
            "already embeds the counterparty name. For card "
            "transactions the merchant address (Open Finance "
            "`cardAcceptorAddress` — `townName`, `country`, `postCode`, "
            "`streetName`) goes on `counterparty.postalAddress`."
        ),
    )
    valueDate: Optional[_dt.date] = Field(
        default=None,
        description=(
            "Date the funds become available, ISO 8601. Servers SHOULD omit "
            "when equal to `date`. Profile of: ISO 20022 `ValueDate`."
        ),
    )
    categoryRaw: Optional[str] = Field(
        default=None,
        description=(
            "Bank-native category label as the upstream system exposes it. "
            "Useful when `categoryId` is mapped from something more specific."
        ),
    )
    transactionCode: Optional[TransactionCode] = Field(
        default=None,
        description="ISO 20022 BankTransactionCode classification of the entry.",
    )
    proprietaryBankTransactionCode: Optional[str] = Field(
        default=None,
        description=(
            "Bank-proprietary transaction code (Open Finance "
            "`proprietaryBankTransactionCode`). Free-form string the "
            "bank uses to classify the entry when an ISO 20022 "
            "`transactionCode` isn't exposed."
        ),
        examples=["PURCHASE", "ATM", "FEE", "REFUND"],
    )
    remittanceInformation: Optional[RemittanceInformation] = Field(
        default=None,
        description=(
            "Free-text and/or structured remittance info attached to the "
            "transaction. Servers SHOULD omit when it would duplicate "
            "`description`."
        ),
    )
    endToEndId: Optional[str] = Field(
        default=None,
        description=(
            "ISO 20022 cross-rail end-to-end identifier preserved across "
            "the payment chain."
        ),
    )
    mandateId: Optional[str] = Field(
        default=None,
        description=(
            "SEPA / direct-debit mandate identifier the bank associates "
            "with this entry. Profile of: ISO 20022 `MandateIdentification`."
        ),
        examples=["Mandate-2018-04-20-1234"],
    )
    creditorId: Optional[str] = Field(
        default=None,
        description=(
            "SEPA Creditor Identifier for direct-debit collections. "
            "Profile of: ISO 20022 `CreditorSchemeIdentification`."
        ),
        examples=["DE98ZZZ09999999999"],
    )
    purposeCode: Optional[str] = Field(
        default=None,
        description=(
            "ISO 20022 ExternalPurposeCode (4-letter) indicating the "
            "purpose of the payment, when the bank exposes it. "
            "Distinct from the BankTransactionCode taxonomy on "
            "`transactionCode`."
        ),
        examples=["SALA", "RENT", "GDDS"],
    )
    entryReference: Optional[str] = Field(
        default=None,
        description=(
            "Stable bank-side entry reference (Berlin Group "
            "`entryReference`). Distinct from `id` in that some banks "
            "expose an opaque server-scoped `id` but also carry the "
            "raw entry reference from the booking system; useful for "
            "delta-fetch / reconciliation."
        ),
    )
    additionalInformation: Optional[str] = Field(
        default=None,
        description=(
            "Free-form additional information the bank attaches to the "
            "entry and which does not fit any of the typed fields above "
            "(Berlin Group / Open Finance `additionalInformation`). "
            "Servers SHOULD omit when it would duplicate `description` "
            "or `remittanceInformation`."
        ),
    )


class GetTransactionResponse(BaseModel):
    """Result of looking up a single transaction by id.

    Returned by the `get-transaction` tool. The envelope mirrors the
    recoverable-error pattern used elsewhere in bank2ai: when the
    transaction is found `item` is populated and `content` is a brief
    status message; when it isn't, `item` is omitted and `content`
    explains why.
    """

    content: str = Field(description="Human-readable status message.")
    item: Optional[Transaction] = Field(
        default=None,
        description="The transaction when found.",
    )


class TransactionList(BaseModel):
    """Envelope for a list of transactions"""

    items: list[Transaction] = Field(description="Transactions matching the request.")
    nextCursor: Optional[str] = Field(
        default=None,
        description=(
            "Opaque cursor to pass back as `cursor` to fetch the next page. "
            "Absent or null when there are no more results."
        ),
    )


class TransactionOrder(str, Enum):
    """Sort order for transactions."""

    NewestFirst = "NewestFirst"
    OldestFirst = "OldestFirst"


class TransactionDirection(str, Enum):
    """Direction filter for transaction summaries."""

    Income = "Income"
    Expenses = "Expenses"


class TransactionsSummaryGroup(BaseModel):
    """One row of an aggregated transactions summary."""

    categoryId: Optional[str] = Field(
        default=None,
        description=(
            "Category id when the request grouped by `category` or `both`; "
            "null otherwise. Resolve to a name via get-categories."
        ),
    )
    month: Optional[str] = Field(
        default=None,
        description=(
            "ISO 8601 month (YYYY-MM) when the request grouped by `month` or `both`; "
            "null otherwise."
        ),
        examples=["2024-03"],
    )
    totalAmount: float = Field(description="Sum of transaction amounts in this group.")
    transactionCount: int = Field(
        description="Number of transactions contributing to this group.",
        ge=0,
    )
    averageAmount: float = Field(
        description="Mean transaction amount within this group.",
    )


class TransactionsSummaryPeriod(BaseModel):
    """Inclusive date range covered by a transactions summary."""

    startDate: str = Field(
        description="Inclusive lower bound, ISO 8601 (YYYY-MM-DD).",
        examples=["2024-03-01"],
    )
    endDate: str = Field(
        description="Inclusive upper bound, ISO 8601 (YYYY-MM-DD).",
        examples=["2024-03-31"],
    )


class TransactionsSummary(BaseModel):
    """Aggregated transactions summary"""

    summary: list[TransactionsSummaryGroup] = Field(
        description="One entry per aggregation key value.",
    )
    period: TransactionsSummaryPeriod = Field(
        description="Date range covered by the aggregation.",
    )
    total: float = Field(description="Sum across all groups in the summary.")


CANONICAL_CATEGORY_IDS: tuple[str, ...] = (
    "Income",
    "Transfer",
    "Groceries",
    "DiningAndEntertainment",
    "Transport",
    "Housing",
    "Utilities",
    "Shopping",
    "Health",
    "Travel",
    "Subscriptions",
    "Fees",
    "Cash",
    "Other",
)
"""Recommended `Category.id` values that all bank2ai servers SHOULD use
when a transaction maps cleanly to one of them. Servers MAY emit
additional, server-specific ids when nothing in the canonical list fits.
Clients MUST treat any `Category.id` as opaque (canonical ids are not
the only valid values)."""


class Category(_Bank2aiModel):
    """Transaction category for spending classification.

    bank2ai-defined categorization model; not profiled from a single
    upstream standard. Localized names live on this object so clients
    can render category labels per the user's locale; programmatic
    identity goes through `id`. See `CANONICAL_CATEGORY_IDS` for the
    recommended id values shared across servers.
    """

    id: str = Field(
        description=(
            "Unique category identifier. SHOULD be one of the canonical ids "
            "in `CANONICAL_CATEGORY_IDS` when a server's category maps "
            "cleanly; otherwise free-form server-specific."
        ),
        examples=["Groceries", "DiningAndEntertainment", "Other"],
    )
    name: str = Field(
        description="Category name (localized)",
        examples=["Groceries", "Transportation", "Entertainment", "Utilities"],
    )


class CategoryList(BaseModel):
    """Envelope for a list of categories"""

    items: list[Category] = Field(description="Available transaction categories.")
