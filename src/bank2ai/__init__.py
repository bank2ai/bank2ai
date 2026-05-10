"""bank2ai, helpers for banks building MCP servers.

The library exposes:

* a Pydantic data model layer (`bank2ai.models`) shared by every bank2ai
  MCP server, and
* a reusable MCP tool surface (`bank2ai.tools`) (`register_tools`) so each
  bank only has to supply async handlers backed by their own APIs.
"""

from .tools import (
    Handler,
    register_tools,
)
from .models import (
    Account,
    AccountList,
    AccountStatus,
    AccountType,
    AccountUsage,
    Category,
    CategoryList,
    CreateRecipientResponse,
    ExecuteTransferDetail,
    ExecuteTransferResponse,
    Recipient,
    RecipientInfo,
    RecipientList,
    Transaction,
    TransactionDirection,
    TransactionList,
    TransactionOrder,
    TransactionStatus,
    TransactionsSummary,
    TransactionsSummaryGroup,
    TransactionsSummaryPeriod,
    TransferAction,
    TransferPreparedItem,
    TransferPreparedResponse,
)

__all__ = [
    "Account",
    "AccountList",
    "AccountStatus",
    "AccountType",
    "AccountUsage",
    "Category",
    "CategoryList",
    "CreateRecipientResponse",
    "ExecuteTransferDetail",
    "ExecuteTransferResponse",
    "Handler",
    "Recipient",
    "RecipientInfo",
    "RecipientList",
    "Transaction",
    "TransactionDirection",
    "TransactionList",
    "TransactionOrder",
    "TransactionStatus",
    "TransactionsSummary",
    "TransactionsSummaryGroup",
    "TransactionsSummaryPeriod",
    "TransferAction",
    "TransferPreparedItem",
    "TransferPreparedResponse",
    "register_tools",
]
