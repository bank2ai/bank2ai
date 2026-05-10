"""Data models for bank integrations."""

from datetime import date, datetime
from enum import Enum
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field, model_serializer


class _Bank2aiModel(BaseModel):
    """Base for documented bank2ai models. Drops None-valued keys on
    serialization so optional fields that are absent on a row don't bloat
    every tool response. The JSON Schema marks these fields optional with
    `default: null`, so omission is conformant; clients must already tolerate
    either form."""

    @model_serializer(mode="wrap")
    def _omit_none(self, handler):
        data = handler(self)
        return {k: v for k, v in data.items() if v is not None}


# ---- Shared identity primitives ----
#
# `AccountIdentifier` and `Party` are used by transaction counterparties,
# transfer creditor details, and (in a later release) `Recipient`.


class AliasType(str, Enum):
    """Type tag for alias-based account identifiers (UPI VPA, Pix key, email-routed payments, etc.)."""

    Email = "email"
    Phone = "phone"
    VPA = "vpa"
    Pix = "pix"
    Other = "other"


class NationalIdType(str, Enum):
    """Opaque label for the kind of national identifier carried in `NationalId.value`.

    bank2ai does not validate national-ID formats; this is a hint so
    clients can render or route appropriately. Servers SHOULD set the
    closest-matching value or use `other`.
    """

    SSN = "ssn"
    Kennitala = "kennitala"
    CPR = "cpr"
    Personnummer = "personnummer"
    CPF = "cpf"
    Other = "other"


class IbanIdentifier(_Bank2aiModel):
    """IBAN-routed account, ISO 13616."""

    type: Literal["iban"] = Field(default="iban", description="Discriminator: `iban`.")
    iban: str = Field(
        description="IBAN, ISO 13616.",
        pattern=r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}$",
        examples=["GB29NWBK60161331926819", "DE89370400440532013000"],
    )


class BbanIdentifier(_Bank2aiModel):
    """Domestic Basic Bank Account Number, used in markets without an IBAN."""

    type: Literal["bban"] = Field(default="bban", description="Discriminator: `bban`.")
    bban: str = Field(
        description="Domestic account identifier in the country's native format.",
        examples=["0133-26-007890"],
    )
    country: str = Field(
        description="ISO 3166-1 alpha-2 country code.",
        pattern=r"^[A-Z]{2}$",
        examples=["IS", "GB"],
    )


class AccountNumberIdentifier(_Bank2aiModel):
    """Country-specific composite for non-IBAN markets (US, UK pre-IBAN, etc.)."""

    type: Literal["accountNumber"] = Field(
        default="accountNumber",
        description="Discriminator: `accountNumber`.",
    )
    accountNumber: str = Field(
        description="Account number in the country's native format.",
    )
    country: str = Field(
        description="ISO 3166-1 alpha-2 country code.",
        pattern=r"^[A-Z]{2}$",
        examples=["US", "GB"],
    )
    routing: Optional[str] = Field(
        default=None,
        description="US ABA routing number, when applicable.",
    )
    sortCode: Optional[str] = Field(
        default=None,
        description="UK sort code, when applicable.",
    )


class AliasIdentifier(_Bank2aiModel):
    """Alias-based identifier (UPI VPA, Pix key, email-routed payments, etc.)."""

    type: Literal["alias"] = Field(default="alias", description="Discriminator: `alias`.")
    alias: str = Field(
        description="The alias value as the user knows it.",
        examples=["alex@upi", "+44-7700-900000"],
    )
    aliasType: AliasType = Field(description="Kind of alias.")


AccountIdentifier = Annotated[
    Union[
        IbanIdentifier,
        BbanIdentifier,
        AccountNumberIdentifier,
        AliasIdentifier,
    ],
    Field(
        discriminator="type",
        description=(
            "Discriminated union of typed account identifiers. Profile of: "
            "ISO 20022 `AccountIdentification4Choice`."
        ),
    ),
]


class NationalId(_Bank2aiModel):
    """Person or business national identifier."""

    value: str = Field(
        description="National identifier value, in the country's native format.",
        examples=["010190-1234", "123-45-6789"],
    )
    country: str = Field(
        description="ISO 3166-1 alpha-2 country code.",
        pattern=r"^[A-Z]{2}$",
        examples=["IS", "US"],
    )
    type: Optional[NationalIdType] = Field(
        default=None,
        description="Hint for the kind of identifier. bank2ai does not validate the value.",
    )


class Party(_Bank2aiModel):
    """Counterparty in a transaction or transfer.

    Profile of: ISO 20022 `PartyIdentification135` (subset).
    """

    name: str = Field(description="Party's full name or business name.")
    accountIdentifier: Optional[AccountIdentifier] = Field(
        default=None,
        description="Party's account identifier when known.",
    )
    bic: Optional[str] = Field(
        default=None,
        description="BIC / SWIFT code of the party's bank, ISO 9362.",
        pattern=r"^[A-Z]{6}[A-Z2-9][A-NP-Z0-9]([A-Z0-9]{3})?$",
        examples=["NWBKGB2L"],
    )
    nationalId: Optional[NationalId] = Field(
        default=None,
        description="Party's national identifier when known.",
    )


