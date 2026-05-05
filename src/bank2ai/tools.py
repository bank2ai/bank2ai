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
    AccountList,
    CategoryList,
    CreateRecipientResponse,
    ExecuteTransferResponse,
    RecipientList,
    SpendingSummary,
    TransactionList,
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
    get_accounts: Optional[Handler] = None,
    get_transactions: Optional[Handler] = None,
    get_categories: Optional[Handler] = None,
    get_spending_summary: Optional[Handler] = None,
    search_recipients: Optional[Handler] = None,
    create_recipient: Optional[Handler] = None,
    prepare_transfer: Optional[Handler] = None,
    execute_transfer: Optional[Handler] = None,
) -> None:
    """Register Bank2AI MCP tools on `app`, dispatching to the handlers
    that were passed in. Tools whose handler is omitted are not
    registered, allowing servers to expose only a subset of the spec.

    Each handler is invoked with keyword arguments matching the tool's
    input schema (using the snake_case names declared below). Handlers
    may return either dicts shaped like the response model or model
    instances directly — FastMCP serializes both via Pydantic.
    """

    if get_accounts is not None:
        _get_accounts_handler = get_accounts

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
        ) -> AccountList:
            return await _get_accounts_handler(
                only_withdrawal_accounts=only_withdrawal_accounts,
                account_type=account_type,
            )

    if get_transactions is not None:
        _get_transactions_handler = get_transactions

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
            account_id: Optional[str] = Field(
                default=None,
                description="Restrict to transactions on this account.id (from get-accounts).",
            ),
        ) -> TransactionList:
            return await _get_transactions_handler(
                count=count,
                type=type,
                order=order,
                start_date=start_date,
                end_date=end_date,
                description=description,
                categories=categories,
                account_id=account_id,
            )

    if get_categories is not None:
        _get_categories_handler = get_categories

        @app.tool(
            name="get-categories",
            description=(
                "Get transaction categories. Returns a list of categories "
                "that transactions can be classified into."
            ),
        )
        async def _get_categories() -> CategoryList:
            return await _get_categories_handler()

    if get_spending_summary is not None:
        _get_spending_summary_handler = get_spending_summary

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
            return await _get_spending_summary_handler(
                group_by=group_by,
                start_date=start_date,
                end_date=end_date,
                categories=categories,
            )

    if search_recipients is not None:
        _search_recipients_handler = search_recipients

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
        ) -> RecipientList:
            return await _search_recipients_handler(name=name)

    if create_recipient is not None:
        _create_recipient_handler = create_recipient

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
            return await _create_recipient_handler(
                name=name,
                account_number=account_number,
                kennitala=kennitala,
            )

    if prepare_transfer is not None:
        _prepare_transfer_handler = prepare_transfer

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
            return await _prepare_transfer_handler(
                amount=amount,
                recipient_ssn=recipient_ssn,
                recipient_account_number=recipient_account_number,
                description=description,
                withdrawal_account_number=withdrawal_account_number,
                currency=currency,
            )

    if execute_transfer is not None:
        _execute_transfer_handler = execute_transfer

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
            return await _execute_transfer_handler(
                withdrawal_account_id=withdrawal_account_id,
                recipient_account_number=recipient_account_number,
                amount=amount,
                description=description,
            )


