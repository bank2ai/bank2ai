"""Registration for the `get-accounts` tool."""

from __future__ import annotations

from typing import Literal, Optional

from fastmcp import FastMCP
from pydantic import Field

from ..models import AccountList
from .base import Handler, OutputSchemaMode, build_decorator_helpers


def register_get_accounts(
    app: FastMCP,
    handler: Handler,
    *,
    output_schemas: OutputSchemaMode,
) -> str:
    out_kwarg, desc = build_decorator_helpers(output_schemas)

    @app.tool(
        name="get-accounts",
        description=desc(
            "Get the user's bank accounts and cards. Returns each account "
            "with balances, identifiers (account number, plus IBAN/BBAN/BIC "
            "or masked PAN where the bank has them), holder, product, type, "
            "lifecycle status, and usage. Field shapes follow the Berlin "
            "Group PSD2 `accountDetails` model where they overlap."
        ),
        **out_kwarg,
    )
    async def _get_accounts(
        only_withdrawal_accounts: bool = Field(
            default=False,
            description=(
                "If true, return only accounts usable as the source of "
                "an outgoing transfer or withdrawal."
            ),
        ),
        account_type: Optional[
            Literal["Current", "Savings", "Credit", "Loan", "Other"]
        ] = Field(
            default=None,
            description=(
                "Filter by account type. `Current` and `Savings` are the "
                "common spending and deposit accounts; `Credit` covers "
                "revolving credit / credit cards; `Loan` covers mortgages "
                "and amortizing loans. Debit and prepaid cards live under "
                "`Current`; their `maskedPan` field flags the attached card."
            ),
        ),
        status: Optional[Literal["Enabled", "Blocked", "Deleted"]] = Field(
            default=None,
            description=(
                "Filter by lifecycle status. Defaults to all statuses; "
                "pass `Enabled` to hide closed or blocked accounts."
            ),
        ),
        usage: Optional[Literal["Private", "Business"]] = Field(
            default=None,
            description=(
                "Filter by usage: personal (`Private`) or business "
                "(`Business`). Servers MAY ignore this if they do not "
                "track usage."
            ),
        ),
    ) -> AccountList:
        return await handler(
            only_withdrawal_accounts=only_withdrawal_accounts,
            account_type=account_type,
            status=status,
            usage=usage,
        )

    return "get-accounts"
