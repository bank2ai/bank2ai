"""Reusable Bank2AI MCP tool specification.

This module isolates the Bank2AI tool spec — names, descriptions, input
parameter signatures, and Pydantic response models — so multiple MCP
servers can expose the same surface without duplicating it. Each server
provides async handler callables and calls `register_tools(app, ...)`.

Output schemas are inferred by FastMCP from the Pydantic response-model
annotations on the registered tool functions.

Auth helpers (middleware + dynamic `authenticate` tool) live alongside
since they share the auth-param types.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable, Literal, Optional

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools.base import Tool
from pydantic import BaseModel, Field

from models import (
    Account,
    AuthParam,
    AuthParamType,
    AuthParamValue,
    AuthResponse,
    Category,
    Receipient,
    Transaction,
)


# ---- Bank2AI response wrapper models ----

class SpendingSummaryGroup(BaseModel):
    group: str
    total_amount: float
    transaction_count: int
    average_amount: float


class SpendingSummaryPeriod(BaseModel):
    start_date: str
    end_date: str


class SpendingSummary(BaseModel):
    """Aggregated spending summary"""

    summary: list[SpendingSummaryGroup]
    period: SpendingSummaryPeriod
    total: float


class CreateRecipientResponse(BaseModel):
    """Result of creating a payment recipient"""

    content: str = Field(description="Human-readable status message")
    item: Optional[Receipient] = None


class TransferAction(BaseModel):
    title: str
    link: str


class TransferPreparedItem(BaseModel):
    amount: float
    description: str
    currency: str
    recipient_account_number: str
    recipient_ssn: str
    recipient_name: str
    withdrawal_account_id: str
    withdrawal_account: Account


class TransferPreparedResponse(BaseModel):
    """Prepared transfer details awaiting confirmation"""

    content: str = Field(description="Human-readable status message")
    item: Optional[TransferPreparedItem] = None
    actions: list[TransferAction] = Field(default_factory=list)


class ExecuteTransferDetail(BaseModel):
    transfer_id: str
    status: str
    timestamp: str


class ExecuteTransferResponse(BaseModel):
    """Result of executing a transfer"""

    content: str
    item: Optional[ExecuteTransferDetail] = None


class AuthenticateResponse(BaseModel):
    """Authentication result"""

    message: Optional[str] = None
    error: Optional[str] = None


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
    ) -> list[Receipient]:
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


# ---- Authentication helpers ----

AUTHENTICATE_TOOL_NAME = "authenticate"

AuthenticateHandler = Callable[[list[AuthParamValue]], Awaitable[AuthResponse]]


class AuthState:
    """Mutable wrapper holding the latest AuthResponse for one server."""

    def __init__(self) -> None:
        self.response: Optional[AuthResponse] = None


def _client_supports_elicitation(ctx: Context, logger: logging.Logger) -> bool:
    session = ctx.session
    client_caps = session.client_params.capabilities if session.client_params else None
    logger.info("Client capabilities: %s", client_caps)
    if client_caps and client_caps.elicitation:
        logger.info("Client elicitation capability: %s", client_caps.elicitation)
        return True
    return False


def _build_elicit_schema(auth_parameters: list[AuthParam]) -> dict:
    properties: dict[str, dict] = {}
    required: list[str] = []
    for param in auth_parameters:
        prop: dict = {"type": "string", "title": param.title}
        if param.type == AuthParamType.Password:
            prop["x-password"] = True
        properties[param.id] = prop
        required.append(param.id)
    return {"type": "object", "properties": properties, "required": required}


async def _elicit_credentials(
    ctx: Context,
    auth_parameters: list[AuthParam],
    logger: logging.Logger,
    authenticate: AuthenticateHandler,
) -> AuthResponse:
    schema = _build_elicit_schema(auth_parameters)
    logger.info("Elicitation schema: %s", json.dumps(schema))
    result = await ctx.session.elicit_form(
        message="Please provide your banking credentials to continue.",
        requestedSchema=schema,
        related_request_id=ctx.request_id,
    )
    if result.action != "accept" or not result.content:
        return AuthResponse(authenticated=False, message="Authentication cancelled by user")

    param_values = [
        AuthParamValue(id=key, value=str(value))
        for key, value in result.content.items()
        if value is not None
    ]
    return await authenticate(param_values)


async def _ensure_authenticated(
    ctx: Context,
    state: AuthState,
    authenticate: AuthenticateHandler,
    logger: logging.Logger,
) -> str | None:
    if state.response is None:
        state.response = await authenticate([])
    if state.response.authenticated:
        return None

    if state.response.required_parameters and _client_supports_elicitation(ctx, logger):
        logger.info("Client supports elicitation, collecting credentials interactively")
        state.response = await _elicit_credentials(
            ctx, state.response.required_parameters, logger, authenticate
        )
        if state.response.authenticated:
            return None
    elif state.response.required_parameters:
        logger.info("Not authenticated, directing LLM to use authenticate tool")
        return (
            "Not authenticated. Please call the 'authenticate' tool first with the user's credentials."
        )

    if state.response.message:
        logger.info("Auth response message: %s", state.response.message)
        return "Communicate this to the end user:\n" + state.response.message

    return state.response.message or "Authentication failed"


def make_auth_middleware(
    state: AuthState,
    authenticate: AuthenticateHandler,
    logger: logging.Logger,
    *,
    log_responses: bool = False,
) -> Middleware:
    """Build a FastMCP middleware that ensures auth before each non-auth tool
    call and retries once on error after re-authenticating."""

    class _AuthMiddleware(Middleware):
        async def on_call_tool(self, mctx: MiddlewareContext, call_next):
            tool_name = mctx.message.name
            if tool_name == AUTHENTICATE_TOOL_NAME:
                return await call_next(mctx)

            ctx = mctx.fastmcp_context
            last_error: Exception | None = None
            for _ in range(2):
                err = await _ensure_authenticated(ctx, state, authenticate, logger)
                if err is not None:
                    raise ToolError(err)
                try:
                    result = await call_next(mctx)
                    if log_responses:
                        logger.info("call_tool response: %s result=%s", tool_name, result)
                    return result
                except Exception as e:
                    logger.info("Problem when calling tool, try again after re-authentication: %s", e)
                    state.response = None
                    last_error = e

            raise last_error  # type: ignore[misc]

    return _AuthMiddleware()


async def register_authenticate_tool(
    app: FastMCP,
    state: AuthState,
    authenticate: AuthenticateHandler,
) -> None:
    """Register the `authenticate` tool with a signature matching the
    handler's required auth params. No-op when authentication needs no
    user-supplied parameters (e.g. demo servers)."""

    init = await authenticate([])
    state.response = init
    if not init.required_parameters:
        return

    async def _do_authenticate(creds: dict[str, str]) -> AuthenticateResponse:
        param_values = [
            AuthParamValue(id=p.id, value=creds.get(p.id, ""))
            for p in (state.response.required_parameters if state.response else [])
        ]
        state.response = await authenticate(param_values)
        if state.response.authenticated:
            return AuthenticateResponse(message="Authentication successful")
        return AuthenticateResponse(error=state.response.message or "Authentication failed")

    sig = ", ".join(
        f"{p.id}: str = Field(description={p.title!r})"
        for p in init.required_parameters
    )
    body_args = ", ".join(
        f'"{p.id}": {p.id}' for p in init.required_parameters
    )
    src = (
        f"async def authenticate({sig}) -> AuthenticateResponse:\n"
        f"    return await _do_authenticate({{{body_args}}})\n"
    )
    namespace: dict = {
        "_do_authenticate": _do_authenticate,
        "Field": Field,
        "AuthenticateResponse": AuthenticateResponse,
    }
    exec(src, namespace)
    fn = namespace["authenticate"]

    titles = ", ".join(f"{p.id} ({p.title})" for p in init.required_parameters)
    tool = Tool.from_function(
        fn,
        name=AUTHENTICATE_TOOL_NAME,
        description=(
            "Authenticate with the bank. Must be called before any other tool when the "
            "server is not yet authenticated. Ask the user for the required credentials. "
            f"Required fields: {titles}."
        ),
    )
    app.add_tool(tool)
