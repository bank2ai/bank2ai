"""Saved payment recipients and the recipient-management envelopes."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .base import _Bank2aiModel
from .identity import AccountIdentifier, NationalId


class Recipient(_Bank2aiModel):
    """Saved payment recipient.

    Profile of: ISO 20022 `Creditor` and `CreditorAccount` (subset).
    Account routing goes through the typed `accountIdentifier`
    discriminated union (IBAN, BBAN, country-specific account number,
    or alias); national identification is opaque to bank2ai and lives
    in the typed `nationalId` sub-object.
    """

    id: str = Field(description="Unique recipient identifier (server-scoped).")
    name: str = Field(
        description="Recipient's full name or business name.",
        examples=["Jane Doe", "Acme Corp"],
    )
    accountIdentifier: AccountIdentifier = Field(
        description="Typed account identifier for routing the transfer.",
    )
    nickname: Optional[str] = Field(
        default=None,
        description="Optional user-friendly handle for the recipient.",
        examples=["Mom", "Landlord"],
    )
    nationalId: Optional[NationalId] = Field(
        default=None,
        description="Recipient's national identifier when known.",
    )
    bic: Optional[str] = Field(
        default=None,
        description="BIC / SWIFT code of the recipient's bank, ISO 9362.",
        pattern=r"^[A-Z]{6}[A-Z2-9][A-NP-Z0-9]([A-Z0-9]{3})?$",
        examples=["NWBKGB2L"],
    )
    defaultDescription: Optional[str] = Field(
        default=None,
        description=(
            "Pre-filled free-text shown on the recipient's statement "
            "for transfers prepared against this recipient. Clients MAY "
            "use this as the default `description` when preparing a "
            "transfer; users can override per transfer."
        ),
    )
    lastUsedAt: Optional[datetime] = Field(
        default=None,
        description="ISO 8601 timestamp of the most recent transfer to this recipient.",
    )
    isFavorite: bool = Field(
        default=False,
        description="Whether this recipient is marked as favorite.",
    )


class RecipientList(BaseModel):
    """Envelope for a list of recipients"""

    items: list[Recipient] = Field(description="Recipients matching the request.")


class CreateRecipientResponse(BaseModel):
    """Result of creating a payment recipient"""

    content: str = Field(description="Human-readable status message")
    item: Optional[Recipient] = Field(
        default=None,
        description="The created recipient when creation succeeded.",
    )
    code: Optional[str] = Field(
        default=None,
        description=(
            "Server-defined code identifying a recoverable error (e.g., "
            "`duplicate_recipient`). Omitted on success."
        ),
    )
