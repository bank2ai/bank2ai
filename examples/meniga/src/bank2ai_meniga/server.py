"""Bank2AI MCP server backed by Meniga APIs.

Required environment variables:
    BANK2AI_MENIGA_BASE_URL: Base URL for the Meniga API
        (e.g. https://api.meniga.cloud/user/core)

Optional environment variables:
    BANK2AI_MENIGA_EMAIL: Email; if set, used as the default credential
    BANK2AI_MENIGA_PASSWORD: Password; if set, used as the default credential
    BANK2AI_MENIGA_CULTURE: Locale (default: en-GB)
    BANK2AI_LOG_RESPONSES: Set to 1/true to log full tool responses
"""

import asyncio
import logging
import os
from collections import defaultdict
from typing import Optional
from uuid import uuid4

import httpx
import jwt
from dotenv import load_dotenv
from fastmcp import FastMCP

from bank2ai import (
    Account,
    AccountType,
    AuthParam,
    AuthParamType,
    AuthParamValue,
    AuthResponse,
    AuthState,
    Category,
    CreateRecipientResponse,
    ExecuteTransferResponse,
    Receipient,
    SpendingSummary,
    SpendingSummaryGroup,
    SpendingSummaryPeriod,
    Transaction,
    TransferAction,
    TransferPreparedItem,
    TransferPreparedResponse,
    make_auth_middleware,
    register_authenticate_tool,
    register_tools,
)


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("bank2ai-meniga")

_log_responses = os.environ.get("BANK2AI_LOG_RESPONSES", "").lower() in ("1", "true", "yes")

_BASE_URL = os.environ["BANK2AI_MENIGA_BASE_URL"].rstrip("/")
_DEFAULT_EMAIL = os.environ.get("BANK2AI_MENIGA_EMAIL", "")
_DEFAULT_PASSWORD = os.environ.get("BANK2AI_MENIGA_PASSWORD", "")
_DEFAULT_CULTURE = os.environ.get("BANK2AI_MENIGA_CULTURE", "en-GB")


# ---- Per-server state ----

_auth_state = AuthState()
_token: Optional[str] = None
_culture: str = _DEFAULT_CULTURE
_categories_cache: list[Category] = []
_recipients_store: list[Receipient] = []


def _client() -> httpx.AsyncClient:
    headers: dict[str, str] = {}
    if _token:
        headers["Authorization"] = f"Bearer {_token}"
    return httpx.AsyncClient(headers=headers, timeout=30.0)


# ---- Auth handler ----

async def authenticate(param_values: list[AuthParamValue]) -> AuthResponse:
    global _token, _culture
    creds = {p.id: p.value for p in param_values}
    email = creds.get("email") or _DEFAULT_EMAIL
    password = creds.get("password") or _DEFAULT_PASSWORD

    if not email or not password:
        logger.warning("Missing email or password in authentication parameters")
        return AuthResponse(
            authenticated=False,
            required_parameters=[
                AuthParam(id="email", title="Email", type=AuthParamType.Text),
                AuthParam(id="password", title="Password", type=AuthParamType.Password),
            ],
        )

    logger.info("Authenticating with Meniga API at %s", _BASE_URL)
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{_BASE_URL}/v1/authentication",
            json={"email": email, "password": password},
        )
        logger.info("Auth response status: %d", response.status_code)
        if response.status_code in (400, 401):
            logger.error("Authentication failed: %d %s", response.status_code, response.text)
            return AuthResponse(authenticated=False, message="Authentication failed")
        response.raise_for_status()
        data = response.json()
        _token = data["data"]["accessToken"]
        decoded = jwt.decode(_token, options={"verify_signature": False})

        _culture = _DEFAULT_CULTURE
        try:
            me_response = await client.get(
                f"{_BASE_URL}/v1/me?includeAll=true",
                headers={"Authorization": "Bearer " + _token},
            )
            me_response.raise_for_status()
            person_id = decoded["context"]["personId"]
            person = next(
                (x for x in me_response.json()["data"] if x["personId"] == person_id),
                None,
            )
            if person:
                _culture = person["culture"]
        except httpx.HTTPError as e:
            logger.warning("Failed to fetch /v1/me, using default culture: %s", e)

    logger.info("Authenticated successfully, culture=%s", _culture)
    return AuthResponse(authenticated=True, token=_token, culture=_culture)


# ---- Bank2AI tool handlers ----

async def get_accounts(
    *,
    only_withdrawal_accounts: bool = False,
    account_type: Optional[str] = None,
) -> list[Account]:
    logger.info(
        "get_accounts: only_withdrawal=%s account_type=%s",
        only_withdrawal_accounts, account_type,
    )
    async with _client() as client:
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
    return accounts


async def get_categories() -> list[Category]:
    if _categories_cache:
        return _categories_cache

    logger.info("get_categories: fetching from API")
    async with _client() as client:
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
    return _categories_cache


