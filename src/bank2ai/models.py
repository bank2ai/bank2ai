"""Data models for bank integrations."""

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AuthParamType(str, Enum):
    """Type of authentication parameter input."""

    Text = "text"
    Password = "password"


class AuthParam(BaseModel):
    """Authentication parameter definition."""

    id: str = Field(description="Identifier for this credential field")
    title: str = Field(description="Human-readable label shown to the user")
    type: AuthParamType = Field(
        default=AuthParamType.Text,
        description="Input type — controls how the client renders the field",
    )


class AuthParamValue(BaseModel):
    """Authentication parameter value from user."""

    id: str = Field(description="Identifier matching an AuthParam.id")
    value: str = Field(description="User-supplied value for the parameter")


class AuthResponse(BaseModel):
    """Response from authentication endpoint."""

    authenticated: bool = Field(
        default=False,
        description="Whether authentication has succeeded",
    )
    message: Optional[str] = Field(
        default=None,
        description="Status or error message to surface to the user",
    )
    required_parameters: list[AuthParam] = Field(
        default_factory=list,
        description="Credential fields the adapter needs to authenticate",
    )
    session_parameters: list[AuthParamValue] = Field(
        default_factory=list,
        description="Session parameters returned by the adapter for subsequent calls",
    )
    token: Optional[str] = Field(
        default=None,
        description="Authentication token issued by the adapter, if any",
    )
    culture: Optional[str] = Field(
        default=None,
        description="Locale/culture string returned by the adapter",
    )


class RecipientInfo(BaseModel):
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
    """Type of bank account."""

    Current = "Current"
    Credit = "Credit"
    Savings = "Savings"


class Account(BaseModel):
    """Bank account with balance and metadata"""

    id: str = Field(description="Unique account identifier")
    name: Optional[str] = Field(
        default=None,
        description="Human-readable account name",
        examples=["Main Checking", "Savings Account", "Credit Card"],
    )
    accountNumber: str = Field(
        description="Formatted account number (format varies by country)",
        examples=["1234-56-789012", "GB29NWBK60161331926819"],
    )
    currency: str = Field(
        description="ISO 4217 currency code",
        pattern="^[A-Z]{3}$",
        examples=["USD", "EUR", "ISK", "GBP"],
    )
    balance: float = Field(description="Current account balance")
    availableBalance: Optional[float] = Field(
        default=None,
        description="Available balance (after pending transactions)",
    )
    overdraftLimit: Optional[float] = Field(
        default=None,
        description="Overdraft/credit limit (0 if none)",
        ge=0,
    )
    isWithdrawalAccount: Optional[bool] = Field(
        default=None,
        description="Whether this account can be used for withdrawals/transfers",
    )
    isDefaultAccount: Optional[bool] = Field(
        default=None,
        description="Whether this is the user's default account",
    )
    accountType: Optional[AccountType] = Field(
        default=None,
        description="Type of account",
    )


class Transaction(BaseModel):
    """Financial transaction with date, amount and metadata"""
    id: Optional[str] = Field(default=None,
        description="Unique transaction identifier")
    description: str = Field(
        description="Transaction description, merchant name or recipient name",
    )
    amount: float = Field(
        description="Transaction amount (negative for expenses, positive for income)",
    )
    transaction_date: date = Field(
        description="Transaction date in ISO 8601 format (YYYY-MM-DD)"
    )
    category: Optional[str] = Field(default=None,
        description="Category name")


class Category(BaseModel):
    """Transaction category for spending classification"""

    id: str = Field(description="Unique category identifier")
    name: str = Field(
        description="Category name (localized)",
        examples=["Groceries", "Transportation", "Entertainment", "Utilities"],
    )


class TransactionType(str, Enum):
    """Filter type for transactions."""

    Any = "Any"
    Income = "Income"
    Expenses = "Expenses"
    Savings = "Savings"


class TransactionOrder(str, Enum):
    """Sort order for transactions."""

    NewestFirst = "NewestFirst"
    OldestFirst = "OldestFirst"


class SpendingSummaryGroup(BaseModel):
    """One row of an aggregated spending summary."""

    group: str = Field(
        description="Aggregation key value (category name, group, month, or merchant).",
    )
    total_amount: float = Field(description="Sum of transaction amounts in this group.")
    transaction_count: int = Field(
        description="Number of transactions contributing to this group.",
        ge=0,
    )
    average_amount: float = Field(
        description="Mean transaction amount within this group.",
    )


class SpendingSummaryPeriod(BaseModel):
    """Inclusive date range covered by a spending summary."""

    start_date: str = Field(
        description="Inclusive lower bound, ISO 8601 (YYYY-MM-DD).",
        examples=["2024-03-01"],
    )
    end_date: str = Field(
        description="Inclusive upper bound, ISO 8601 (YYYY-MM-DD).",
        examples=["2024-03-31"],
    )


class SpendingSummary(BaseModel):
    """Aggregated spending summary"""

    summary: list[SpendingSummaryGroup] = Field(
        description="One entry per aggregation key value.",
    )
    period: SpendingSummaryPeriod = Field(
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


class AuthenticateResponse(BaseModel):
    """Authentication result"""

    message: Optional[str] = Field(
        default=None,
        description="Success message to surface to the user.",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message when authentication failed.",
    )


