"""Bank2ai MCP server backed by Meniga APIs.

Required environment variables:
    BANK2AI_MENIGA_BASE_URL: Base URL for the Meniga API
        (e.g. https://api.meniga.cloud/user/core)

Optional environment variables:
    BANK2AI_MENIGA_EMAIL: Email; if set, used as the default credential
    BANK2AI_MENIGA_PASSWORD: Password; if set, used as the default credential
    BANK2AI_MENIGA_CULTURE: Locale (default: en-GB)
"""

import asyncio
import logging
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import httpx
import jwt
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token, get_context

from bank2ai import (
    Account,
    AccountList,
    AccountStatus,
    AccountType,
    Category,
    CategoryList,
    CreateRecipientResponse,
    ExecuteTransferResponse,
    ExecutedTransfer,
    GetTransactionResponse,
    Party,
    PostalAddress,
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


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("bank2ai-meniga")

_BASE_URL = os.environ["BANK2AI_MENIGA_BASE_URL"].rstrip("/")
_DEFAULT_EMAIL = os.environ.get("BANK2AI_MENIGA_EMAIL", "")
_DEFAULT_PASSWORD = os.environ.get("BANK2AI_MENIGA_PASSWORD", "")
_DEFAULT_CULTURE = os.environ.get("BANK2AI_MENIGA_CULTURE", "en-GB")


# ---- Per-server state ----

_culture: str = _DEFAULT_CULTURE
_categories_cache: list[Category] = []
_recipients_store: list[Recipient] = []


_TOKEN_REFRESH_LEEWAY_SECONDS = 60


def _token_expired_or_expiring(token: str) -> bool:
    """Return True if `token` is un-parseable, expired, or expires within the leeway."""
    try:
        claims = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError:
        return True
    exp = claims.get("exp")
    if exp is None:
        return False
    return time.time() >= exp - _TOKEN_REFRESH_LEEWAY_SECONDS


async def _client() -> httpx.AsyncClient:
    headers: dict[str, str] = {}
    token: Optional[str] = None
    access_token = get_access_token()
    if access_token is not None:
        token = access_token.token
    else:
        token = await authenticate()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.AsyncClient(headers=headers, timeout=30.0)


# ---- Auth handler ----

async def authenticate() -> Optional[str]:
    context = get_context()
    token = await context.get_state("meniga_token")
    if token:
        if _token_expired_or_expiring(token):
            logger.info("Cached Meniga token expired or expiring; re-authenticating")
        else:
            return token

    email = _DEFAULT_EMAIL
    password = _DEFAULT_PASSWORD

    if not email or not password:
        logger.warning("Missing email or password in authentication parameters")
        return None

    logger.info("Authenticating with Meniga API at %s", _BASE_URL)
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{_BASE_URL}/v1/authentication",
            json={"email": email, "password": password},
        )
        logger.info("Auth response status: %d", response.status_code)
        if response.status_code in (400, 401):
            logger.error("Authentication failed: %d %s", response.status_code, response.text)
            return None
        response.raise_for_status()
        data = response.json()
        token = data["data"]["accessToken"]
        await context.set_state("meniga_token", token)
        return token


# ---- bank2ai tool handlers ----

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

    params: dict[str, str] = {}

    if status != AccountStatus.Enabled:
        params["includeDisabled"] = True
        params["includeHidden"] = True

    async with await _client() as client:
        response = await client.get(f"{_BASE_URL}/v1/accounts", params=params)
    response.raise_for_status()

    accounts: list[Account] = []
    for acc in response.json()["data"]:
        category = acc.get("accountCategory")
        if category == "Credit":
            # Statement-cycle fields (statementBalance, minimumPaymentDue,
            # paymentDueDate, statementClosingDate) aren't on /v1/accounts;
            # they need a separate Meniga endpoint and stay omitted for now.
            at, is_withdrawal = AccountType.Credit, False
        elif category == "Savings":
            at, is_withdrawal = AccountType.Savings, True
        elif category == "Current":
            at, is_withdrawal = AccountType.Current, True
        else:
            continue

        if acc.get("isHidden"):
            st = AccountStatus.Deleted
        elif acc.get("isDisabled"):
            st = AccountStatus.Blocked
        else:
            st = AccountStatus.Enabled

        accounts.append(Account(
            id=str(acc["id"]),
            name=acc["name"],
            accountNumber=acc["accountIdentifier"],
            balance=acc["balance"],
            availableBalance=acc["limit"] + acc["balance"],
            overdraftLimit=acc["limit"],
            currency=acc["currencyCode"],
            accountType=at,
            isWithdrawalAccount=is_withdrawal,
            status=st,
        ))

    first_current = next(
        (a for a in accounts if a.accountType == AccountType.Current), None
    )
    if first_current is not None:
        first_current.isDefaultAccount = True

    if only_withdrawal_accounts:
        accounts = [a for a in accounts if a.isWithdrawalAccount]

    if account_type:
        accounts = [a for a in accounts if a.accountType == account_type]

    if status is not None and status != AccountStatus.Enabled:
        accounts = [a for a in accounts if a.status == status]

    if usage:
        accounts = [a for a in accounts if a.usage == usage]

    logger.info("get_accounts: returning %d accounts", len(accounts))
    return AccountList(items=accounts)