async def get_transactions(
    *,
    count: Optional[int] = None,
    type: str = "Any",
    order: str = "NewestFirst",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    description: Optional[str] = None,
    categories: Optional[list[str]] = None,
) -> list[Transaction]:
    logger.info(
        "get_transactions: count=%s type=%s order=%s start=%s end=%s desc=%s cats=%s",
        count, type, order, start_date, end_date, description, categories,
    )
    params: dict[str, str] = {
        "fields": "id,amount,categoryId,text,date",
        "includeChildCategoriesForParentWhenUsingSearchText": "true",
    }
    if type != "Any":
        params["categoryTypes"] = type
    if count is not None:
        params["take"] = str(count)
    if start_date is not None:
        params["periodFrom"] = start_date
    if end_date is not None:
        params["periodTo"] = end_date
    if description:
        params["searchText"] = description
        params["useAccentInsensitiveSearch"] = "true"
    if order == "OldestFirst":
        params["ascendingOrder"] = "true"

    all_categories = await get_categories()

    if categories:
        category_ids = {c.id for c in all_categories if c.name in categories}
        if category_ids:
            params["categoryIds"] = ",".join(category_ids)

    async with _client() as client:
        response = await client.get(f"{_BASE_URL}/v1/transactions", params=params)
    response.raise_for_status()

    cat_by_id = {c.id: c.name for c in all_categories}

    transactions: list[Transaction] = []
    for t in response.json()["data"]:
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
            category=cat_name,
        ))

    logger.info("get_transactions: returning %d transactions", len(transactions))
    return transactions


async def get_spending_summary(
    *,
    group_by: str = "category",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    categories: Optional[list[str]] = None,
) -> SpendingSummary:
    logger.info("get_spending_summary: group_by=%s", group_by)
    transactions = await get_transactions(
        type="Expenses",
        start_date=start_date,
        end_date=end_date,
        categories=categories,
    )

    groups: dict[str, dict[str, float]] = defaultdict(lambda: {"total": 0, "count": 0})
    for t in transactions:
        key = t.category or "Uncategorized"
        groups[key]["total"] += t.amount
        groups[key]["count"] += 1

    summary = [
        SpendingSummaryGroup(
            group=group,
            total_amount=stats["total"],
            transaction_count=int(stats["count"]),
            average_amount=stats["total"] / stats["count"] if stats["count"] > 0 else 0,
        )
        for group, stats in groups.items()
    ]
    summary.sort(key=lambda g: g.total_amount)

    return SpendingSummary(
        summary=summary,
        period=SpendingSummaryPeriod(
            start_date=start_date or "all",
            end_date=end_date or "all",
        ),
        total=sum(g.total_amount for g in summary),
    )


async def search_recipients(*, name: str) -> list[Receipient]:
    logger.info("search_recipients: name=%s", name)
    matches = [r for r in _recipients_store if name.lower() in r.name.lower()]
    logger.info("search_recipients: found %d matches", len(matches))
    return matches


async def create_recipient(
    *,
    name: str,
    account_number: str,
    kennitala: str = "",
) -> CreateRecipientResponse:
    logger.info("create_recipient: name=%s account=%s", name, account_number)
    recipient = Receipient(
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


async def prepare_transfer(
    *,
    amount: float,
    recipient_ssn: str,
    recipient_account_number: str,
    description: str = "",
    withdrawal_account_number: str = "",
    currency: str = "",
) -> TransferPreparedResponse:
    logger.info("prepare_transfer: amount=%s recipient_ssn=%s", amount, recipient_ssn)
    accounts = await get_accounts()
    if withdrawal_account_number:
        account = next(
            (a for a in accounts if a.accountNumber == withdrawal_account_number),
            None,
        )
    else:
        account = next((a for a in accounts if a.isDefaultAccount), None)

    if not account:
        logger.warning("prepare_transfer: no valid account found")
        return TransferPreparedResponse(content="Invalid or no default account found.")

    if account.availableBalance is not None and account.availableBalance < amount:
        logger.warning("prepare_transfer: insufficient funds")
        return TransferPreparedResponse(content="Insufficient funds.")

    recipients = await search_recipients(name=recipient_ssn)
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
app.add_middleware(
    make_auth_middleware(_auth_state, authenticate, logger, log_responses=_log_responses)
)

register_tools(
    app,
    get_accounts=get_accounts,
    get_transactions=get_transactions,
    get_categories=get_categories,
    get_spending_summary=get_spending_summary,
    search_recipients=search_recipients,
    create_recipient=create_recipient,
    prepare_transfer=prepare_transfer,
    execute_transfer=execute_transfer,
)


async def main() -> None:
    await register_authenticate_tool(app, _auth_state, authenticate)
    await app.run_async()


def main_sync() -> None:
    """Entry-point for the ``bank2ai-meniga`` console script."""
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()
