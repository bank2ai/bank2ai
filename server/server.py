"""Bank2AI Demo MCP Server

A reference implementation of the Bank2AI specification using hardcoded test data.
This server demonstrates how to implement the Bank2AI tools using FastMCP.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastmcp import Context, FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools.base import Tool, ToolResult

from adapters import get_adapter
from adapters.models import (
    AuthParam,
    AuthParamType,
    AuthParamValue,
    AuthReponse,
    TransactionOrder,
    TransactionType,
    custom_json_encoder,
)


def _json(obj, **kwargs) -> str:
    """JSON-encode with non-ASCII characters preserved."""
    return json.dumps(obj, ensure_ascii=False, **kwargs)


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
auth_response: AuthReponse | None = None

AUTHENTICATE_TOOL_NAME = "authenticate"


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


async def _authenticate_with_elicitation(ctx: Context, auth_parameters: list[AuthParam]) -> AuthReponse:
    """Use MCP elicitation to collect credentials from the user, then authenticate."""
    schema = _build_elicit_schema(auth_parameters)
    logger.info("Elicitation schema: %s", json.dumps(schema))

    result = await ctx.session.elicit_form(
        message="Please provide your banking credentials to continue.",
        requestedSchema=schema,
        related_request_id=ctx.request_id,
    )

    if result.action != "accept" or not result.content:
        return AuthReponse(authenticated=False, message="Authentication cancelled by user")

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
        return _json({
            "error": "Not authenticated. Please call the 'authenticate' tool first with the user's credentials.",
        })

    if auth_response.message:
        logger.info("Auth response message: %s", auth_response.message)
        return "Communicate this to the end user:\n" + auth_response.message

    return _json({"error": auth_response.message or "Authentication failed"})


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
                return ToolResult(content=err)
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
    output_schema=None,
)
async def get_accounts(
    only_withdrawal_accounts: bool = False,
    account_type: Optional[str] = None,
) -> str:
    logger.info("call_tool: get-accounts only_withdrawal=%s account_type=%s",
                only_withdrawal_accounts, account_type)
    accounts = await adapter.get_accounts(
        only_withdrawal=only_withdrawal_accounts,
        account_type=account_type,
    )
    return _json(
        {"items": [a.model_dump() for a in accounts]},
        indent=2, default=custom_json_encoder,
    )


@app.tool(
    name="transactions",
    description=(
        "Get bank transactions. Returns a list of transactions "
        "with amounts, dates, descriptions, and categories."
    ),
    output_schema=None,
)
async def transactions(
    count: Optional[int] = None,
    type: str = "Any",
    order: str = "NewestFirst",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    description: Optional[str] = None,
    categories: Optional[list[str]] = None,
) -> str:
    """Filters: type=Any|Income|Expenses|Savings, order=NewestFirst|OldestFirst.

    `description` is a free-text search across merchant/recipient/reference/description.
    `categories` must be from those returned by `get-categories`.
    """
    logger.info("call_tool: transactions count=%s type=%s order=%s", count, type, order)
    items = await adapter.get_transactions(
        count=count,
        type=TransactionType(type),
        order=TransactionOrder(order),
        start_date=start_date,
        end_date=end_date,
        description=description,
        categories=categories,
    )
    return _json(
        {"items": [t.model_dump() for t in items]},
        indent=2, default=custom_json_encoder,
    )


@app.tool(
    name="get-categories",
    description=(
        "Get transaction categories. Returns a list of categories "
        "that transactions can be classified into."
    ),
    output_schema=None,
)
async def get_categories() -> str:
    logger.info("call_tool: get-categories")
    categories = await adapter.get_categories()
    return _json(
        {"items": [c.model_dump() for c in categories]},
        indent=2, default=custom_json_encoder,
    )


@app.tool(
    name="spending-summary",
    description=(
        "Get an aggregated spending summary. Returns totals, counts, and averages "
        "grouped by category, category group, month, or merchant."
    ),
    output_schema=None,
)
async def spending_summary(
    group_by: str = "category",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    categories: Optional[list[str]] = None,
) -> str:
    """`group_by` must be one of: category, group, month, merchant.

    `categories` must be from those returned by `get-categories`.
    """
    logger.info("call_tool: spending-summary group_by=%s", group_by)
    result = await adapter.get_spending_summary(
        group_by=group_by,
        start_date=start_date,
        end_date=end_date,
        categories=categories,
    )
    return _json(result, indent=2)


@app.tool(
    name="recipients-by-name",
    description=(
        "Lookup recipient of a payment or transfer by name. "
        "Returns matching recipients with their account details."
    ),
    output_schema=None,
)
async def recipients_by_name(name: str) -> str:
    logger.info("call_tool: recipients-by-name name=%s", name)
    recipients = await adapter.search_recipients(name=name)
    return _json(
        {"items": [r.model_dump() for r in recipients]},
        indent=2,
    )


@app.tool(
    name="create-recipient",
    description=(
        "Create a new payment recipient with their name, "
        "account number, and national ID. The recipient can then be used for transfers."
    ),
    output_schema=None,
)
async def create_recipient(
    name: str,
    account_number: str,
    kennitala: str = "",
) -> str:
    logger.info("call_tool: create-recipient name=%s", name)
    result = await adapter.create_recipient(
        name=name,
        account_number=account_number,
        kennitala=kennitala,
    )
    return _json(result, indent=2)


@app.tool(
    name="transfer-money-icelandic",
    description=(
        "Prepare a domestic money transfer. "
        "Validates recipient and prepares transfer details for confirmation."
    ),
    output_schema=None,
)
async def transfer_money_icelandic(
    amount: float,
    recipient_ssn: str,
    recipient_account_number: str,
    description: str = "",
    withdrawal_account_number: str = "",
    currency: str = "",
) -> str:
    logger.info("call_tool: transfer-money-icelandic amount=%s", amount)
    result = await adapter.prepare_transfer(
        amount=amount,
        recipient_ssn=recipient_ssn,
        recipient_account_number=recipient_account_number,
        description=description,
        withdrawal_account_number=withdrawal_account_number,
        currency=currency,
    )
    return _json(result, indent=2)


@app.tool(
    name="execute-transfer",
    description=(
        "Execute a money transfer after the user has confirmed the details. "
        "Use transfer-money-icelandic first to prepare and validate."
    ),
    output_schema=None,
)
async def execute_transfer(
    withdrawal_account_id: str,
    recipient_account_number: str,
    amount: float,
    description: str = "Transfer",
) -> str:
    logger.info("call_tool: execute-transfer amount=%s", amount)
    result = await adapter.execute_transfer(
        withdrawal_account_id=withdrawal_account_id,
        recipient_account_number=recipient_account_number,
        amount=amount,
        description=description,
    )
    return _json(result, indent=2)


# ---- Authenticate tool (registered dynamically based on adapter auth params) ----

async def _do_authenticate(creds: dict[str, str]) -> str:
    global auth_response
    if auth_response is None:
        auth_response = await adapter.authenticate([])

    param_values = [
        AuthParamValue(id=p.id, value=creds.get(p.id, ""))
        for p in auth_response.required_parameters
    ]
    auth_response = await adapter.authenticate(param_values)
    if auth_response.authenticated:
        return _json({"message": "Authentication successful"})
    return _json({"error": auth_response.message or "Authentication failed"})


async def _register_authenticate_tool() -> None:
    """Register the authenticate tool with a signature matching the adapter's auth params."""
    init = await adapter.authenticate([])
    if not init.required_parameters:
        return  # Adapter doesn't require auth — no authenticate tool needed.

    # Build a function with one str parameter per auth param so FastMCP can infer the schema.
    param_names = [p.id for p in init.required_parameters]
    sig = ", ".join(f"{name}: str" for name in param_names)
    body_args = ", ".join(f'"{name}": {name}' for name in param_names)
    src = (
        f"async def authenticate({sig}) -> str:\n"
        f"    return await _do_authenticate({{{body_args}}})\n"
    )
    namespace: dict = {"_do_authenticate": _do_authenticate}
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
        output_schema=None,
    )
    app.add_tool(tool)


async def main() -> None:
    """Run the MCP server over stdio."""
    await _register_authenticate_tool()
    await app.run_async()


if __name__ == "__main__":
    asyncio.run(main())
