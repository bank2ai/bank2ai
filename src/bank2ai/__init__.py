"""bank2ai — helpers for banks building MCP servers.

The library exposes:

* a Pydantic data model layer (`bank2ai.models`) shared by every Bank2AI
  MCP server, and
* a reusable MCP tool surface (`bank2ai.mcp`) — `register_tools` — so each
  bank only has to supply async handlers backed by their own APIs.
"""

from .mcp import (
    Handler,
    register_tools,
)
from .models import (
    Account,
    AccountType,
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
    "Account",
    "AccountType",
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
    "register_tools",
]