async def get_categories() -> CategoryList:
    if _categories_cache:
        return CategoryList(items=_categories_cache)

    logger.info("get_categories: fetching from API")
    async with await _client() as client:
        response = await client.get(
            f"{_BASE_URL}/v1/categories",
            params={"culture": _culture},
        )
    response.raise_for_status()

    for cat in response.json()["data"]:
        _categories_cache.append(Category(id=str(cat["id"]), name=cat["name"]))
        for sub in cat.get("children", []):
            _categories_cache.append(Category(id=str(sub["id"]), name=sub["name"]))

    logger.info("get_categories: loaded %d categories", len(_categories_cache))
    return CategoryList(items=_categories_cache)


_ISO_ALPHA2_RE = re.compile(r"^[A-Z]{2}$")

_MINIMAL_TRANSACTION_FIELDS = frozenset({
    "id",
    "accountId",
    "description",
    "amount",
    "date",
    "categoryId",
    "originalCurrency",
    "originalAmount",
})


def _apply_verbosity(t: Transaction, verbosity: str) -> Transaction:
    if verbosity == "full":
        return t
    for field in Transaction.model_fields:
        if field not in _MINIMAL_TRANSACTION_FIELDS:
            setattr(t, field, None)
    return t


def _map_transaction(t: dict) -> Transaction:
    # Meniga's `amount` is in the account currency and `amountInCurrency` is
    # in the transaction's original currency; they're equal for domestic
    # transactions. Per the bank2ai spec, originalAmount/originalCurrency are
    # populated only when the transaction was in a foreign currency.
    original_date = t.get("originalDate")
    is_foreign = (
        t.get("amountInCurrency") is not None
        and t["amountInCurrency"] != t["amount"]
    )
    text = t["text"]
    original_text = t.get("originalText")

    counterparty: Optional[Party] = None
    if t.get("isMerchant"):
        parsed = {
            entry["key"].lower(): entry.get("value")
            for entry in (t.get("parsedData") or [])
            if entry.get("key")
        }
        town = (parsed.get("city") or "").strip() or None
        country_raw = (parsed.get("country") or "").strip() or None
        country = country_raw if country_raw and _ISO_ALPHA2_RE.match(country_raw) else None
        postal = PostalAddress(townName=town, country=country) if (town or country) else None
        counterparty = Party(name=original_text or text, postalAddress=postal)

    return Transaction(
        id=str(t["id"]),
        accountId=str(t["accountId"]),
        description=text,
        amount=t["amount"],
        date=original_date,
        originalAmount=t["amountInCurrency"] if is_foreign else None,
        originalCurrency=t["currency"] if is_foreign else None,
        categoryId=str(t["categoryId"]) if t.get("categoryId") is not None else None,
        merchantCategoryCode=str(t["mcc"]) if t.get("mcc") is not None else None,
        counterparty=counterparty,
    )


async def get_transactions(
    *,
    count: Optional[int] = None,
    order: str = "NewestFirst",
    verbosity: str = "minimal",
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
        "get_transactions: count=%s order=%s verbosity=%s start=%s end=%s desc=%s cats=%s account_ids=%s min=%s max=%s cursor=%s",
        count, order, verbosity, start_date, end_date, description, category_ids, account_ids, min_amount, max_amount, cursor,
    )
    params: dict[str, str] = {
        "includeChildCategoriesForParentWhenUsingSearchText": "true",
    }
    if verbosity == "minimal":
        params["fields"] = "id,accountId,amount,amountInCurrency,currency,categoryId,text,originalDate,isSplitChild"

    if count is not None:
        params["take"] = str(count)
    if cursor:
        params["pageToken"] = cursor
    if start_date is not None:
        params["originalPeriodFrom"] = start_date
    if end_date is not None:
        params["originalPeriodTo"] = end_date
    if description:
        params["searchText"] = description
        params["useAccentInsensitiveSearch"] = "true"
    if order == "OldestFirst":
        params["ascendingOrder"] = "true"
    if account_ids:
        params["accountIds"] = ",".join(account_ids)
    if min_amount is not None:
        params["amountFrom"] = str(min_amount)
    if max_amount is not None:
        params["amountTo"] = str(max_amount)

    if category_ids:
        params["categoryIds"] = ",".join(category_ids)

    async with await _client() as client:
        response = await client.get(f"{_BASE_URL}/v1/transactions", params=params)
    response.raise_for_status()

    transactions: list[Transaction] = []
    response_json = response.json()
    for t in response_json["data"]:
        logger.info(t)
        transactions.append(_apply_verbosity(_map_transaction(t), verbosity))

    next_cursor: Optional[str] = response_json["meta"]["pageToken"]

    logger.info("get_transactions: returning %d transactions", len(transactions))
    return TransactionList(items=transactions, nextCursor=next_cursor)


