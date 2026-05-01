"""Bank2AI Demo MCP Server

A reference implementation of the Bank2AI specification using hardcoded test data.
This server demonstrates how to implement the Bank2AI tools using the MCP SDK.
"""

import asyncio
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from mcp.server import Server
from mcp.types import Tool, TextContent, ClientCapabilities, ElicitationCapability, FormElicitationCapability

from adapters import get_adapter
from adapters.models import AuthParamValue, AuthReponse, AuthParamType, AuthParam, TransactionType, TransactionOrder, custom_json_encoder

def _json(obj, **kwargs):
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

# Initialize MCP server and bank adapter
app = Server("bank2ai-demo")
adapter = get_adapter(logger)
auth_response: AuthReponse | None = None


async def _build_elicit_schema(auth_parameters : list[AuthParam]) -> dict:
    """Build a JSON Schema for elicitation from the adapter's auth params."""
    auth_response = await adapter.authenticate([])
    if not auth_response.required_parameters:
        return None
    
    properties = {}
    required = []
    for param in auth_response.required_parameters:
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


def _client_supports_elicitation() -> bool:
    """Check if the connected client supports elicitation."""
    session = app.request_context.session
    client_caps = session.client_params.capabilities if session.client_params else None
    logger.info("Client capabilities: %s", client_caps)
    if client_caps and client_caps.elicitation:
        logger.info("Client elicitation capability: %s", client_caps.elicitation)
        return True
    return False


async def _authenticate_with_elicitation() -> AuthReponse:
    """Use MCP elicitation to collect credentials from the user, then authenticate."""
    session = app.request_context.session
    schema = _build_elicit_schema()
    logger.info("Elicitation schema: %s", json.dumps(schema))

    result = await session.elicit_form(
        message="Please provide your banking credentials to continue.",
        requestedSchema=schema,
        related_request_id=app.request_context.request_id,
    )

    if result.action != "accept" or not result.content:
        return AuthReponse(authenticated=False, message="Authentication cancelled by user")

    param_values = [
        AuthParamValue(id=key, value=str(value))
        for key, value in result.content.items()
        if value is not None
    ]
    return await adapter.authenticate(param_values)


async def _build_authenticate_tool() -> Tool | None:
    """Build an authenticate tool dynamically from the adapter's auth params.

    Returns None if the adapter doesn't require authentication.
    """
    auth_response = await adapter.authenticate([])
    if not auth_response.required_parameters:
        return None

    properties = {}
    required = []
    for param in auth_response.required_parameters:
        properties[param.id] = {
            "type": "string",
            "description": param.title,
        }
        required.append(param.id)

    return Tool(
        name="authenticate",
        description=(
            "Authenticate with the bank. This must be called before any other "
            "tool if the server is not already authenticated. Ask the user for "
            "the required credentials."
        ),
        inputSchema={
            "type": "object",
            "properties": properties,
            "required": required,
        },
    )


# Tool definitions matching Bank2AI specification

TOOL_GET_ACCOUNTS = Tool(
    name="get-accounts",
    description=(
        "Get bank accounts and cards. Returns a list of accounts "
        "with balances, account numbers, and types."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "only_withdrawal_accounts": {
                "type": "boolean",
                "description": "Filter to only withdrawal-capable accounts",
                "default": False,
            },
            "account_type": {
                "type": "string",
                "description": "Filter by account type",
                "enum": ["Current", "Savings", "Credit"],
            },
        },
        "required": [],
    },
)

TOOL_TRANSACTIONS = Tool(
    name="transactions",
    description=(
        "Get bank transactions. Returns a list of transactions "
        "with amounts, dates, descriptions, and categories."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "count": {
                "type": "integer",
                "description": "Maximum number of transactions to return",
            },
            "type": {
                "type": "string",
                "description": "Transaction type filter",
                "enum": ["Any", "Income", "Expenses", "Savings"],
                "default": "Any",
            },
            "order": {
                "type": "string",
                "description": "Sort order for transactions",
                "enum": ["NewestFirst", "OldestFirst"],
                "default": "NewestFirst",
            },
            "start_date": {
                "type": "string",
                "description": "Start date filter (ISO format: YYYY-MM-DD)",
            },
            "end_date": {
                "type": "string",
                "description": "End date filter (ISO format: YYYY-MM-DD)",
            },
            "description": {
                "type": "string",
                "description": "Search text to filter transactions by description. This can be merchant name, recipient name, transaction reference, or any text in the transaction description.",
            },
            "categories": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Filter transactions by category names. Categories must be from those returned by the get-categories tool.",
            },
        },
        "required": [],
    },
)

