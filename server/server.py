"""Bank2AI Demo MCP Server

A reference implementation of the Bank2AI specification using hardcoded test data.
This server demonstrates how to implement the Bank2AI tools using FastMCP.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Literal, Optional

from dotenv import load_dotenv
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools.base import Tool
from pydantic import Field

from adapters import get_adapter
from adapters.models import (
    Account,
    AuthParam,
    AuthParamType,
    AuthParamValue,
    AuthResponse,
    Category,
    Receipient,
    Transaction,
    TransactionOrder,
    TransactionType,
)


load_dotenv()

# Configure file logging (log to repository root)
_repo_root = Path(__file__).resolve().parent.parent
logging.basicConfig(
    filename=_repo_root / "bank2ai-server.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("bank2ai")
_log_responses = os.environ.get("BANK2AI_LOG_RESPONSES", "").lower() in ("1", "true", "yes")

# Initialize FastMCP server and bank adapter
app = FastMCP("bank2ai-demo")
adapter = get_adapter(logger)
auth_response: AuthResponse | None = None

AUTHENTICATE_TOOL_NAME = "authenticate"


# ---- Output schemas ----

_SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"


def _load_item_schema(filename: str) -> dict[str, Any]:
    """Load a JSON Schema for a single item type from the schemas/ directory."""
    schema = json.loads((_SCHEMA_DIR / filename).read_text())
    # Strip top-level metadata that doesn't belong in an embedded outputSchema.
    schema.pop("$schema", None)
    schema.pop("$id", None)
    return schema


_ACCOUNT_SCHEMA = _load_item_schema("account.json")
_RECIPIENT_SCHEMA = _load_item_schema("recipient.json")

SPENDING_SUMMARY_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Aggregated spending summary",
    "properties": {
        "summary": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "group": {"type": "string"},
                    "total_amount": {"type": "number"},
                    "transaction_count": {"type": "integer"},
                    "average_amount": {"type": "number"},
                },
                "required": ["group", "total_amount", "transaction_count", "average_amount"],
            },
        },
        "period": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string"},
                "end_date": {"type": "string"},
            },
            "required": ["start_date", "end_date"],
        },
        "total": {"type": "number"},
    },
    "required": ["summary", "period", "total"],
}

CREATE_RECIPIENT_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Result of creating a payment recipient",
    "properties": {
        "content": {"type": "string", "description": "Human-readable status message"},
        "item": _RECIPIENT_SCHEMA,
    },
    "required": ["content"],
}

TRANSFER_PREPARED_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Prepared transfer details awaiting confirmation",
    "properties": {
        "content": {"type": "string", "description": "Human-readable status message"},
        "item": {
            "type": "object",
            "properties": {
                "amount": {"type": "number"},
                "description": {"type": "string"},
                "currency": {"type": "string"},
                "recipient_account_number": {"type": "string"},
                "recipient_ssn": {"type": "string"},
                "recipient_name": {"type": "string"},
                "withdrawal_account_id": {"type": "string"},
                "withdrawal_account": _ACCOUNT_SCHEMA,
            },
        },
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "link": {"type": "string"},
                },
                "required": ["title", "link"],
            },
        },
    },
    "required": ["content"],
}

EXECUTE_TRANSFER_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Result of executing a transfer",
    "properties": {
        "content": {"type": "string"},
        "item": {
            "type": "object",
            "properties": {
                "transfer_id": {"type": "string"},
                "status": {"type": "string"},
                "timestamp": {"type": "string"},
            },
            "required": ["transfer_id", "status", "timestamp"],
        },
    },
    "required": ["content"],
}

AUTHENTICATE_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Authentication result",
    "properties": {
        "message": {"type": "string"},
        "error": {"type": "string"},
    },
}


# ---- Auth helpers ----


def _client_supports_elicitation(ctx: Context) -> bool:
    """Check if the connected client supports elicitation."""
    session = ctx.session
    client_caps = session.client_params.capabilities if session.client_params else None
    logger.info("Client capabilities: %s", client_caps)
    if client_caps and client_caps.elicitation:
        logger.info("Client elicitation capability: %s", client_caps.elicitation)
        return True
    return False


def _build_elicit_schema(auth_parameters: list[AuthParam]) -> dict:
    """Build a JSON Schema for elicitation from the adapter's auth params."""
    properties = {}
    required = []
    for param in auth_parameters:
        prop: dict = {
            "type": "string",
            "title": param.title,
        }
        if param.type == AuthParamType.Password:
            prop["x-password"] = True
        properties[param.id] = prop
        required.append(param.id)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


async def _authenticate_with_elicitation(ctx: Context, auth_parameters: list[AuthParam]) -> AuthResponse:
    """Use MCP elicitation to collect credentials from the user, then authenticate."""
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
    return await adapter.authenticate(param_values)


async def _ensure_authenticated(ctx: Context) -> str | None:
    """Ensure the adapter is authenticated. Return an error string for the LLM, or None."""
    global auth_response

    if auth_response is None:
        auth_response = await adapter.authenticate([])

    if auth_response.authenticated:
        return None

    if auth_response.required_parameters and _client_supports_elicitation(ctx):
        logger.info("Client supports elicitation, collecting credentials interactively")
        auth_response = await _authenticate_with_elicitation(ctx, auth_response.required_parameters)
        if auth_response.authenticated:
            return None
    elif auth_response.required_parameters:
        logger.info("Not authenticated, directing LLM to use authenticate tool")
        return (
            "Not authenticated. Please call the 'authenticate' tool first with the user's credentials."
        )

    if auth_response.message:
        logger.info("Auth response message: %s", auth_response.message)
        return "Communicate this to the end user:\n" + auth_response.message

    return auth_response.message or "Authentication failed"


# ---- Middleware ----

