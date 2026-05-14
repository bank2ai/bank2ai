"""Shared identity primitives.

`AccountIdentifier` and `Party` are used by transaction counterparties,
transfer creditor details, and `Recipient`.
"""

from enum import Enum
from typing import Annotated, Literal, Optional, Union

from pydantic import Field

from .base import _Bank2aiModel


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