TOOL_GET_CATEGORIES = Tool(
    name="get-categories",
    description=(
        "Get transaction categories. Returns a list of categories "
        "that transactions can be classified into."
    ),
    inputSchema={
        "type": "object",
        "properties": {},
        "required": [],
    },
)

TOOL_SPENDING_SUMMARY = Tool(
    name="spending-summary",
    description=(
        "Get an aggregated spending summary. Returns totals, counts, and averages "
        "grouped by category, category group, month, or merchant."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "group_by": {
                "type": "string",
                "description": "How to group the spending data",
                "enum": ["category", "group", "month", "merchant"],
                "default": "category",
            },
            "start_date": {
                "type": "string",
                "description": "Start date filter (ISO format: YYYY-MM-DD)",
            },
            "end_date": {
                "type": "string",
                "description": "End date filter (ISO format: YYYY-MM-DD)",
            },
            "categories": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Filter spending summary by category names. Categories must be from those returned by the get-categories tool.",
            },
        },
        "required": [],
    },
)

TOOL_RECIPIENTS_BY_NAME = Tool(
    name="recipients-by-name",
    description=(
        "Lookup recipient of a payment or transfer by name. "
        "Returns matching recipients with their account details."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name to search for",
            },
        },
        "required": ["name"],
    },
)

TOOL_CREATE_RECIPIENT = Tool(
    name="create-recipient",
    description=(
        "Create a new payment recipient with their name, "
        "account number, and national ID. The recipient can then be used for transfers."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Recipient's full name",
            },
            "account_number": {
                "type": "string",
                "description": "Recipient's bank account number",
            },
            "kennitala": {
                "type": "string",
                "description": "Recipient's national ID",
                "default": "",
            },
        },
        "required": ["name", "account_number"],
    },
)

TOOL_TRANSFER_MONEY = Tool(
    name="transfer-money-icelandic",
    description=(
        "Prepare a domestic money transfer. "
        "Validates recipient and prepares transfer details for confirmation."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "amount": {
                "type": "number",
                "description": "Amount to transfer",
            },
            "recipient_ssn": {
                "type": "string",
                "description": "Recipient's social security number",
            },
            "recipient_account_number": {
                "type": "string",
                "description": "Recipient's bank account number",
            },
            "description": {
                "type": "string",
                "description": "Transfer description/reference",
                "default": "",
            },
            "withdrawal_account_number": {
                "type": "string",
                "description": "Account to withdraw from (uses default if not specified)",
                "default": "",
            },
            "currency": {
                "type": "string",
                "description": "Currency code",
                "default": "",
            },
        },
        "required": ["amount", "recipient_ssn", "recipient_account_number"],
    },
)

TOOL_EXECUTE_TRANSFER = Tool(
    name="execute-transfer",
    description=(
        "Execute a money transfer after the user has confirmed the details. "
        "Use transfer-money-icelandic first to prepare and validate."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "withdrawal_account_id": {
                "type": "string",
                "description": "Source account ID to withdraw from",
            },
            "recipient_account_number": {
                "type": "string",
                "description": "Destination account number",
            },
            "amount": {
                "type": "number",
                "description": "Amount to transfer",
            },
            "description": {
                "type": "string",
                "description": "Transfer description/reference",
                "default": "Transfer",
            },
        },
        "required": ["withdrawal_account_id", "recipient_account_number", "amount"],
    },
)


