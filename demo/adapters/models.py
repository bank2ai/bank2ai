"""Data models for bank integrations."""

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class AuthParamType(str, Enum):
    """Type of authentication parameter input."""

    Text = "text"
    Password = "password"


class AuthParam(BaseModel):
    """Authentication parameter definition."""

    id: str
    title: str
    type: AuthParamType = AuthParamType.Text


class AuthParamValue(BaseModel):
    """Authentication parameter value from user."""

    id: str
    value: str


class AuthReponse(BaseModel):
    """Response from authentication endpoint."""
    authenticated: bool = False
    message: Optional[str] = None
    required_parameters: list[AuthParam] = []
    session_parameters: list[AuthParamValue] = []
    token: Optional[str] = None
    culture: Optional[str] = None

class ReceipientInfo(BaseModel):
    """Basic recipient information for transfers."""

    name: str
    socialSecurityNumber: str
    accountNumber: str


class Receipient(ReceipientInfo):
    """Payment recipient with full details."""

    id: Optional[str] = None
    name: str
    accountNumber: str
    accountNumberType: Optional[str] = None
    bankInfo: Optional[str] = None
    paymentType: Optional[str] = None
    socialSecurityNumber: str
    address: Optional[str] = None
    isFavorite: bool = False
    description: Optional[str] = None


class AccountType(str, Enum):
    """Type of bank account."""

    Current = "Current"
    Credit = "Credit"
    Savings = "Savings"


class Account(BaseModel):
    """Bank account details."""

    id: str
    name: Optional[str] = None
    accountNumber: str
    currency: str
    balance: float
    availableBalance: Optional[float] = None
    overdraftLimit: Optional[float] = None
    isWithdrawalAccount: Optional[bool] = None
    isDefaultAccount: Optional[bool] = None
    accountType: Optional[AccountType] = None


class Transaction(BaseModel):
    """Bank transaction."""

    id: Optional[str] = None
    description: str
    amount: float
    transaction_date: date
    category: Optional[str] = None


class Category(BaseModel):
    """Transaction category."""

    id: str
    name: str


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


def custom_json_encoder(obj):
    """Custom JSON encoder for date objects."""
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} is not JSON serializable")
