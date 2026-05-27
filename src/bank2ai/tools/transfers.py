"""Registrations for the transfer tools (`prepare-transfer`, `execute-transfer`)."""

from __future__ import annotations

from typing import Optional

from fastmcp import FastMCP
from pydantic import Field

from ..models import (
    ExecuteTransferResponse,
    Party,
    PrepareTransferResponse,
    Rail,
    RemittanceInformation,
)
from .base import Handler, OutputSchemaMode, build_decorator_helpers


def register_prepare_transfer(
    app: FastMCP,
    handler: Handler,
    *,
    output_schemas: OutputSchemaMode,
) -> str:
    out_kwarg, desc = build_decorator_helpers(output_schemas)

    @app.tool(
        name="prepare-transfer",
        description=desc(
            "Prepare a money transfer on any supported rail (SEPA, "
            "SEPA Instant, SWIFT, domestic-IS, etc.). Validates the "
            "creditor, computes fees / FX / payee verification when "
            "applicable, and returns a transferIntentId plus a "
            "summary the user confirms. Does NOT execute; pass the "
            "intent id to `execute-transfer`."
        ),
        **out_kwarg,
    )
    async def _prepare_transfer(
        debtor_account_id: str = Field(
            description="Source `Account.id` from `get-accounts`.",
        ),
        creditor: Party = Field(
            description=(
                "Creditor record. `accountIdentifier` is required "
                "for routing; `name` is required for display and "
                "Confirmation-of-Payee on rails that support it."
            ),
        ),
        amount: float = Field(
            description="Instructed amount in `currency`.",
            gt=0,
        ),
        currency: str = Field(
            description="ISO 4217 currency code of the instructed amount.",
            pattern=r"^[A-Z]{3}$",
            examples=["ISK", "EUR", "USD"],
        ),
        rail: Rail = Field(
            description=(
                "Settlement rail. Drives validation, fees, and the "
                "set of meaningful `local_instrument` values."
            ),
        ),
        local_instrument: Optional[str] = Field(
            default=None,
            description=(
                "Rail-specific instrument code; `INST` for SEPA "
                "Instant, `RTGS` for SWIFT, etc. Free-form per rail."
            ),
        ),
        requested_execution_date: Optional[str] = Field(
            default=None,
            description=(
                "ISO 8601 (YYYY-MM-DD) requested execution date. "
                "Omit for as-soon-as-possible per the rail."
            ),
            pattern=r"^\d{4}-\d{2}-\d{2}$",
        ),
        remittance_information: Optional[RemittanceInformation] = Field(
            default=None,
            description=(
                "Structured / unstructured remittance information "
                "to attach to the transfer."
            ),
        ),
        end_to_end_id: Optional[str] = Field(
            default=None,
            description=(
                "Optional client-supplied ISO 20022 cross-rail "
                "identifier. Servers MUST generate one when the "
                "client omits it; the resolved value is echoed in "
                "the response summary."
            ),
        ),
        description: Optional[str] = Field(
            default=None,
            description=(
                "Free-text shown on the counterparty's statement. "
                "Falls back to `remittance_information.unstructured` "
                "when both are set."
            ),
        ),
        idempotency_key: Optional[str] = Field(
            default=None,
            description=(
                "Optional idempotency key, scoped to this tool. "
                "Servers SHOULD return the original prepared-transfer "
                "response for repeat calls with the same key within "
                "at least 24 hours."
            ),
            max_length=128,
        ),
    ) -> PrepareTransferResponse:
        return await handler(
            debtor_account_id=debtor_account_id,
            creditor=creditor,
            amount=amount,
            currency=currency,
            rail=rail,
            local_instrument=local_instrument,
            requested_execution_date=requested_execution_date,
            remittance_information=remittance_information,
            end_to_end_id=end_to_end_id,
            description=description,
            idempotency_key=idempotency_key,
        )

    return "prepare-transfer"


def register_execute_transfer(
    app: FastMCP,
    handler: Handler,
    *,
    output_schemas: OutputSchemaMode,
) -> str:
    out_kwarg, desc = build_decorator_helpers(output_schemas)

    @app.tool(
        name="execute-transfer",
        description=desc(
            "Execute a transfer the user has confirmed. Takes only "
            "the `transfer_intent_id` returned by `prepare-transfer`. "
            "The intent's amount, creditor, debtor, and rail are "
            "immutable: any change requires a new prepare call. "
            "Servers reject expired intents with a structured error."
        ),
        **out_kwarg,
    )
    async def _execute_transfer(
        transfer_intent_id: str = Field(
            description=(
                "Intent token from a recent `prepare-transfer` call."
            ),
        ),
        idempotency_key: Optional[str] = Field(
            default=None,
            description=(
                "Optional idempotency key. Servers SHOULD return the "
                "original response for repeat calls with the same key."
            ),
            max_length=128,
        ),
    ) -> ExecuteTransferResponse:
        return await handler(
            transfer_intent_id=transfer_intent_id,
            idempotency_key=idempotency_key,
        )

    return "execute-transfer"
