"""Reusable Bank2AI MCP tool specification.

This module isolates the Bank2AI tool spec — names, descriptions, input
parameter signatures, and Pydantic response models — so multiple MCP
servers can expose the same surface without duplicating it. Each server
provides async handler callables and calls `register_tools(app, ...)`.

Output schemas are inferred by FastMCP from the Pydantic response-model
annotations on the registered tool functions.

"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Literal, Optional

from fastmcp import FastMCP
from pydantic import Field

from .models import (
    Account,
    Category,
    CreateRecipientResponse,
    ExecuteTransferResponse,
    Recipient,
    SpendingSummary,
    Transaction,
    TransferPreparedResponse,
)


# ---- Handler protocol ----
# Handlers are async callables receiving the input-schema's keyword args
# and returning JSON-serializable data shaped like the response model.

Handler = Callable[..., Awaitable[Any]]


# ---- Tool registration ----


def register_tools(
    app: FastMCP,
    *,
    get_accounts: Handler,
    get_transactions: Handler,
    get_categories: Handler,
    get_spending_summary: Handler,
    search_recipients: Handler,
    create_recipient: Handler,
    prepare_transfer: Handler,
    execute_transfer: Handler,
) -> None:
    """Register all Bank2AI MCP tools on `app`, dispatching to handlers.

    Each handler is invoked with keyword arguments matching the tool's
    input schema (using the snake_case names declared below). Handlers
    may return either dicts shaped like the response model or model
    instances directly — FastMCP serializes both via Pydantic.
    """

    @app.tool(
        name="get-accounts",
        description=(
            "Get bank accounts and cards. Returns a list of accounts "
            "with balances, account numbers, and types."
        ),
    )
    async def _get_accounts(
        only_withdrawal_accounts: bool = Field(
            default=False,
            description="If true, return only accounts usable for withdrawals/transfers.",
        ),
        account_type: Optional[Literal["Current", "Savings", "Credit"]] = Field(
            default=None,
            description="Filter by account type.",
        ),
    ) -> list[Account]:
        return await get_accounts(
            only_withdrawal_accounts=only_withdrawal_accounts,
            account_type=account_type,
        )

    @app.tool(
        name="transactions",
        description=(
            "Get bank transactions. Returns a list of transactions "
            "with amounts, dates, descriptions, and categories."
        ),
    )
    async def _transactions(
        count: Optional[int] = Field(
            default=None,
            description="Maximum number of transactions to return.",
            ge=1,
        ),
        type: Literal["Any", "Income", "Expenses", "Savings"] = Field(
            default="Any",
            description="Filter by direction.",
        ),
        order: Literal["NewestFirst", "OldestFirst"] = Field(
            default="NewestFirst",
            description="Sort order.",
        ),
        start_date: Optional[str] = Field(
            default=None,
            description="Inclusive lower bound, ISO 8601 (YYYY-MM-DD).",
            pattern=r"^\d{4}-\d{2}-\d{2}$",
            examples=["2024-03-15"],
        ),
        end_date: Optional[str] = Field(
            default=None,
            description="Inclusive upper bound, ISO 8601 (YYYY-MM-DD).",
            pattern=r"^\d{4}-\d{2}-\d{2}$",
            examples=["2024-03-15"],
        ),
        description: Optional[str] = Field(
            default=None,
            description="Free-text search across merchant/recipient/reference/description.",
        ),
        categories: Optional[list[str]] = Field(
            default=None,
            description="Restrict to these category names (the `name` field from get-categories, not the id).",
        ),
    ) -> list[Transaction]:
        return await get_transactions(
            count=count,
            type=type,
            order=order,
            start_date=start_date,
            end_date=end_date,
            description=description,
            categories=categories,
        )

    @app.tool(
        name="get-categories",
        description=(
            "Get transaction categories. Returns a list of categories "
            "that transactions can be classified into."
        ),
    )
    async def _get_categories() -> list[Category]:
        return await get_categories()

    @app.tool(
        name="spending-summary",
        description=(
            "Get an aggregated spending summary. Returns totals, counts, and averages "
            "grouped by category, category group, month, or merchant."
        ),
    )
    async def _spending_summary(
        group_by: Literal["category", "group", "month", "merchant"] = Field(
            default="category",
            description="Aggregation key.",
        ),
        start_date: Optional[str] = Field(
            default=None,
            description="Inclusive lower bound, ISO 8601 (YYYY-MM-DD).",
            pattern=r"^\d{4}-\d{2}-\d{2}$",
            examples=["2024-03-15"],
        ),
        end_date: Optional[str] = Field(
            default=None,
            description="Inclusive upper bound, ISO 8601 (YYYY-MM-DD).",
            pattern=r"^\d{4}-\d{2}-\d{2}$",
            examples=["2024-03-15"],
        ),
        categories: Optional[list[str]] = Field(
            default=None,
            description="Restrict to these category names (the `name` field from get-categories, not the id).",
        ),
    ) -> SpendingSummary:
        return await get_spending_summary(
            group_by=group_by,
            start_date=start_date,
            end_date=end_date,
            categories=categories,
        )

    @app.tool(
        name="recipients-by-name",
        description=(
            "Lookup recipient of a payment or transfer by name. "
            "Returns matching recipients with their account details."
        ),
    )
    async def _recipients_by_name(
        name: str = Field(
            description="Free-text search; matches partial names of saved recipients.",
        ),
    ) -> list[Recipient]:
        return await search_recipients(name=name)

    @app.tool(
        name="create-recipient",
        description=(
            "Create a new payment recipient with their name, "
            "account number, and national ID. The recipient can then be used for transfers."
        ),
    )
    async def _create_recipient(
        name: str = Field(description="Recipient's full name or business name."),
        account_number: str = Field(
            description="Recipient's bank account number (format varies by country).",
            examples=["5678-90-123456"],
        ),
        kennitala: str = Field(
            default="",
            description="Icelandic national ID for the recipient, if known.",
            examples=["010190-1234"],
        ),
    ) -> CreateRecipientResponse:
        return await create_recipient(
            name=name,
            account_number=account_number,
            kennitala=kennitala,
        )

    @app.tool(
        name="transfer-money-icelandic",
        description=(
            "Prepare a domestic money transfer. "
            "Validates recipient and prepares transfer details for confirmation."
        ),
    )
    async def _transfer_money_icelandic(
        amount: float = Field(
            description="Transfer amount in the source account's currency.",
            gt=0,
        ),
        recipient_ssn: str = Field(
            description="Recipient's Icelandic kennitala.",
            examples=["010190-1234"],
        ),
        recipient_account_number: str = Field(
            description="Destination bank account number.",
            examples=["5678-90-123456"],
        ),
        description: str = Field(
            default="",
            description="Free-text note shown on the recipient's statement.",
        ),
        withdrawal_account_number: str = Field(
            default="",
            description="Source account number; if empty, the user's default withdrawal account is used.",
        ),
        currency: str = Field(
            default="",
            description="ISO 4217 currency code; if empty, source-account currency is used.",
            pattern=r"^[A-Z]{3}$|^$",
            examples=["ISK", "EUR", "USD"],
        ),
    ) -> TransferPreparedResponse:
        return await prepare_transfer(
            amount=amount,
            recipient_ssn=recipient_ssn,
            recipient_account_number=recipient_account_number,
            description=description,
            withdrawal_account_number=withdrawal_account_number,
            currency=currency,
        )

    @app.tool(
        name="execute-transfer",
        description=(
            "Execute a money transfer after the user has confirmed the details. "
            "Use transfer-money-icelandic first to prepare and validate."
        ),
    )
    async def _execute_transfer(
        withdrawal_account_id: str = Field(
            description="Source account.id (from get-accounts).",
        ),
        recipient_account_number: str = Field(
            description="Destination bank account number.",
        ),
        amount: float = Field(
            description="Transfer amount.",
            gt=0,
        ),
        description: str = Field(
            default="Transfer",
            description="Free-text note shown on the recipient's statement.",
        ),
    ) -> ExecuteTransferResponse:
        return await execute_transfer(
            withdrawal_account_id=withdrawal_account_id,
            recipient_account_number=recipient_account_number,
            amount=amount,
            description=description,
        )


