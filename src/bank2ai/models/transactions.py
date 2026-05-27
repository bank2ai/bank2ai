"""Transactions, categories, and the aggregated summary envelope.

Categories live here because they exist only to classify transactions.
"""

import datetime as _dt
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .base import _Bank2aiModel
from .identity import Party


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
    transactions. Heavily-used fields (`transactionDate`, `counterparty`,
    FX `originalAmount` / `originalCurrency`) sit on the top-level
    model; everything else — remittance text, end-to-end / mandate /
    creditor ids, purpose / transaction codes, MCC, masked PAN, and
    other ISO 20022 / Open Finance audit metadata — lives under
    `properties` as string entries (see the field for the list of
    known keys). Servers MAY omit any optional field and SHOULD drop
    unset optional keys on the wire so every row stays lean for LLM
    consumption; a full audit view is available via `get-transaction`.

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
    originalDescription: Optional[str] = Field(
        default=None,
        description=(
            "Raw merchant / counterparty string as the payment rail "
            "delivered it, before any server-side cleanup or "
            "categorisation. Servers SHOULD populate this only when it "
            "differs from `description`; when the two would be equal, "
            "omit `originalDescription` so clients don't have to dedupe."
        ),
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
            "For booked entries (`isPending` absent or false) this is the date the "
            "transaction posted to the account (formerly `bookingDate`; "
            "profile of ISO 20022 / Berlin Group `bookingDate`). For "
            "pending authorisations (`isPending=true`) — where no "
            "booking date exists yet — this is the authorisation / "
            "point-of-sale date (Open Finance `transactionDate`). "
            "Always populated so clients can sort and chart by `date` "
            "without branching on `isPending`."
        ),
    )
    isPending: Optional[bool] = Field(
        default=None,
        description=(
            "True for authorisations not yet posted to the account. "
            "Profile of Berlin Group PSD2 `bookingStatus` collapsed to "
            "a boolean (Booked → false / absent, Pending → true). "
            "Servers SHOULD set this to true only for pending "
            "authorisations and SHOULD omit the field on booked "
            "entries (the common case) to keep payloads lean. Clients "
            "MUST treat an absent `isPending` as equivalent to false."
        ),
    )
    categoryId: Optional[str] = Field(
        default=None,
        description="Category id (the `id` field from get-categories which also has category name).",
    )
    transactionDate: Optional[_dt.date] = Field(
        default=None,
        description=(
            "Card swipe / authorisation date for booked card entries "
            "where it differs from the posting `date` (Open Finance "
            "`transactionDate`). Servers SHOULD omit when equal to "
            "`date`, and MUST omit on pending entries — for those, the "
            "authorisation date is carried by `date` itself."
        ),
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
    properties: Optional[dict[str, str]] = Field(
        default=None,
        description=(
            "Open bag of rarely-used metadata keyed by string. Servers "
            "populate whatever they have; clients tolerate any subset and "
            "any extra server-specific keys. Known keys (servers SHOULD "
            "use these names when populating the corresponding value):\n"
            "- `remittanceInformation`: free-text remittance line (SEPA `RemittanceInformation/Unstructured`); omit when it would duplicate `description`.\n"
            "- `creditorReference`: structured creditor reference, typically ISO 11649 RF-prefixed.\n"
            "- `endToEndId`: ISO 20022 cross-rail end-to-end identifier preserved across the payment chain.\n"
            "- `maskedPan`: masked card PAN; middle digits MUST be masked.\n"
            "- `merchantCategoryCode`: ISO 18245 4-digit MCC for card entries.\n"
            "- `categoryRaw`: bank-native category label upstream of `categoryId`.\n"
            "- `transactionCode`: ISO 20022 BankTransactionCode as `domain[-family[-subFamily]]` (Berlin Group convention, e.g. `PMNT-RCDT-SALA`).\n"
            "- `proprietaryBankTransactionCode`: bank-proprietary transaction code (e.g. `PURCHASE`, `ATM`).\n"
            "- `mandateId`: SEPA / direct-debit mandate identifier.\n"
            "- `creditorId`: SEPA Creditor Identifier (direct-debit collections).\n"
            "- `purposeCode`: ISO 20022 ExternalPurposeCode (4 letters, e.g. `SALA`, `RENT`).\n"
            "- `entryReference`: stable bank-side entry reference (Berlin Group `entryReference`).\n"
            "- `additionalInformation`: free-form bank-attached info that doesn't fit elsewhere."
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
