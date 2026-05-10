"""Bank2ai Demo MCP Server.

Reference implementation of the bank2ai MCP spec backed by hardcoded
demo data (see `data.py`). The tool surface is provided by
`bank2ai.register_tools`; this module only supplies handlers.
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from fastmcp import FastMCP

from bank2ai import (
    Account,
    AccountList,
    Category,
    CategoryList,
    CreateRecipientResponse,
    ExecuteTransferDetail,
    ExecuteTransferResponse,
    Recipient,
    RecipientList,
    Transaction,
    TransactionList,
    TransactionsSummary,
    TransactionsSummaryGroup,
    TransactionsSummaryPeriod,
    TransferAction,
    TransferPreparedItem,
    TransferPreparedResponse,
    register_tools,
)

from . import data as demo_data


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("bank2ai-demo")


# ---- Handlers ----

async def get_accounts(
    *,
    only_withdrawal_accounts: bool = False,
    account_type: Optional[str] = None,
    status: Optional[str] = None,
    usage: Optional[str] = None,
) -> AccountList:
    logger.info(
        "get_accounts: only_withdrawal=%s account_type=%s status=%s usage=%s",
        only_withdrawal_accounts, account_type, status, usage,
    )
    accounts = list(demo_data.ACCOUNTS)
    if only_withdrawal_accounts:
        accounts = [a for a in accounts if a.get("isWithdrawalAccount")]
    if account_type:
        accounts = [a for a in accounts if a.get("accountType") == account_type]
    if status:
        accounts = [a for a in accounts if a.get("status") == status]
    if usage:
        accounts = [a for a in accounts if a.get("usage") == usage]
    return AccountList(items=[Account(**a) for a in accounts])


_FULL_ONLY_TRANSACTION_FIELDS = (
    "valueDate",
    "categoryRaw",
    "counterparty",
    "transactionCode",
    "remittanceInformation",
    "endToEndId",
    "merchantCategoryCode",
)
_STANDARD_AND_ABOVE_FIELDS = (
    "status",
    "categoryId",
    "originalCurrency",
    "originalAmount",
)


def _apply_verbosity(t: Transaction, verbosity: str) -> Transaction:
    """Clear optional fields above the requested verbosity cap. The
    Pydantic base class drops None-valued keys on serialization, so
    suppressed fields are simply absent in the wire payload.
    """

    if verbosity == "full":
        return t
    for field in _FULL_ONLY_TRANSACTION_FIELDS:
        setattr(t, field, None)
    if verbosity == "minimal":
        for field in _STANDARD_AND_ABOVE_FIELDS:
            setattr(t, field, None)
    return t


async def get_transactions(
    *,
    count: Optional[int] = None,
    order: str = "NewestFirst",
    verbosity: str = "standard",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    description: Optional[str] = None,
    category_ids: Optional[list[str]] = None,
    account_ids: Optional[list[str]] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    cursor: Optional[str] = None,
) -> TransactionList:
    logger.info(
        "get_transactions: count=%s order=%s verbosity=%s account_ids=%s cursor=%s",
        count, order, verbosity, account_ids, cursor,
    )
    transactions = list(demo_data.TRANSACTIONS)

    if account_ids:
        wanted = set(account_ids)
        transactions = [t for t in transactions if t.get("accountId") in wanted]

    if start_date:
        transactions = [t for t in transactions if t["bookingDate"] >= start_date]
    if end_date:
        transactions = [t for t in transactions if t["bookingDate"] <= end_date]

    if min_amount is not None:
        transactions = [t for t in transactions if t["amount"] >= min_amount]
    if max_amount is not None:
        transactions = [t for t in transactions if t["amount"] <= max_amount]

    if category_ids:
        wanted_cats = set(category_ids)
        transactions = [
            t for t in transactions if t.get("categoryId") in wanted_cats
        ]

    if description:
        search = description.lower()
        transactions = [t for t in transactions if search in t["description"].lower()]

    transactions.sort(
        key=lambda t: t["bookingDate"],
        reverse=(order == "NewestFirst"),
    )

    try:
        offset = max(int(cursor), 0) if cursor else 0
    except ValueError:
        offset = 0

    if offset:
        transactions = transactions[offset:]

    next_cursor: Optional[str] = None
    if count is not None and len(transactions) > count:
        next_cursor = str(offset + count)
        transactions = transactions[:count]

    return TransactionList(
        items=[_apply_verbosity(Transaction(**t), verbosity) for t in transactions],
        nextCursor=next_cursor,
    )


async def get_categories() -> CategoryList:
    logger.info("get_categories")
    return CategoryList(items=[Category(**c) for c in demo_data.CATEGORIES])


async def get_transactions_summary(
    *,
    direction: str,
    group_by: str = "category",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category_ids: Optional[list[str]] = None,
    account_ids: Optional[list[str]] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
) -> TransactionsSummary:
    logger.info(
        "get_transactions_summary: direction=%s group_by=%s account_ids=%s",
        direction, group_by, account_ids,
    )
    transactions = list(demo_data.TRANSACTIONS)

    if account_ids:
        wanted = set(account_ids)
        transactions = [t for t in transactions if t.get("accountId") in wanted]

    if direction == "Expenses":
        transactions = [t for t in transactions if t["amount"] < 0]
    else:
        transactions = [t for t in transactions if t["amount"] > 0]

    if min_amount is not None:
        transactions = [t for t in transactions if t["amount"] >= min_amount]
    if max_amount is not None:
        transactions = [t for t in transactions if t["amount"] <= max_amount]

    if start_date:
        transactions = [t for t in transactions if t["bookingDate"] >= start_date]
    if end_date:
        transactions = [t for t in transactions if t["bookingDate"] <= end_date]
    if category_ids:
        wanted_cats = set(category_ids)
        transactions = [
            t for t in transactions if t.get("categoryId") in wanted_cats
        ]

    def grouping_key(t: dict) -> tuple[Optional[str], Optional[str]]:
        cat = t.get("categoryId")
        month = str(t["bookingDate"])[:7]
        if group_by == "category":
            return (cat, None)
        if group_by == "month":
            return (None, month)
        if group_by == "both":
            return (cat, month)
        return (None, None)

    groups: dict[tuple[Optional[str], Optional[str]], dict[str, float]] = defaultdict(
        lambda: {"total": 0, "count": 0}
    )
    for t in transactions:
        key = grouping_key(t)
        groups[key]["total"] += t["amount"]
        groups[key]["count"] += 1

    summary = [
        TransactionsSummaryGroup(
            categoryId=cat,
            month=month,
            totalAmount=stats["total"],
            transactionCount=int(stats["count"]),
            averageAmount=stats["total"] / stats["count"] if stats["count"] > 0 else 0,
        )
        for (cat, month), stats in groups.items()
    ]
    summary.sort(key=lambda g: g.totalAmount)

    return TransactionsSummary(
        summary=summary,
        period=TransactionsSummaryPeriod(
            startDate=start_date or "all",
            endDate=end_date or "all",
        ),
        total=sum(g.totalAmount for g in summary),
    )


async def get_recipients(*, name: str) -> RecipientList:
    logger.info("get_recipients: name=%s", name)
    search = name.lower()
    return RecipientList(
        items=[Recipient(**r) for r in demo_data.RECIPIENTS if search in r["name"].lower()],
    )


async def create_recipient(
    *,
    name: str,
    account_number: str,
    kennitala: str = "",
) -> CreateRecipientResponse:
    logger.info("create_recipient: name=%s", name)
    recipient = Recipient(
        id=f"rcpt_{len(demo_data.RECIPIENTS) + 1:03d}",
        name=name,
        accountNumber=account_number,
        socialSecurityNumber=kennitala,
        accountNumberType="Domestic",
        bankInfo="Demo Bank",
        paymentType="Domestic",
        isFavorite=False,
    )
    return CreateRecipientResponse(
        content=f"Recipient '{name}' created successfully.",
        item=recipient,
    )


async def prepare_transfer_icelandic(
    *,
    amount: float,
    recipient_ssn: str,
    recipient_account_number: str,
    description: str = "",
    withdrawal_account_number: str = "",
    currency: str = "",
) -> TransferPreparedResponse:
    logger.info("prepare_transfer_icelandic: amount=%s", amount)
    recipient_data = next(
        (r for r in demo_data.RECIPIENTS if r["socialSecurityNumber"] == recipient_ssn),
        None,
    )
    if not recipient_data:
        return TransferPreparedResponse(content="Invalid social security number.")

    if withdrawal_account_number:
        account_data = next(
            (a for a in demo_data.ACCOUNTS if a["accountNumber"] == withdrawal_account_number),
            None,
        )
    else:
        account_data = next((a for a in demo_data.ACCOUNTS if a["isDefaultAccount"]), None)

    if not account_data:
        return TransferPreparedResponse(content="Invalid or no default account found.")

    if account_data["availableBalance"] < amount:
        return TransferPreparedResponse(content="Insufficient funds.")

    account = Account(**account_data)
    return TransferPreparedResponse(
        content="A transfer has been prepared. Please confirm the details with the user before calling execute-transfer.",
        item=TransferPreparedItem(
            amount=amount,
            description=description,
            currency=currency or account.currency,
            recipient_account_number=recipient_account_number,
            recipient_ssn=recipient_ssn,
            recipient_name=recipient_data["name"],
            withdrawal_account_id=account.id,
            withdrawal_account=account,
        ),
        actions=[TransferAction(title="Transfer", link="/transfer")],
    )


async def execute_transfer(
    *,
    withdrawal_account_id: str,
    recipient_account_number: str,
    amount: float,
    description: str = "Transfer",
) -> ExecuteTransferResponse:
    logger.info("execute_transfer: amount=%s", amount)
    return ExecuteTransferResponse(
        content=f"Transfer of {amount:,.2f} completed successfully.",
        item=ExecuteTransferDetail(
            transfer_id=f"txfr_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            status="completed",
            timestamp=datetime.now().isoformat(),
        ),
    )


# ---- Wire up ----

app = FastMCP("bank2ai-demo")

register_tools(
    app,
    get_accounts=get_accounts,
    get_transactions=get_transactions,
    get_categories=get_categories,
    get_transactions_summary=get_transactions_summary,
    get_recipients=get_recipients,
    create_recipient=create_recipient,
    prepare_transfer_icelandic=prepare_transfer_icelandic,
    execute_transfer=execute_transfer,
)


async def main() -> None:
    await app.run_async()


def main_sync() -> None:
    """Entry-point for the ``bank2ai-demo`` console script."""
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()