class AuthMiddleware(Middleware):
    """Authenticates the bank adapter before each tool call and retries once on error."""

    async def on_call_tool(self, mctx: MiddlewareContext, call_next):
        global auth_response

        tool_name = mctx.message.name
        # The authenticate tool is the only way to (re)establish auth — never gate it.
        if tool_name == AUTHENTICATE_TOOL_NAME:
            return await call_next(mctx)

        ctx = mctx.fastmcp_context
        last_error: Exception | None = None
        for _ in range(2):
            err = await _ensure_authenticated(ctx)
            if err is not None:
                # Raise so the MCP layer returns an isError result and skips
                # output-schema validation.
                raise ToolError(err)
            try:
                result = await call_next(mctx)
                if _log_responses:
                    logger.info("call_tool response: %s result=%s", tool_name, result)
                return result
            except Exception as e:
                logger.info("Problem when calling tool, try again after re-authentication: %s", e)
                auth_response = None
                last_error = e

        raise last_error  # type: ignore[misc]


app.add_middleware(AuthMiddleware())


# ---- Tools ----

@app.tool(
    name="get-accounts",
    description=(
        "Get bank accounts and cards. Returns a list of accounts "
        "with balances, account numbers, and types."
    ),
)
async def get_accounts(
    only_withdrawal_accounts: bool = Field(
        default=False,
        description="If true, return only accounts usable for withdrawals/transfers.",
    ),
    account_type: Optional[Literal["Current", "Savings", "Credit"]] = Field(
        default=None,
        description="Filter by account type.",
    ),
) -> list[Account]:
    logger.info("call_tool: get-accounts only_withdrawal=%s account_type=%s",
                only_withdrawal_accounts, account_type)
    return await adapter.get_accounts(
        only_withdrawal=only_withdrawal_accounts,
        account_type=account_type,
    )


@app.tool(
    name="transactions",
    description=(
        "Get bank transactions. Returns a list of transactions "
        "with amounts, dates, descriptions, and categories."
    ),
    
)
async def transactions(
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
    logger.info("call_tool: transactions count=%s type=%s order=%s", count, type, order)
    return await adapter.get_transactions(
        count=count,
        type=TransactionType(type),
        order=TransactionOrder(order),
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
async def get_categories() -> list[Category]:
    logger.info("call_tool: get-categories")
    return await adapter.get_categories()


@app.tool(
    name="spending-summary",
    description=(
        "Get an aggregated spending summary. Returns totals, counts, and averages "
        "grouped by category, category group, month, or merchant."
    ),
    output_schema=SPENDING_SUMMARY_OUTPUT_SCHEMA,
)
async def spending_summary(
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
) -> dict:
    logger.info("call_tool: spending-summary group_by=%s", group_by)
    return await adapter.get_spending_summary(
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
async def recipients_by_name(
    name: str = Field(
        description="Free-text search; matches partial names of saved recipients.",
    ),
) -> list[Receipient]:
    logger.info("call_tool: recipients-by-name name=%s", name)
    return await adapter.search_recipients(name=name)


@app.tool(
    name="create-recipient",
    description=(
        "Create a new payment recipient with their name, "
        "account number, and national ID. The recipient can then be used for transfers."
    ),
    output_schema=CREATE_RECIPIENT_OUTPUT_SCHEMA,
)
async def create_recipient(
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
) -> dict:
    logger.info("call_tool: create-recipient name=%s", name)
    return await adapter.create_recipient(
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
    output_schema=TRANSFER_PREPARED_OUTPUT_SCHEMA,
)
async def transfer_money_icelandic(
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
) -> dict:
    logger.info("call_tool: transfer-money-icelandic amount=%s", amount)
    return await adapter.prepare_transfer(
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
    output_schema=EXECUTE_TRANSFER_OUTPUT_SCHEMA,
)
async def execute_transfer(
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
) -> dict:
    logger.info("call_tool: execute-transfer amount=%s", amount)
    return await adapter.execute_transfer(
        withdrawal_account_id=withdrawal_account_id,
        recipient_account_number=recipient_account_number,
        amount=amount,
        description=description,
    )


# ---- Authenticate tool (registered dynamically based on adapter auth params) ----

async def _do_authenticate(creds: dict[str, str]) -> dict:
    global auth_response
    if auth_response is None:
        auth_response = await adapter.authenticate([])

    param_values = [
        AuthParamValue(id=p.id, value=creds.get(p.id, ""))
        for p in auth_response.required_parameters
    ]
    auth_response = await adapter.authenticate(param_values)
    if auth_response.authenticated:
        return {"message": "Authentication successful"}
    return {"error": auth_response.message or "Authentication failed"}


async def _register_authenticate_tool() -> None:
    """Register the authenticate tool with a signature matching the adapter's auth params."""
    init = await adapter.authenticate([])
    if not init.required_parameters:
        return  # Adapter doesn't require auth — no authenticate tool needed.

    # Build a function with one str parameter per auth param so FastMCP can infer the schema.
    param_names = [p.id for p in init.required_parameters]
    sig = ", ".join(
        f"{p.id}: str = Field(description={p.title!r})"
        for p in init.required_parameters
    )
    body_args = ", ".join(f'"{name}": {name}' for name in param_names)
    src = (
        f"async def authenticate({sig}) -> dict:\n"
        f"    return await _do_authenticate({{{body_args}}})\n"
    )
    namespace: dict = {"_do_authenticate": _do_authenticate, "Field": Field}
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
        output_schema=AUTHENTICATE_OUTPUT_SCHEMA,
    )
    app.add_tool(tool)


async def main() -> None:
    """Run the MCP server over stdio."""
    await _register_authenticate_tool()
    await app.run_async()


if __name__ == "__main__":
    asyncio.run(main())
