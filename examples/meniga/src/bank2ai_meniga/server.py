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
import time
from collections import defaultdict
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
    AccountType,
    Category,
    CategoryList,
    CreateRecipientResponse,
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
) -> AccountList:
    logger.info(
        "get_accounts: only_withdrawal=%s account_type=%s",
        only_withdrawal_accounts, account_type,
    )
    async with await _client() as client:
        response = await client.get(f"{_BASE_URL}/v1/accounts")
    response.raise_for_status()

    accounts: list[Account] = []
    for acc in response.json()["data"]:
        category = acc.get("accountCategory")
        if category == "Credit":
            at, is_withdrawal = AccountType.Credit, False
        elif category == "Savings":
            at, is_withdrawal = AccountType.Savings, True
        elif category == "Current":
            at, is_withdrawal = AccountType.Current, True
        else:
            continue

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


async def get_transactions(
    *,
    count: Optional[int] = None,
    order: str = "NewestFirst",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    description: Optional[str] = None,
    categories: Optional[list[str]] = None,
    account_ids: Optional[list[str]] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    cursor: Optional[str] = None,
) -> TransactionList:
    logger.info(
        "get_transactions: count=%s order=%s start=%s end=%s desc=%s cats=%s account_ids=%s min=%s max=%s cursor=%s",
        count, order, start_date, end_date, description, categories, account_ids, min_amount, max_amount, cursor,
    )
    params: dict[str, str] = {
        "fields": "id,amount,amountInCurrency,currency,categoryId,text,date",
        "includeChildCategoriesForParentWhenUsingSearchText": "true",
    }
    if count is not None:
        params["take"] = str(count)
    if cursor:
        params["pageToken"] = cursor
    if start_date is not None:
        params["periodFrom"] = start_date
    if end_date is not None:
        params["periodTo"] = end_date
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

    all_categories = (await get_categories()).items

    if categories:
        category_ids = {c.id for c in all_categories if c.name in categories}
        if category_ids:
            params["categoryIds"] = ",".join(category_ids)

    async with await _client() as client:
        response = await client.get(f"{_BASE_URL}/v1/transactions", params=params)
    response.raise_for_status()

    cat_by_id = {c.id: c.name for c in all_categories}

    transactions: list[Transaction] = []
    response_json = response.json()
    for t in response_json["data"]:
        cat_name = cat_by_id.get(str(t["categoryId"]))
        if categories:
            lower_cats = {c.lower() for c in categories}
            if (cat_name or "").lower() not in lower_cats:
                continue

        transactions.append(Transaction(
            id=str(t["id"]),
            description=t["text"],
            amount=t["amount"],
            transaction_date=t["date"],
            amount_in_currency=t.get("amountInCurrency"),
            currency=t.get("currency"),
            category=cat_name,
        ))

    next_cursor: Optional[str] = response_json["meta"]["pageToken"]

    logger.info("get_transactions: returning %d transactions", len(transactions))
    return TransactionList(items=transactions, nextCursor=next_cursor)


async def get_transactions_summary(
    *,
    direction: str,
    group_by: str = "category",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    categories: Optional[list[str]] = None,
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
        categories=categories,
        account_ids=account_ids,
        min_amount=eff_min,
        max_amount=eff_max,
    )).items

    def grouping_key(t: Transaction) -> tuple[Optional[str], Optional[str]]:
        cat = t.category or "Uncategorized"
        month = t.transaction_date.strftime("%Y-%m")
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
            category=cat,
            month=month,
            total_amount=stats["total"],
            transaction_count=int(stats["count"]),
            average_amount=stats["total"] / stats["count"] if stats["count"] > 0 else 0,
        )
        for (cat, month), stats in groups.items()
    ]
    summary.sort(key=lambda g: g.total_amount)

    return TransactionsSummary(
        summary=summary,
        period=TransactionsSummaryPeriod(
            start_date=start_date or "all",
            end_date=end_date or "all",
        ),
        total=sum(g.total_amount for g in summary),
    )


async def get_recipients(*, name: str) -> RecipientList:
    logger.info("get_recipients: name=%s", name)
    matches = [r for r in _recipients_store if name.lower() in r.name.lower()]
    logger.info("get_recipients: found %d matches", len(matches))
    return RecipientList(items=matches)


async def create_recipient(
    *,
    name: str,
    account_number: str,
    kennitala: str = "",
) -> CreateRecipientResponse:
    logger.info("create_recipient: name=%s account=%s", name, account_number)
    recipient = Recipient(
        id=str(uuid4()),
        name=name,
        accountNumber=account_number,
        socialSecurityNumber=kennitala,
    )
    _recipients_store.append(recipient)
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
    logger.info("prepare_transfer_icelandic: amount=%s recipient_ssn=%s", amount, recipient_ssn)
    accounts = (await get_accounts()).items
    if withdrawal_account_number:
        account = next(
            (a for a in accounts if a.accountNumber == withdrawal_account_number),
            None,
        )
    else:
        account = next((a for a in accounts if a.isDefaultAccount), None)

    if not account:
        logger.warning("prepare_transfer_icelandic: no valid account found")
        return TransferPreparedResponse(content="Invalid or no default account found.")

    if account.availableBalance is not None and account.availableBalance < amount:
        logger.warning("prepare_transfer_icelandic: insufficient funds")
        return TransferPreparedResponse(content="Insufficient funds.")

    recipients = (await get_recipients(name=recipient_ssn)).items
    recipient = next(
        (r for r in recipients if r.socialSecurityNumber == recipient_ssn), None
    )

    return TransferPreparedResponse(
        content="A transfer has been prepared. Please confirm the details with the user before calling execute-transfer.",
        item=TransferPreparedItem(
            amount=amount,
            description=description,
            currency=currency or account.currency,
            recipient_account_number=recipient_account_number,
            recipient_ssn=recipient_ssn,
            recipient_name=recipient.name if recipient else "Unknown",
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
    logger.info("execute_transfer: amount=%s to=%s", amount, recipient_account_number)
    return ExecuteTransferResponse(
        content=f"Transfer of {amount:,.2f} completed successfully.",
    )


# ---- Wire up ----

app = FastMCP("bank2ai-meniga")

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
    """Entry-point for the ``bank2ai-meniga`` console script."""
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()
