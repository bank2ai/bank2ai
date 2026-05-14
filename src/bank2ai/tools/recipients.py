"""Registrations for the recipient-management tools."""

from __future__ import annotations

from typing import Optional

from fastmcp import FastMCP
from pydantic import Field

from ..models import (
    AccountIdentifier,
    CreateRecipientResponse,
    NationalId,
    RecipientList,
)
from .base import Handler, OutputSchemaMode, build_decorator_helpers


def register_get_recipients(
    app: FastMCP,
    handler: Handler,
    *,
    output_schemas: OutputSchemaMode,
) -> str:
    out_kwarg, desc = build_decorator_helpers(output_schemas)

    @app.tool(
        name="get-recipients",
        description=desc(
            "Get saved payment recipients filtered by name. "
            "Returns matching recipients with their account details."
        ),
        **out_kwarg,
    )
    async def _get_recipients(
        name: str = Field(
            description="Free-text search; matches partial names of saved recipients.",
        ),
    ) -> RecipientList:
        return await handler(name=name)

    return "get-recipients"


def register_create_recipient(
    app: FastMCP,
    handler: Handler,
    *,
    output_schemas: OutputSchemaMode,
) -> str:
    out_kwarg, desc = build_decorator_helpers(output_schemas)

    @app.tool(
        name="create-recipient",
        description=desc(
            "Create a new payment recipient. Account routing goes "
            "through the typed `account_identifier` discriminated "
            "union (IBAN, BBAN with country, country-specific account "
            "number, or alias). National identification, when known, "
            "uses the typed `national_id` sub-object. The recipient "
            "can then be used for transfers."
        ),
        **out_kwarg,
    )
    async def _create_recipient(
        name: str = Field(description="Recipient's full name or business name."),
        account_identifier: AccountIdentifier = Field(
            description=(
                "Typed account identifier. One of: "
                "`{type: 'iban', iban}`, "
                "`{type: 'bban', bban, country}`, "
                "`{type: 'accountNumber', accountNumber, country, routing?, sortCode?}`, "
                "`{type: 'alias', alias, aliasType}`."
            ),
        ),
        national_id: Optional[NationalId] = Field(
            default=None,
            description=(
                "Recipient's national identifier when known. Shape: "
                "`{value, country, type?}` where `type` is an opaque "
                "label (`kennitala`, `ssn`, `cpr`, `personnummer`, "
                "`cpf`, `other`). bank2ai does not validate the value."
            ),
        ),
        nickname: Optional[str] = Field(
            default=None,
            description="Optional user-friendly handle (e.g., 'Mom').",
        ),
        bic: Optional[str] = Field(
            default=None,
            description="BIC / SWIFT code of the recipient's bank, ISO 9362.",
            pattern=r"^[A-Z]{6}[A-Z2-9][A-NP-Z0-9]([A-Z0-9]{3})?$",
        ),
        default_description: Optional[str] = Field(
            default=None,
            description="Pre-fill text for transfers' description field.",
        ),
        idempotency_key: Optional[str] = Field(
            default=None,
            description=(
                "Optional idempotency key, scoped to this tool. "
                "Servers SHOULD return the original response for "
                "repeat calls with the same key within at least 24 "
                "hours."
            ),
            max_length=128,
        ),
    ) -> CreateRecipientResponse:
        return await handler(
            name=name,
            account_identifier=account_identifier,
            national_id=national_id,
            nickname=nickname,
            bic=bic,
            default_description=default_description,
            idempotency_key=idempotency_key,
        )

    return "create-recipient"