class RecipientInfo(_Bank2aiModel):
    """Basic recipient information for transfers."""

    name: str = Field(description="Recipient's full name or business name")
    socialSecurityNumber: str = Field(
        description="National ID / SSN (format varies by country)",
    )
    accountNumber: str = Field(description="Recipient's bank account number")


class Recipient(RecipientInfo):
    """Payment recipient with account details"""

    id: Optional[str] = Field(default=None, description="Unique recipient identifier")
    name: str = Field(description="Recipient's full name or business name")
    accountNumber: str = Field(
        description="Recipient's bank account number",
        examples=["5678-90-123456", "GB29NWBK60161331926819"],
    )
    accountNumberType: Optional[str] = Field(
        default=None,
        description="Type of account number",
        examples=["Domestic", "IBAN", "SWIFT"],
    )
    bankInfo: Optional[str] = Field(
        default=None,
        description="Bank name or identifier",
        examples=["Example Bank", "Bank of America"],
    )
    paymentType: Optional[str] = Field(
        default=None,
        description="Type of payment supported",
        examples=["Domestic", "International", "SEPA"],
    )
    socialSecurityNumber: str = Field(
        description="National ID / SSN (format varies by country)",
        examples=["010190-1234", "123-45-6789"],
    )
    address: Optional[str] = Field(
        default=None,
        description="Recipient's address (if available)",
    )
    isFavorite: bool = Field(
        default=False,
        description="Whether this recipient is marked as favorite",
    )
    description: Optional[str] = Field(
        default=None,
        description="User-provided description or note",
        examples=["Friend", "Landlord", "Contractor"],
    )


class AccountType(str, Enum):
    """Type of bank account.

    Aligned with the ISO 20022 ExternalCashAccountType1Code values exposed
    via the Berlin Group PSD2 `cashAccountType`, collapsed to the buckets
    that map cleanly across regions and reflect distinctions a user would
    actually ask about:

      - `Current`  - day-to-day transaction account (ISO 20022 CACC).
                     Debit cards and stored-value / prepaid cards live
                     here too: `maskedPan` flags an attached card and the
                     balance/availableBalance pair answers "can I use it?"
      - `Savings`  - interest-bearing savings (ISO 20022 SVGS)
      - `Credit`   - revolving credit / credit card account; carries the
                     statement-cycle fields below (`statementBalance`,
                     `minimumPaymentDue`, `paymentDueDate`, ...).
      - `Loan`     - amortizing loan or mortgage (ISO 20022 LOAN)
      - `Other`    - anything else (escrow, brokerage, etc.)
    """

    Current = "Current"
    Credit = "Credit"
    Savings = "Savings"
    Loan = "Loan"
    Other = "Other"


class AccountStatus(str, Enum):
    """Lifecycle status of an account, per Berlin Group PSD2 `accountStatus`."""

    Enabled = "Enabled"
    Blocked = "Blocked"
    Deleted = "Deleted"


class AccountUsage(str, Enum):
    """How the account is used, per Berlin Group PSD2 `usage`.

    `Private` corresponds to PSD2 `PRIV` (personal); `Business` to `ORGA`
    (professional / organisation).
    """

    Private = "Private"
    Business = "Business"