# Tool handlers

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    logger.info("list_tools called")
    tools = [
        TOOL_GET_ACCOUNTS,
        TOOL_TRANSACTIONS,
        TOOL_GET_CATEGORIES,
        TOOL_SPENDING_SUMMARY,
        TOOL_RECIPIENTS_BY_NAME,
        TOOL_CREATE_RECIPIENT,
        TOOL_TRANSFER_MONEY,
        TOOL_EXECUTE_TRANSFER,
    ]
    auth_tool = await _build_authenticate_tool()
    if auth_tool:
        tools.insert(0, auth_tool)
    return tools


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls by delegating to the configured bank adapter.

    Authentication priority:
    1. If client supports MCP elicitation — collect credentials via elicit_form()
    2. If adapter exposes auth params — an 'authenticate' tool is available for the
       LLM to call with credentials collected conversationally from the user
    3. If no auth params needed (e.g. demo adapter) — authenticate immediately
    """    
    global auth_response

    logger.info("call_tool: %s args=%s", name, json.dumps(arguments))

    try:
        result = await _dispatch_tool(name, arguments)

    except Exception as e:
        logger.info("Problem when calling tool, try again after re-authentication: %s", e)
        auth_response = None  # Reset auth on any error to force re-authentication
        result = await _dispatch_tool(name, arguments)

    if _log_responses:
        for content in result:
            logger.info("call_tool response: %s text=%s", name, content.text)
    return result    


async def _dispatch_tool(name: str, arguments: dict) -> list[TextContent]:
    """Dispatch a tool call to the appropriate adapter method."""
    global auth_response

    # Auto-authenticate on first data tool call
    if auth_response is None:
        auth_response = await adapter.authenticate([])

    # Handle the authenticate tool
    if name == "authenticate":
        param_values = [
            AuthParamValue(id=p.id, value=arguments.get(p.id, ""))
            for p in auth_response.required_parameters
        ]
        auth_response = await adapter.authenticate(param_values)
        if auth_response.authenticated:
            return [TextContent(type="text", text=_json({
                "message": "Authentication successful",
            }))]
        else:
            return [TextContent(type="text", text=_json({
                "error": auth_response.message or "Authentication failed",
            }))]
    
    if not auth_response.authenticated:
        if auth_response.required_parameters and _client_supports_elicitation():
            logger.info("Client supports elicitation, collecting credentials interactively")
            auth_response = await _authenticate_with_elicitation()
        elif auth_response.required_parameters:
            logger.info("Not authenticated, directing LLM to use authenticate tool")
            return [TextContent(type="text", text=_json({
                "error": "Not authenticated. Please call the 'authenticate' tool first with the user's credentials.",
            }))]
        
        if auth_response.message:
            logger.info("Auth response message: %s", auth_response.message)
            return [TextContent(
                type="text",
                text="Communicate this to the end user:\n" + auth_response.message,
            )]

        if not auth_response.authenticated:
            return [TextContent(
                type="text",
                text=_json({"error": auth_response.message or "Authentication failed"}),
            )]

    if name == "get-accounts":
        accounts = await adapter.get_accounts(
            only_withdrawal=arguments.get("only_withdrawal_accounts", False),
            account_type=arguments.get("account_type"),
        )
        return [TextContent(
            type="text",
            text=_json(
                {"items": [a.model_dump() for a in accounts]},
                indent=2, default=custom_json_encoder,
            ),
        )]

    elif name == "transactions":
        transactions = await adapter.get_transactions(
            count=arguments.get("count"),
            type=TransactionType(arguments.get("type", "Any")),
            order=TransactionOrder(arguments.get("order", "NewestFirst")),
            start_date=arguments.get("start_date"),
            end_date=arguments.get("end_date"),
            description=arguments.get("description"),
            categories=arguments.get("categories"),
        )
        return [TextContent(
            type="text",
            text=_json(
                {"items": [t.model_dump() for t in transactions]},
                indent=2, default=custom_json_encoder,
            ),
        )]

    elif name == "get-categories":
        categories = await adapter.get_categories()
        return [TextContent(
            type="text",
            text=_json(
                {"items": [c.model_dump() for c in categories]},
                indent=2, default=custom_json_encoder,
            ),
        )]

    elif name == "spending-summary":
        result = await adapter.get_spending_summary(
            group_by=arguments.get("group_by", "category"),
            start_date=arguments.get("start_date"),
            end_date=arguments.get("end_date"),
            categories=arguments.get("categories"),
        )
        return [TextContent(type="text", text=_json(result, indent=2))]

    elif name == "recipients-by-name":
        recipients = await adapter.search_recipients(name=arguments["name"])
        return [TextContent(
            type="text",
            text=_json(
                {"items": [r.model_dump() for r in recipients]},
                indent=2,
            ),
        )]

    elif name == "create-recipient":
        result = await adapter.create_recipient(
            name=arguments["name"],
            account_number=arguments["account_number"],
            kennitala=arguments.get("kennitala", ""),
        )
        return [TextContent(type="text", text=_json(result, indent=2))]

    elif name == "transfer-money-icelandic":
        result = await adapter.prepare_transfer(
            amount=arguments["amount"],
            recipient_ssn=arguments["recipient_ssn"],
            recipient_account_number=arguments["recipient_account_number"],
            description=arguments.get("description", ""),
            withdrawal_account_number=arguments.get("withdrawal_account_number", ""),
            currency=arguments.get("currency", ""),
        )
        return [TextContent(type="text", text=_json(result, indent=2))]

    elif name == "execute-transfer":
        result = await adapter.execute_transfer(
            withdrawal_account_id=arguments["withdrawal_account_id"],
            recipient_account_number=arguments["recipient_account_number"],
            amount=arguments["amount"],
            description=arguments.get("description", "Transfer"),
        )
        return [TextContent(type="text", text=_json(result, indent=2))]

    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
