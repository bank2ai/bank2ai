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


class PostalAddress(_Bank2aiModel):
    """Postal address of a party or card-acceptor merchant.

    Profile of: ISO 20022 `PostalAddress24` (subset). Aligns with the
    Open Finance / Berlin Group `cardAcceptorAddress` structure so card
    transactions can surface where the swipe happened. Servers SHOULD
    populate whichever subfields the bank exposes and omit the rest;
    `townName` and `country` are the most commonly available and the
    most useful for LLM context.
    """

    streetName: Optional[str] = Field(
        default=None,
        description="Street name without the building number.",
        examples=["Rue de Rivoli"],
    )
    buildingNumber: Optional[str] = Field(
        default=None,
        description="Building number on the street.",
        examples=["12", "12B"],
    )
    postCode: Optional[str] = Field(
        default=None,
        description="Postal / ZIP code.",
        examples=["75001", "SW1A 1AA"],
    )
    townName: Optional[str] = Field(
        default=None,
        description="City, town, or village name.",
        examples=["Paris", "Stockholm", "Reykjavík"],
    )
    countrySubDivision: Optional[str] = Field(
        default=None,
        description="State, province, region, or other top-level subdivision.",
        examples=["CA", "Île-de-France"],
    )
    country: Optional[str] = Field(
        default=None,
        description="ISO 3166-1 alpha-2 country code.",
        pattern=r"^[A-Z]{2}$",
        examples=["FR", "SE", "IS", "US"],
    )
    addressLine: Optional[list[str]] = Field(
        default=None,
        description=(
            "Free-form address lines, used when the bank exposes the "
            "address as unparsed text. Servers SHOULD prefer the typed "
            "fields above and fall back to `addressLine` only when "
            "they cannot decompose the address."
        ),
    )


class Party(_Bank2aiModel):
    """Counterparty in a transaction or transfer.

    Profile of: ISO 20022 `PartyIdentification135` (subset). For card
    transactions the counterparty is the card-accepting merchant;
    `postalAddress` then carries the Open Finance `cardAcceptorAddress`.
    """

    name: str = Field(description="Party's full name or business name.")
    brandName: Optional[str] = Field(
        default=None,
        description=(
            "Brand or chain name the party belongs to, when `name` is a "
            "specific outlet of a larger brand. For card transactions "
            "this is the merchant's parent brand (e.g. `name` = "
            '"Starbucks Reserve Roastery", `brandName` = "Starbucks"). '
            "Clients MAY use `brandName` to group transactions by chain "
            "while still displaying the specific outlet on each row."
        ),
        examples=["Starbucks", "Bónus"],
    )
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
    postalAddress: Optional[PostalAddress] = Field(
        default=None,
        description=(
            "Postal address of the party. For card transactions, this "
            "is the merchant / card-acceptor address (Open Finance "
            "`cardAcceptorAddress`). Servers SHOULD populate whatever "
            "subset they have, typically at least `townName` and "
            "`country`."
        ),
    )
    latitude: Optional[float] = Field(
        default=None,
        description=(
            "Geographic latitude of the party's location in decimal "
            "degrees (WGS 84). For card transactions, this is the "
            "merchant / card-acceptor location. Profile of: Berlin "
            "Group `geoLocation` (latitude component)."
        ),
        ge=-90,
        le=90,
        examples=[48.8566, 64.1466],
    )
    longitude: Optional[float] = Field(
        default=None,
        description=(
            "Geographic longitude of the party's location in decimal "
            "degrees (WGS 84). For card transactions, this is the "
            "merchant / card-acceptor location. Profile of: Berlin "
            "Group `geoLocation` (longitude component)."
        ),
        ge=-180,
        le=180,
        examples=[2.3522, -21.9426],
    )
