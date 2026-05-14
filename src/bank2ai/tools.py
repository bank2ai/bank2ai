"""Reusable bank2ai MCP tool specification.

This module isolates the bank2ai tool spec, names, descriptions, input
parameter signatures, and Pydantic response models, so multiple MCP
servers can expose the same surface without duplicating it. Each server
provides async handler callables and calls `register_tools(app, ...)`.

By default, output schemas are inferred by FastMCP from the Pydantic
response-model annotations on the registered tool functions. Servers
can opt into progressive disclosure (lean `list_tools` payloads, full
output schemas fetched on demand via a `describe-tools` meta tool) by
passing ``output_schemas="discovery"`` to ``register_tools``.

"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Literal, Optional

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from .models import (
    AccountIdentifier,
    AccountList,
    CategoryList,
    CreateRecipientResponse,
    ExecuteTransferResponse,
    GetTransactionResponse,
    NationalId,
    Party,
    PrepareTransferResponse,
    Rail,
    RecipientList,
    RemittanceInformation,
    TransactionList,
    TransactionsSummary,
)


# ---- Handler protocol ----
# Handlers are async callables receiving the input-schema's keyword args
# and returning JSON-serializable data shaped like the response model.

Handler = Callable[..., Awaitable[Any]]

OutputSchemaMode = Literal["inline", "discovery", "off"]


# Canonical response model for each bank2ai tool. Used both as the
# return-type annotation that FastMCP introspects in `inline` mode and
# as the source of schemas served by `describe-tools` in `discovery`
# mode, so the two paths cannot diverge.
_TOOL_RESPONSE_MODELS: dict[str, type[BaseModel]] = {
    "get-accounts": AccountList,
    "get-transactions": TransactionList,
    "get-transaction": GetTransactionResponse,
    "get-categories": CategoryList,
    "get-transactions-summary": TransactionsSummary,
    "get-recipients": RecipientList,
    "create-recipient": CreateRecipientResponse,
    "prepare-transfer": PrepareTransferResponse,
    "execute-transfer": ExecuteTransferResponse,
}


# ---- Tool registration ----


def register_tools(
    app: FastMCP,
    *,
    get_accounts: Optional[Handler] = None,
    get_transactions: Optional[Handler] = None,
    get_transaction: Optional[Handler] = None,
    get_categories: Optional[Handler] = None,
    get_transactions_summary: Optional[Handler] = None,
    get_recipients: Optional[Handler] = None,
    create_recipient: Optional[Handler] = None,
    prepare_transfer: Optional[Handler] = None,
    execute_transfer: Optional[Handler] = None,
    output_schemas: OutputSchemaMode = "inline",
) -> None:
    """Register bank2ai MCP tools on `app`, dispatching to the handlers
    that were passed in. Tools whose handler is omitted are not
    registered, allowing servers to expose only a subset of the spec.

    Each handler is invoked with keyword arguments matching the tool's
    input schema (using the snake_case names declared below). Handlers
    may return either dicts shaped like the response model or model
    instances directly, FastMCP serializes both via Pydantic.

    ``output_schemas`` controls how output JSON Schemas are exposed:

    * ``"inline"`` (default): FastMCP inlines each tool's output schema
      in ``list_tools``, inferred from its Pydantic return annotation.
    * ``"discovery"``: ``list_tools`` returns no output schemas. A
      companion ``describe-tools`` tool is registered so clients can
      pull the schemas they need on demand (progressive disclosure).
    * ``"off"``: output schemas are suppressed and no meta tool is
      registered. Use when clients have the schemas out of band.
    """

    _out_kwarg: dict[str, Any] = (
        {} if output_schemas == "inline" else {"output_schema": None}
    )
    _registered_names: list[str] = []

    _discovery_suffix = (
        " Output JSON Schema available on demand via `describe-tools`."
        if output_schemas == "discovery"
        else ""
    )

    def _desc(text: str) -> str:
        return text + _discovery_suffix

    if get_accounts is not None:
        _registered_names.append("get-accounts")
        _get_accounts_handler = get_accounts

        @app.tool(
            name="get-accounts",
            description=_desc(
                "Get the user's bank accounts and cards. Returns each account "
                "with balances, identifiers (account number, plus IBAN/BBAN/BIC "
                "or masked PAN where the bank has them), holder, product, type, "
                "lifecycle status, and usage. Field shapes follow the Berlin "
                "Group PSD2 `accountDetails` model where they overlap."
            ),
            **_out_kwarg,
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
            return await _get_accounts_handler(
                only_withdrawal_accounts=only_withdrawal_accounts,
                account_type=account_type,
                status=status,
                usage=usage,
            )

    if get_transactions is not None:
        _registered_names.append("get-transactions")
        _get_transactions_handler = get_transactions

        @app.tool(
            name="get-transactions",
            description=_desc(
                "Get bank transactions. Returns a list of transactions "
                "with amounts, dates, descriptions, and categories. The "
                "`verbosity` parameter caps how many optional fields the "
                "server populates: use `minimal` for compact lists, "
                "`standard` (default) for general use, `full` for an "
                "audit / reconciliation view including ISO 20022 "
                "metadata when the server can populate it."
            ),
            **_out_kwarg,
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
            verbosity: Literal["minimal", "standard", "full"] = Field(
                default="standard",
                description=(
                    "Upper bound on optional fields each Transaction may "
                    "carry. `minimal` keeps only the required fields plus "
                    "`counterpartyName`; `standard` adds `status`, "
                    "`categoryId`, `originalCurrency`, `originalAmount`; "
                    "`full` additionally allows every ISO 20022 optional "
                    "field (`valueDate`, `categoryRaw`, `counterparty`, "
                    "`transactionCode`, `remittanceInformation`, "
                    "`endToEndId`, `merchantCategoryCode`). Servers MAY "
                    "omit any optional field even at `full` if they don't "
                    "have it."
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
            description: Optional[str] = Field(
                default=None,
                description="Free-text search across merchant/recipient/reference/description.",
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
            return await _get_transactions_handler(
                count=count,
                order=order,
                verbosity=verbosity,
                start_date=start_date,
                end_date=end_date,
                description=description,
                category_ids=category_ids,
                account_ids=account_ids,
                min_amount=min_amount,
                max_amount=max_amount,
                cursor=cursor,
            )

    if get_transaction is not None:
        _registered_names.append("get-transaction")
        _get_transaction_handler = get_transaction

        @app.tool(
            name="get-transaction",
            description=_desc(
                "Look up a single transaction by id and return every "
                "field the server can populate, including ISO 20022 "
                "metadata (transactionCode, remittanceInformation, "
                "endToEndId, merchantCategoryCode, etc.). Use this for "
                "audit / reconciliation flows; for compact lists prefer "
                "`get-transactions` with a `verbosity` cap."
            ),
            **_out_kwarg,
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
            return await _get_transaction_handler(
                transaction_id=transaction_id,
                account_id=account_id,
            )

    if get_categories is not None:
        _registered_names.append("get-categories")
        _get_categories_handler = get_categories

        @app.tool(
            name="get-categories",
            description=_desc(
                "Get transaction categories. Returns a list of categories "
                "that transactions can be classified into."
            ),
            **_out_kwarg,
        )
        async def _get_categories() -> CategoryList:
            return await _get_categories_handler()

    if get_transactions_summary is not None:
        _registered_names.append("get-transactions-summary")
        _get_transactions_summary_handler = get_transactions_summary

        @app.tool(
            name="get-transactions-summary",
            description=_desc(
                "Get an aggregated summary of transactions, scoped to either income or "
                "expenses. Returns totals, counts, and averages, optionally grouped by "
                "category, month, or both. Filters mirror get-transactions: account, "
                "date, amount range, category ids."
            ),
            **_out_kwarg,
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
            return await _get_transactions_summary_handler(
                direction=direction,
                group_by=group_by,
                start_date=start_date,
                end_date=end_date,
                category_ids=category_ids,
                account_ids=account_ids,
                min_amount=min_amount,
                max_amount=max_amount,
            )

    if get_recipients is not None:
        _registered_names.append("get-recipients")
        _get_recipients_handler = get_recipients

        @app.tool(
            name="get-recipients",
            description=_desc(
                "Get saved payment recipients filtered by name. "
                "Returns matching recipients with their account details."
            ),
            **_out_kwarg,
        )
        async def _get_recipients(
            name: str = Field(
                description="Free-text search; matches partial names of saved recipients.",
            ),
        ) -> RecipientList:
            return await _get_recipients_handler(name=name)

    if create_recipient is not None:
        _registered_names.append("create-recipient")
        _create_recipient_handler = create_recipient

        @app.tool(
            name="create-recipient",
            description=_desc(
                "Create a new payment recipient. Account routing goes "
                "through the typed `account_identifier` discriminated "
                "union (IBAN, BBAN with country, country-specific account "
                "number, or alias). National identification, when known, "
                "uses the typed `national_id` sub-object. The recipient "
                "can then be used for transfers."
            ),
            **_out_kwarg,
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
            return await _create_recipient_handler(
                name=name,
                account_identifier=account_identifier,
                national_id=national_id,
                nickname=nickname,
                bic=bic,
                default_description=default_description,
                idempotency_key=idempotency_key,
            )

    if prepare_transfer is not None:
        _registered_names.append("prepare-transfer")
        _prepare_transfer_handler = prepare_transfer

        @app.tool(
            name="prepare-transfer",
            description=_desc(
                "Prepare a money transfer on any supported rail (SEPA, "
                "SEPA Instant, SWIFT, domestic-IS, etc.). Validates the "
                "creditor, computes fees / FX / payee verification when "
                "applicable, and returns a transferIntentId plus a "
                "summary the user confirms. Does NOT execute; pass the "
                "intent id to `execute-transfer`."
            ),
            **_out_kwarg,
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
            return await _prepare_transfer_handler(
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

    if execute_transfer is not None:
        _registered_names.append("execute-transfer")
        _execute_transfer_handler = execute_transfer

        @app.tool(
            name="execute-transfer",
            description=_desc(
                "Execute a transfer the user has confirmed. Takes only "
                "the `transfer_intent_id` returned by `prepare-transfer`. "
                "The intent's amount, creditor, debtor, and rail are "
                "immutable: any change requires a new prepare call. "
                "Servers reject expired intents with a structured error."
            ),
            **_out_kwarg,
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
            return await _execute_transfer_handler(
                transfer_intent_id=transfer_intent_id,
                idempotency_key=idempotency_key,
            )

    if output_schemas == "discovery":

        @app.tool(
            name="describe-tools",
            description=(
                "Return the output JSON Schema for one or more bank2ai "
                "tools registered on this server. Use this when you need "
                "to validate or parse a tool's response: the server omits "
                "`outputSchema` from `tools/list` to keep the listing "
                "compact, and serves the schemas here on demand. Pass "
                "`tool_names` to fetch a subset, or omit it for every "
                "registered tool. Unknown names yield an `outputSchema` "
                "of `null` rather than an error."
            ),
            output_schema=None,
        )
        async def _describe_tools(
            tool_names: Optional[list[str]] = Field(
                default=None,
                description=(
                    "Tool names to describe (e.g. `[\"get-accounts\", "
                    "\"prepare-transfer\"]`). Omit to receive every "
                    "bank2ai tool registered on this server."
                ),
            ),
        ) -> dict[str, Any]:
            target = tool_names if tool_names else list(_registered_names)
            schemas: dict[str, dict[str, Any]] = {}
            for name in target:
                if name in _registered_names:
                    model = _TOOL_RESPONSE_MODELS.get(name)
                    schemas[name] = {
                        "outputSchema": (
                            model.model_json_schema() if model is not None else None
                        ),
                    }
                else:
                    schemas[name] = {"outputSchema": None}
            return {"schemas": schemas}
