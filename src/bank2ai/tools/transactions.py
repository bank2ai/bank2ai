"""Registrations for the transaction-oriented tools (including `get-categories`)."""

from __future__ import annotations

from typing import Literal, Optional

from fastmcp import FastMCP
from pydantic import Field

from ..models import (
    CategoryList,
    GetTransactionResponse,
    TransactionList,
    TransactionsSummary,
)
from .base import Handler, OutputSchemaMode, build_decorator_helpers


def register_get_transactions(
    app: FastMCP,
    handler: Handler,
    *,
    output_schemas: OutputSchemaMode,
) -> str:
    out_kwarg, desc = build_decorator_helpers(output_schemas)

    @app.tool(
        name="get-transactions",
        description=desc(
            "Get bank transactions. Returns a list of transactions "
            "with amounts, dates, descriptions, and categories. The "
            "`verbosity` parameter selects between a compact default "
            "(`minimal`) and full transactions view (`full`) "
            "that surfaces every optional ISO 20022 / Open Finance "
            "field the server can populate."
        ),
        **out_kwarg,
    )
    async def _get_transactions(
        count: Optional[int] = Field(
            default=None,
            description="Maximum number of transactions to return.",
            ge=1,
        ),
        order: Literal["NewestFirst", "OldestFirst"] = Field(
            default="NewestFirst",
            description="Sort order.",
        ),
        verbosity: Optional[Literal["minimal", "full"]] = Field(
            default=None,
            description=(
                "`minimal` returns every Transaction field except "
                "`counterparty` and the `properties` audit bag, on the "
                "assumption that the merchant / counterparty name is "
                "read off `description` and ISO 20022 / Open Finance "
                "audit metadata isn't needed for everyday questions. "
                "`full` returns every field the server can populate. "
                "Servers MAY still omit any optional field at `full` "
                "if they don't have it. When omitted, defaults to "
                "`full` if `search_text` is set (so client-side "
                "filtering has the extra context) and `minimal` "
                "otherwise."
            ),
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
        search_text: Optional[str] = Field(
            default=None,
            description=(
                "Single-token, greedy substring match across a transaction's "
                "text fields (description, counterparty, remittance, references). "
                "Prefer the most distinctive token and narrow the rest "
                "client-side (e.g. via the LLM): for \"Starbucks Oxford Street\" "
                "pass `Starbucks` and filter the location locally."
            ),
        ),
        category_ids: Optional[list[str]] = Field(
            default=None,
            description="Restrict to these category ids (the `id` field from get-categories).",
        ),
        account_ids: Optional[list[str]] = Field(
            default=None,
            description="Restrict to transactions on these account.id values (from get-accounts).",
        ),
        min_amount: Optional[float] = Field(
            default=None,
            description=(
                "Inclusive lower bound on the transaction amount. "
                "Amounts are signed: expenses are negative, income is positive. "
                "Examples: `min_amount=0` keeps only income; "
                "`min_amount=-100` drops expenses larger than 100."
            ),
        ),
        max_amount: Optional[float] = Field(
            default=None,
            description=(
                "Inclusive upper bound on the transaction amount. "
                "Amounts are signed: expenses are negative, income is positive. "
                "Examples: `max_amount=0` keeps only expenses; "
                "`max_amount=-50` keeps only expenses of 50 or more (in absolute value)."
            ),
        ),
        cursor: Optional[str] = Field(
            default=None,
            description=(
                "Opaque pagination cursor returned as `nextCursor` from a "
                "previous call. Omit to fetch the first page."
            ),
        ),
    ) -> TransactionList:
        resolved_verbosity = verbosity or ("full" if search_text else "minimal")
        return await handler(
            count=count,
            order=order,
            verbosity=resolved_verbosity,
            start_date=start_date,
            end_date=end_date,
            search_text=search_text,
            category_ids=category_ids,
            account_ids=account_ids,
            min_amount=min_amount,
            max_amount=max_amount,
            cursor=cursor,
        )

    return "get-transactions"


def register_get_transaction(
    app: FastMCP,
    handler: Handler,
    *,
    output_schemas: OutputSchemaMode,
) -> str:
    out_kwarg, desc = build_decorator_helpers(output_schemas)

    @app.tool(
        name="get-transaction",
        description=desc(
            "Look up a single transaction by id and return every "
            "field the server can populate, including `counterparty` "
            "(with `postalAddress` for card entries) and the open "
            "`properties` bag of ISO 20022 / SEPA / card audit metadata "
            "(remittance text, end-to-end / mandate / creditor ids, "
            "purpose / transaction codes, MCC, masked PAN, etc.). Use "
            "this for audit / reconciliation flows; for compact lists "
            "prefer `get-transactions` with a `verbosity` cap."
        ),
        **out_kwarg,
    )
    async def _get_transaction(
        transaction_id: str = Field(
            description="Transaction id (the `id` field from get-transactions).",
        ),
        account_id: Optional[str] = Field(
            default=None,
            description=(
                "Source account.id (from get-accounts). Optional; servers "
                "MAY require it for routing or for additional "
                "authorization checks."
            ),
        ),
    ) -> GetTransactionResponse:
        return await handler(
            transaction_id=transaction_id,
            account_id=account_id,
        )

    return "get-transaction"


def register_get_transactions_summary(
    app: FastMCP,
    handler: Handler,
    *,
    output_schemas: OutputSchemaMode,
) -> str:
    out_kwarg, desc = build_decorator_helpers(output_schemas)

    @app.tool(
        name="get-transactions-summary",
        description=desc(
            "Get an aggregated summary of transactions, scoped to either income or "
            "expenses. Returns totals, counts, and averages, optionally grouped by "
            "category, month, or both. Filters mirror get-transactions: account, "
            "date, amount range, category ids."
        ),
        **out_kwarg,
    )
    async def _transactions_summary(
        direction: Literal["Income", "Expenses"] = Field(
            description=(
                "Restrict to income (positive amounts) or expenses (negative amounts). "
                "A summary covers exactly one direction; call the tool twice to compare."
            ),
        ),
        group_by: Literal["none", "category", "month", "both"] = Field(
            default="category",
            description=(
                "Aggregation key. `none` returns a single row spanning all matched "
                "transactions; `category` groups by category id; `month` groups by "
                "calendar month (YYYY-MM); `both` groups by (category id, month) pairs. "
                "Each summary row reports `categoryId` and/or `month` accordingly."
            ),
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
        category_ids: Optional[list[str]] = Field(
            default=None,
            description="Restrict to these category ids (the `id` field from get-categories).",
        ),
        account_ids: Optional[list[str]] = Field(
            default=None,
            description="Restrict to transactions on these account.id values (from get-accounts).",
        ),
        min_amount: Optional[float] = Field(
            default=None,
            description=(
                "Inclusive lower bound on the transaction amount. "
                "Amounts are signed: expenses are negative, income is positive. "
                "Combined with `direction`, both filters are applied."
            ),
        ),
        max_amount: Optional[float] = Field(
            default=None,
            description=(
                "Inclusive upper bound on the transaction amount. "
                "Amounts are signed: expenses are negative, income is positive. "
                "Combined with `direction`, both filters are applied."
            ),
        ),
    ) -> TransactionsSummary:
        return await handler(
            direction=direction,
            group_by=group_by,
            start_date=start_date,
            end_date=end_date,
            category_ids=category_ids,
            account_ids=account_ids,
            min_amount=min_amount,
            max_amount=max_amount,
        )

    return "get-transactions-summary"


def register_get_categories(
    app: FastMCP,
    handler: Handler,
    *,
    output_schemas: OutputSchemaMode,
) -> str:
    out_kwarg, desc = build_decorator_helpers(output_schemas)

    @app.tool(
        name="get-categories",
        description=desc(
            "Get transaction categories. Returns a list of categories "
            "that transactions can be classified into."
        ),
        **out_kwarg,
    )
    async def _get_categories() -> CategoryList:
        return await handler()

    return "get-categories"
