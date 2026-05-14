"""Account, balances, and the get-accounts envelope."""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .base import _Bank2aiModel


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


class BalanceType(str, Enum):
    """Type of balance per Berlin Group PSD2 `balanceType`."""

    ClosingBooked = "ClosingBooked"
    Expected = "Expected"
    InterimAvailable = "InterimAvailable"
    ForwardAvailable = "ForwardAvailable"
    NonInvoiced = "NonInvoiced"


class Balance(_Bank2aiModel):
    """One typed balance entry on an account.

    Profile of: Berlin Group PSD2 `balances` array element.
    """

    type: BalanceType = Field(description="Balance type.")
    amount: float = Field(description="Balance amount in `currency`.")
    currency: str = Field(
        description="ISO 4217 currency code.",
        pattern="^[A-Z]{3}$",
    )
    asOf: Optional[datetime] = Field(
        default=None,
        description="ISO 8601 timestamp when this balance was last refreshed.",
    )


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
    balances: Optional[list[Balance]] = Field(
        default=None,
        description=(
            "Typed balance entries when the bank exposes more than just "
            "the booked and available scalars (`ClosingBooked`, "
            "`Expected`, `InterimAvailable`, `ForwardAvailable`, "
            "`NonInvoiced`). When populated, the top-level `balance` and "
            "`availableBalance` scalars are derived shortcuts for the "
            "most-recent `ClosingBooked` and `InterimAvailable` entries; "
            "servers MUST keep them consistent. Servers without typed "
            "balance support SHOULD omit this field and emit only the "
            "scalars."
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


class AccountList(BaseModel):
    """Envelope for a list of accounts"""

    items: list[Account] = Field(description="Accounts matching the request.")
