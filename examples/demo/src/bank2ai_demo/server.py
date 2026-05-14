"""Bank2ai Demo MCP Server.

Reference implementation of the bank2ai MCP spec backed by hardcoded
demo data (see `data.py`). The tool surface is provided by
`bank2ai.register_tools`; this module only supplies handlers.
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from dotenv import load_dotenv
from fastmcp import FastMCP

from bank2ai import (
    Account,
    AccountList,
    Category,
    CategoryList,
    CreateRecipientResponse,
    ExecuteTransferResponse,
    ExecutedTransfer,
    GetTransactionResponse,
    Party,
    PrepareTransferResponse,
    PreparedTransfer,
    Rail,
    Recipient,
    RecipientList,
    RemittanceInformation,
    Transaction,
    TransactionList,
    TransactionsSummary,
    TransactionsSummaryGroup,
    TransactionsSummaryPeriod,
    TransferAction,
    TransferExecutionStatus,
    TransferSummary,
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
    "transactionCode",
    "proprietaryBankTransactionCode",
    "remittanceInformation",
    "endToEndId",
    "mandateId",
    "creditorId",
    "purposeCode",
    "entryReference",
    "additionalInformation",
)
_STANDARD_AND_ABOVE_FIELDS = (
    "status",
    "categoryId",
    "originalCurrency",
    "originalAmount",
    "transactionDate",
    "maskedPan",
    "merchantCategoryCode",
    "counterparty",
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
        transactions = [t for t in transactions if t["date"] >= start_date]
    if end_date:
        transactions = [t for t in transactions if t["date"] <= end_date]

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
        key=lambda t: t["date"],
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


async def get_transaction(
    *,
    transaction_id: str,
    account_id: Optional[str] = None,
) -> GetTransactionResponse:
    logger.info("get_transaction: id=%s account_id=%s", transaction_id, account_id)
    record = next(
        (t for t in demo_data.TRANSACTIONS if t.get("id") == transaction_id),
        None,
    )
    if record is None:
        return GetTransactionResponse(
            content=f"No transaction with id '{transaction_id}'.",
        )
    if account_id is not None and record.get("accountId") != account_id:
        return GetTransactionResponse(
            content=f"Transaction '{transaction_id}' is not on account '{account_id}'.",
        )
    return GetTransactionResponse(
        content="Transaction found.",
        item=Transaction(**record),
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
        transactions = [t for t in transactions if t["date"] >= start_date]
    if end_date:
        transactions = [t for t in transactions if t["date"] <= end_date]
    if category_ids:
        wanted_cats = set(category_ids)
        transactions = [
            t for t in transactions if t.get("categoryId") in wanted_cats
        ]

    def grouping_key(t: dict) -> tuple[Optional[str], Optional[str]]:
        cat = t.get("categoryId")
        month = str(t["date"])[:7]
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
    account_identifier: dict,
    national_id: Optional[dict] = None,
    nickname: Optional[str] = None,
    bic: Optional[str] = None,
    default_description: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> CreateRecipientResponse:
    logger.info("create_recipient: name=%s idempotency_key=%s", name, idempotency_key)
    if (cached := _idempotent_get("create-recipient", idempotency_key)) is not None:
        return cached  # type: ignore[return-value]
    recipient = Recipient(
        id=f"rcpt_{len(demo_data.RECIPIENTS) + 1:03d}",
        name=name,
        accountIdentifier=account_identifier,
        nationalId=national_id,
        nickname=nickname,
        bic=bic,
        defaultDescription=default_description,
    )
    response = CreateRecipientResponse(
        content=f"Recipient '{name}' created successfully.",
        item=recipient,
    )
    _idempotent_put("create-recipient", idempotency_key, response)
    return response


# ---- Transfer intent store ----
#
# In-memory mapping from `transferIntentId` to the prepared transfer.
# A real bank persists this in a short-lived store; the demo keeps it
# in-process and lets entries lapse silently when the server restarts.

_INTENT_TTL = timedelta(minutes=5)
_intent_store: dict[str, PreparedTransfer] = {}


# ---- Idempotency cache ----
#
# Scoped per (tool name, idempotency_key) so different tools can't
# collide on the same key. A real bank persists this with a 24h+ TTL;
# the demo keeps it in-process.

_idempotency_cache: dict[tuple[str, str], object] = {}


def _idempotent_get(tool: str, key: Optional[str]) -> Optional[object]:
    if key is None:
        return None
    return _idempotency_cache.get((tool, key))


def _idempotent_put(tool: str, key: Optional[str], response: object) -> None:
    if key is not None:
        _idempotency_cache[(tool, key)] = response


async def prepare_transfer(
    *,
    debtor_account_id: str,
    creditor: dict,
    amount: float,
    currency: str,
    rail: str,
    local_instrument: Optional[str] = None,
    requested_execution_date: Optional[str] = None,
    remittance_information: Optional[dict] = None,
    end_to_end_id: Optional[str] = None,
    description: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> PrepareTransferResponse:
    logger.info(
        "prepare_transfer: rail=%s amount=%s currency=%s debtor=%s idempotency_key=%s",
        rail, amount, currency, debtor_account_id, idempotency_key,
    )
    if (cached := _idempotent_get("prepare-transfer", idempotency_key)) is not None:
        return cached  # type: ignore[return-value]

    creditor_party = Party.model_validate(creditor)
    if creditor_party.accountIdentifier is None:
        return PrepareTransferResponse(
            content="creditor.accountIdentifier is required for routing.",
            code="missing_creditor_identifier",
        )

    account_data = next(
        (a for a in demo_data.ACCOUNTS if a["id"] == debtor_account_id),
        None,
    )
    if account_data is None:
        return PrepareTransferResponse(
            content=f"No debtor account with id '{debtor_account_id}'.",
            code="invalid_account",
        )
    if account_data.get("availableBalance", 0) < amount:
        return PrepareTransferResponse(
            content="Insufficient funds.",
            code="insufficient_funds",
        )

    debtor_account = Account(**account_data)
    resolved_end_to_end_id = end_to_end_id or f"e2e_{uuid4().hex[:16]}"
    intent_id = f"intent_{uuid4().hex}"
    now = datetime.now(timezone.utc)

    summary = TransferSummary(
        debtorAccount=debtor_account,
        creditor=creditor_party,
        amount=amount,
        currency=currency,
        rail=Rail(rail),
        localInstrument=local_instrument,
        requestedExecutionDate=requested_execution_date,
        remittanceInformation=(
            RemittanceInformation.model_validate(remittance_information)
            if remittance_information
            else None
        ),
        endToEndId=resolved_end_to_end_id,
        description=description,
    )
    prepared = PreparedTransfer(
        transferIntentId=intent_id,
        expiresAt=now + _INTENT_TTL,
        summary=summary,
    )
    _intent_store[intent_id] = prepared

    response = PrepareTransferResponse(
        content=(
            "A transfer has been prepared. Confirm the details with the "
            "user, then call execute-transfer with the transferIntentId."
        ),
        item=prepared,
        actions=[TransferAction(title="Transfer", link="/transfer")],
    )
    _idempotent_put("prepare-transfer", idempotency_key, response)
    return response


async def execute_transfer(
    *,
    transfer_intent_id: str,
    idempotency_key: Optional[str] = None,
) -> ExecuteTransferResponse:
    logger.info(
        "execute_transfer: intent=%s idempotency_key=%s",
        transfer_intent_id, idempotency_key,
    )
    if (cached := _idempotent_get("execute-transfer", idempotency_key)) is not None:
        return cached  # type: ignore[return-value]

    intent = _intent_store.get(transfer_intent_id)
    if intent is None:
        return ExecuteTransferResponse(
            content=f"No such transfer intent '{transfer_intent_id}'.",
            code="intent_not_found",
        )
    now = datetime.now(timezone.utc)
    if now >= intent.expiresAt:
        return ExecuteTransferResponse(
            content=(
                f"Transfer intent '{transfer_intent_id}' expired at "
                f"{intent.expiresAt.isoformat()}. Call prepare-transfer again."
            ),
            code="intent_expired",
        )
    response = ExecuteTransferResponse(
        content=(
            f"Transfer of {intent.summary.amount:,.2f} {intent.summary.currency} "
            "completed successfully."
        ),
        item=ExecutedTransfer(
            transactionId=f"tx_{uuid4().hex[:12]}",
            status=TransferExecutionStatus.Settled,
            executedAt=now,
        ),
    )
    _idempotent_put("execute-transfer", idempotency_key, response)
    return response


# ---- Wire up ----

app = FastMCP("bank2ai-demo")

register_tools(
    app,
    get_accounts=get_accounts,
    get_transactions=get_transactions,
    get_transaction=get_transaction,
    get_categories=get_categories,
    get_transactions_summary=get_transactions_summary,
    get_recipients=get_recipients,
    create_recipient=create_recipient,
    prepare_transfer=prepare_transfer,
    execute_transfer=execute_transfer,
)


async def main() -> None:
    await app.run_async()


def main_sync() -> None:
    """Entry-point for the ``bank2ai-demo`` console script."""
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()