async def get_transaction(
    *,
    transaction_id: str,
    account_id: Optional[str] = None,
) -> GetTransactionResponse:
    logger.info("get_transaction: id=%s account_id=%s", transaction_id, account_id)
    async with await _client() as client:
        response = await client.get(f"{_BASE_URL}/v1/transactions/{transaction_id}")
    if response.status_code == 404:
        return GetTransactionResponse(
            content=f"No transaction with id '{transaction_id}'.",
        )
    response.raise_for_status()
    t = response.json()["data"]
    if account_id is not None and str(t.get("accountId")) != account_id:
        return GetTransactionResponse(
            content=f"Transaction '{transaction_id}' is not on account '{account_id}'.",
        )
    return GetTransactionResponse(
        content="Transaction found.",
        item=_map_transaction(t),
    )


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

    eff_min = min_amount
    eff_max = max_amount
    if direction == "Expenses":
        eff_max = 0 if max_amount is None else min(max_amount, 0)
    else:
        eff_min = 0 if min_amount is None else max(min_amount, 0)

    transactions = (await get_transactions(
        start_date=start_date,
        end_date=end_date,
        category_ids=category_ids,
        account_ids=account_ids,
        min_amount=eff_min,
        max_amount=eff_max,
    )).items

    def grouping_key(t: Transaction) -> tuple[Optional[str], Optional[str]]:
        cat = t.categoryId
        month = t.date.strftime("%Y-%m")
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
        groups[key]["total"] += t.amount
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
    matches = [r for r in _recipients_store if name.lower() in r.name.lower()]
    logger.info("get_recipients: found %d matches", len(matches))
    return RecipientList(items=matches)


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
        id=str(uuid4()),
        name=name,
        accountIdentifier=account_identifier,
        nationalId=national_id,
        nickname=nickname,
        bic=bic,
        defaultDescription=default_description,
    )
    _recipients_store.append(recipient)
    response = CreateRecipientResponse(
        content=f"Recipient '{name}' created successfully.",
        item=recipient,
    )
    _idempotent_put("create-recipient", idempotency_key, response)
    return response


# ---- Transfer intent store (in-memory) ----

_INTENT_TTL = timedelta(minutes=5)
_intent_store: dict[str, PreparedTransfer] = {}


# ---- Idempotency cache ----

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

    accounts = (await get_accounts()).items
    debtor = next((a for a in accounts if a.id == debtor_account_id), None)
    if debtor is None:
        return PrepareTransferResponse(
            content=f"No debtor account with id '{debtor_account_id}'.",
            code="invalid_account",
        )
    if debtor.availableBalance is not None and debtor.availableBalance < amount:
        return PrepareTransferResponse(
            content="Insufficient funds.",
            code="insufficient_funds",
        )

    resolved_end_to_end_id = end_to_end_id or f"e2e_{uuid4().hex[:16]}"
    intent_id = f"intent_{uuid4().hex}"
    now = datetime.now(timezone.utc)

    summary = TransferSummary(
        debtorAccount=debtor,
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
            "submitted to Meniga."
        ),
        item=ExecutedTransfer(
            transactionId=f"tx_{uuid4().hex[:12]}",
            status=TransferExecutionStatus.Pending,
            executedAt=now,
        ),
    )
    _idempotent_put("execute-transfer", idempotency_key, response)
    return response


# ---- Wire up ----

app = FastMCP("bank2ai-meniga")

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
    output_schemas="inline",
)


async def main() -> None:
    await app.run_async()


def main_sync() -> None:
    """Entry-point for the ``bank2ai-meniga`` console script."""
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()