class Account(_Bank2aiModel):
    """Bank account with balance and metadata.

    Property names follow Berlin Group PSD2 `accountDetails` where they
    overlap (`iban`, `bban`, `bic`, `maskedPan`, `product`, `status`,
    `usage`), so servers fronting a PSD2 backend can map fields directly.
    Servers SHOULD populate at least one of `accountNumber`, `iban`,
    `bban`, or `maskedPan`.
    """

    id: str = Field(description="Unique account identifier (server-scoped)")
    name: Optional[str] = Field(
        default=None,
        description="Human-readable account name set by the bank or the user.",
        examples=["Main Checking", "Emergency Fund", "Visa Credit Card"],
    )
    accountNumber: str = Field(
        description=(
            "Display-friendly account number in the locally familiar format. "
            "For European accounts this is typically the IBAN; otherwise the "
            "domestic account number. Use the typed identifier fields (`iban`, "
            "`bban`, `maskedPan`) when you need to parse or route on it."
        ),
        examples=["1234-56-789012", "GB29NWBK60161331926819", "0133-26-007890"],
    )
    iban: Optional[str] = Field(
        default=None,
        description="IBAN (ISO 13616), when the account has one.",
        pattern=r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}$",
        examples=["GB29NWBK60161331926819", "DE89370400440532013000"],
    )
    bban: Optional[str] = Field(
        default=None,
        description=(
            "Basic Bank Account Number, the domestic identifier used in "
            "countries (or for products) without an IBAN."
        ),
        examples=["BARC12345612345678", "0133-26-007890"],
    )
    bic: Optional[str] = Field(
        default=None,
        description="BIC / SWIFT code of the holding bank (ISO 9362).",
        pattern=r"^[A-Z]{6}[A-Z2-9][A-NP-Z0-9]([A-Z0-9]{3})?$",
        examples=["NWBKGB2L", "DEUTDEFF"],
    )
    maskedPan: Optional[str] = Field(
        default=None,
        description=(
            "Masked Primary Account Number for card accounts. The middle "
            "digits MUST be obscured."
        ),
        examples=["411111xxxxxx1111", "****-****-****-1234"],
    )
    currency: str = Field(
        description=(
            "ISO 4217 currency code of the account. For multi-currency "
            "accounts (per PSD2 convention) use `XXX`."
        ),
        pattern="^[A-Z]{3}$",
        examples=["USD", "EUR", "ISK", "GBP", "XXX"],
    )
    balance: float = Field(
        description=(
            "Current booked balance in `currency`. For credit accounts a "
            "negative value indicates an outstanding balance owed."
        ),
    )
    availableBalance: Optional[float] = Field(
        default=None,
        description=(
            "Funds available to spend right now in `currency`, after pending "
            "authorisations and including any `overdraftLimit` headroom. "
            "Aligns with the PSD2 `interimAvailable` balance type."
        ),
    )
    overdraftLimit: Optional[float] = Field(
        default=None,
        description=(
            "Approved overdraft on a current/savings account or credit limit "
            "on a credit/card account, in `currency`. `0` (or omitted) means "
            "no extra headroom beyond `balance`."
        ),
        ge=0,
    )
    ownerName: Optional[str] = Field(
        default=None,
        description=(
            "Primary account holder's name as the bank holds it. For joint "
            "accounts, servers MAY join multiple names with `, `."
        ),
        examples=["Jane Doe", "Jane Doe & John Doe", "Acme Corp"],
    )
    product: Optional[str] = Field(
        default=None,
        description=(
            "Bank's marketing name for the account product, per PSD2 `product`. "
            "Free-form and proprietary to the issuer."
        ),
        examples=["Premium Checking", "Visa Signature", "Easy Saver"],
    )
    status: Optional[AccountStatus] = Field(
        default=None,
        description=(
            "Lifecycle status. If omitted, clients SHOULD treat the account "
            "as `Enabled`."
        ),
    )
    usage: Optional[AccountUsage] = Field(
        default=None,
        description="Whether this is a personal or business account.",
    )
    accountType: Optional[AccountType] = Field(
        default=None,
        description="Type of account.",
    )
    isWithdrawalAccount: Optional[bool] = Field(
        default=None,
        description=(
            "Whether this account can be used as the source of an outgoing "
            "transfer or withdrawal."
        ),
    )
    isDefaultAccount: Optional[bool] = Field(
        default=None,
        description=(
            "Whether this is the user's default account for new transfers. "
            "At most one account per response SHOULD have this set to true."
        ),
    )
    openedDate: Optional[date] = Field(
        default=None,
        description="Date the account was opened, ISO 8601 (YYYY-MM-DD).",
    )
    balanceUpdatedAt: Optional[datetime] = Field(
        default=None,
        description=(
            "ISO 8601 timestamp at which `balance` and `availableBalance` "
            "were last refreshed by the bank."
        ),
    )
    statementBalance: Optional[float] = Field(
        default=None,
        description=(
            "Credit accounts only. Total billed on the most recent closed "
            "statement, in `currency`. Pay this in full by `paymentDueDate` "
            "to avoid interest charges. Servers MUST omit on non-credit "
            "accounts."
        ),
    )
    minimumPaymentDue: Optional[float] = Field(
        default=None,
        description=(
            "Credit accounts only. Minimum payment required by "
            "`paymentDueDate` to keep the account current and avoid late "
            "fees, in `currency`. Servers MUST omit on non-credit accounts."
        ),
    )
    paymentDueDate: Optional[date] = Field(
        default=None,
        description=(
            "Credit accounts only. ISO 8601 date by which "
            "`minimumPaymentDue` must be paid. Servers MUST omit on "
            "non-credit accounts."
        ),
    )
    statementClosingDate: Optional[date] = Field(
        default=None,
        description=(
            "Credit accounts only. ISO 8601 date the current billing cycle "
            "closes and the next statement is generated. Optional even on "
            "credit accounts; servers MUST omit on non-credit accounts."
        ),
    )


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

    Profile of: ISO 20022 `EntryDetails2` and Berlin Group PSD2
    `transactions` array element.
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
    bookingDate: date = Field(
        description="Date the transaction posted to the account, ISO 8601 (YYYY-MM-DD).",
    )
    status: Optional[TransactionStatus] = Field(
        default=None,
        description=(
            "Booking status. If omitted, clients SHOULD treat the transaction "
            "as `Booked`."
        ),
    )
    counterpartyName: Optional[str] = Field(
        default=None,
        description=(
            "Best-effort merchant or counterparty display name. Distinct from "
            "`description`, which is the bank's narrative as presented to the user."
        ),
    )
    categoryId: Optional[str] = Field(
        default=None,
        description="Category id (the `id` field from get-categories which also has category name).",
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
    valueDate: Optional[date] = Field(
        default=None,
        description=(
            "Date the funds become available, ISO 8601. Servers SHOULD omit "
            "when equal to `bookingDate`. Profile of: ISO 20022 `ValueDate`."
        ),
    )
    categoryRaw: Optional[str] = Field(
        default=None,
        description=(
            "Bank-native category label as the upstream system exposes it. "
            "Useful when `categoryId` is mapped from something more specific."
        ),
    )
    counterparty: Optional[Party] = Field(
        default=None,
        description=(
            "Typed counterparty record. Servers SHOULD populate when more "
            "than just `counterpartyName` is known (account identifier, BIC, "
            "national id)."
        ),
    )
    transactionCode: Optional[TransactionCode] = Field(
        default=None,
        description="ISO 20022 BankTransactionCode classification of the entry.",
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
    merchantCategoryCode: Optional[str] = Field(
        default=None,
        description="ISO 18245 Merchant Category Code (4 digits).",
        pattern=r"^\d{4}$",
        examples=["5411", "5812"],
    )


class Category(_Bank2aiModel):
    """Transaction category for spending classification"""

    id: str = Field(description="Unique category identifier")
    name: str = Field(
        description="Category name (localized)",
        examples=["Groceries", "Transportation", "Entertainment", "Utilities"],
    )


class AccountList(BaseModel):
    """Envelope for a list of accounts"""

    items: list[Account] = Field(description="Accounts matching the request.")


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


class CategoryList(BaseModel):
    """Envelope for a list of categories"""

    items: list[Category] = Field(description="Available transaction categories.")


class RecipientList(BaseModel):
    """Envelope for a list of recipients"""

    items: list[Recipient] = Field(description="Recipients matching the request.")


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


class CreateRecipientResponse(BaseModel):
    """Result of creating a payment recipient"""

    content: str = Field(description="Human-readable status message")
    item: Optional[Recipient] = Field(
        default=None,
        description="The created recipient when creation succeeded.",
    )


class TransferAction(BaseModel):
    """Suggested follow-up action for a prepared transfer."""

    title: str = Field(description="Human-readable label for the action.")
    link: str = Field(description="Target URL or in-app link to perform the action.")


class TransferPreparedItem(BaseModel):
    """Validated transfer details awaiting user confirmation."""

    amount: float = Field(description="Transfer amount in `currency`.", gt=0)
    description: str = Field(
        description="Free-text note shown on the recipient's statement.",
    )
    currency: str = Field(
        description="ISO 4217 currency code.",
        pattern="^[A-Z]{3}$",
        examples=["ISK", "EUR", "USD"],
    )
    recipient_account_number: str = Field(
        description="Destination bank account number.",
    )
    recipient_ssn: str = Field(
        description="Recipient's national ID / SSN.",
    )
    recipient_name: str = Field(description="Recipient's full name or business name.")
    withdrawal_account_id: str = Field(
        description="Source account.id (from get-accounts).",
    )
    withdrawal_account: Account = Field(
        description="Resolved source account snapshot used for the transfer.",
    )


class TransferPreparedResponse(BaseModel):
    """Prepared transfer details awaiting confirmation"""

    content: str = Field(description="Human-readable status message")
    item: Optional[TransferPreparedItem] = Field(
        default=None,
        description="Prepared transfer details when validation succeeded.",
    )
    actions: list[TransferAction] = Field(
        default_factory=list,
        description="Optional follow-up actions the client may surface.",
    )


class ExecuteTransferDetail(BaseModel):
    """Bank-issued receipt for an executed transfer."""

    transfer_id: str = Field(description="Bank-issued transfer identifier.")
    status: str = Field(
        description="Execution status reported by the bank.",
        examples=["Completed", "Pending", "Rejected"],
    )
    timestamp: str = Field(
        description="ISO 8601 timestamp when the bank recorded the transfer.",
    )


class ExecuteTransferResponse(BaseModel):
    """Result of executing a transfer"""

    content: str = Field(description="Human-readable status message")
    item: Optional[ExecuteTransferDetail] = Field(
        default=None,
        description="Receipt details when the transfer was accepted by the bank.",
    )


