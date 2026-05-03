"""bank2ai — helpers for banks building MCP servers.

The library exposes:

* a Pydantic data model layer (`bank2ai.models`) shared by every Bank2AI
  MCP server, and
* a reusable MCP tool surface (`bank2ai.mcp`) — `register_tools` plus the
  optional auth middleware and dynamic `authenticate` tool — so each bank
  only has to supply async handlers backed by their own APIs.
"""

from .mcp import (
    AUTHENTICATE_TOOL_NAME,
    AuthState,
    AuthenticateHandler,
    Handler,
    make_auth_middleware,
    register_authenticate_tool,
    register_tools,
)
from .models import (
    Account,
    AccountType,
    AuthenticateResponse,
    AuthParam,
    AuthParamType,
    AuthParamValue,
    AuthResponse,
    Category,
    CreateRecipientResponse,
    ExecuteTransferDetail,
    ExecuteTransferResponse,
    Recipient,
    RecipientInfo,
    SpendingSummary,
    SpendingSummaryGroup,
    SpendingSummaryPeriod,
    Transaction,
    TransactionOrder,
    TransactionType,
    TransferAction,
    TransferPreparedItem,
    TransferPreparedResponse,
)

__all__ = [
    "AUTHENTICATE_TOOL_NAME",
    "Account",
    "AccountType",
    "AuthParam",
    "AuthParamType",
    "AuthParamValue",
    "AuthResponse",
    "AuthState",
    "AuthenticateHandler",
    "AuthenticateResponse",
    "Category",
    "CreateRecipientResponse",
    "ExecuteTransferDetail",
    "ExecuteTransferResponse",
    "Handler",
    "Recipient",
    "RecipientInfo",
    "SpendingSummary",
    "SpendingSummaryGroup",
    "SpendingSummaryPeriod",
    "Transaction",
    "TransactionOrder",
    "TransactionType",
    "TransferAction",
    "TransferPreparedItem",
    "TransferPreparedResponse",
    "make_auth_middleware",
    "register_authenticate_tool",
    "register_tools",
]
