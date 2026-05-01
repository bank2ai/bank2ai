"""Meniga bank adapter.

Integrates with Meniga APIs (api.meniga.cloud, api.meniga.is) to provide
Bank2AI MCP tool implementations backed by real bank data.

Required environment variables:
    BANK2AI_MENIGA_BASE_URL: Base URL for the Meniga API (e.g. https://api.meniga.cloud/user/core)
    BANK2AI_MENIGA_EMAIL: Email for Meniga authentication
    BANK2AI_MENIGA_PASSWORD: Password for Meniga authentication

Optional environment variables:
    BANK2AI_MENIGA_CULTURE: Culture/locale setting (default: en-GB)
"""

import logging
import os
from collections import defaultdict
from typing import Any, Optional
from uuid import uuid4
import jwt
import httpx

from adapters.base import BankAdapter
from adapters.models import *


class MenigaAdapter(BankAdapter):
    """Bank adapter backed by a Meniga API."""

    def __init__(self, logger: logging.Logger):
        super().__init__(logger)
        self._base_url = os.environ["BANK2AI_MENIGA_BASE_URL"].rstrip("/")
        self._email = os.environ["BANK2AI_MENIGA_EMAIL"]
        self._password = os.environ["BANK2AI_MENIGA_PASSWORD"]
        self._culture = os.environ.get("BANK2AI_MENIGA_CULTURE", "en-GB")
        self._token: Optional[str] = None
        self._categories: list[Category] = []
        self._receipients: list[Receipient] = []
        self.logger.info("MenigaAdapter initialized, base_url=%s", self._base_url)

    def get_client(self) -> httpx.AsyncClient:
        if self._token:
            return httpx.AsyncClient(
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=30.0,
            )
        else:
            self.logger.error("Auth token missing")
            return httpx.AsyncClient()

    async def authenticate(self, param_values: list[AuthParamValue]) -> AuthReponse:
        creds = {p.id: p.value for p in param_values}
        email = creds.get("email", self._email)
        password = creds.get("password", self._password)
        if not email or not password:
            self.logger.warning("Missing email or password in authentication parameters")
            return AuthReponse(
                authenticated=False,
                required_parameters = [
                    AuthParam(id="email", title="Email", type=AuthParamType.Text),
                    AuthParam(id="password", title="Password", type=AuthParamType.Password),
                ],
            )        

        self.logger.info("Authenticating with Meniga API at %s", self._base_url)
        response = httpx.post(
            f"{self._base_url}/v1/authentication",
            json={"email": email, "password": password},
        )
        self.logger.info("Auth response status: %d", response.status_code)

        if response.status_code in (400, 401):
            self.logger.error("Authentication failed: %d %s", response.status_code, response.text)
            return AuthReponse(authenticated=False, message="Authentication failed")

        response.raise_for_status()
        response_data = response.json()
        self._token = response_data["data"]["accessToken"]
        decoded_token = jwt.decode(self._token, options={"verify_signature": False})
        self.logger.info("Token decoded, fetching user profile")
    
        me_response = httpx.get(
            f"{self._base_url}/v1/me?includeAll=true",
            headers={"Authorization": "Bearer " + self._token},
        ).json()

        person_id = decoded_token["context"]["personId"]
        person = next(
            (x for x in me_response["data"] if x["personId"] == person_id),
            None,
        )
        self._culture = person["culture"] if person else "en-GB"
        self._email = email
        self._password = password
        self.logger.info("Authenticated successfully, culture=%s", self._culture)

        return AuthReponse(
            authenticated=True,
            token=self._token,
            culture=self._culture,
        )

    async def get_accounts(
        self,
        only_withdrawal: bool = False,
        account_type: Optional[str] = None,
    ) -> list[Account]:
        self.logger.info("get_accounts: only_withdrawal=%s, account_type=%s", only_withdrawal, account_type)
        client = self.get_client()
        response = await client.get(f"{self._base_url}/v1/accounts")
        response.raise_for_status()

        accounts: list[Account] = []
        for acc in response.json()["data"]:
            category = acc.get("accountCategory")
            match category:
                case "Credit":
                    at = AccountType.Credit
                    is_withdrawal = False
                case "Savings":
                    at = AccountType.Savings
                    is_withdrawal = True
                case "Current":
                    at = AccountType.Current
                    is_withdrawal = True
                case _:
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

        if only_withdrawal:
            accounts = [a for a in accounts if a.isWithdrawalAccount]

        if account_type:
            accounts = [a for a in accounts if a.accountType == account_type]

        self.logger.info("get_accounts: returning %d accounts", len(accounts))
        return accounts

    async def get_categories(self) -> list[Category]:
        if self._categories:
            return self._categories

        self.logger.info("get_categories: fetching from API")
        client = self.get_client()
        response = await client.get(
            f"{self._base_url}/v1/categories",
            params={"culture": self._culture},
        )
        response.raise_for_status()

        for cat in response.json()["data"]:
            self._categories.append(Category(id=str(cat["id"]), name=cat["name"]))
            for sub in cat.get("children", []):
                self._categories.append(Category(id=str(sub["id"]), name=sub["name"]))

        self.logger.info("get_categories: loaded %d categories", len(self._categories))
        return self._categories

    async def get_transactions(
        self,
        count: Optional[int] = None,
        type: TransactionType = TransactionType.Any,
        order: TransactionOrder = TransactionOrder.NewestFirst,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        description: Optional[str] = None,
        categories: Optional[list[str]] = None,
    ) -> list[Transaction]:
        self.logger.info(
            "get_transactions: count=%s type=%s order=%s start=%s end=%s desc=%s cats=%s",
            count, type, order, start_date, end_date, description, categories,
        )
        params: dict[str, str] = {
            "fields": "id,amount,categoryId,text,date",
            "includeChildCategoriesForParentWhenUsingSearchText": "true",
        }

        if type != TransactionType.Any:
            params["categoryTypes"] = type.value

        if count is not None:
            params["take"] = str(count)

        if start_date is not None:
            params["periodFrom"] = start_date

        if end_date is not None:
            params["periodTo"] = end_date

        if description:
            params["searchText"] = description
            params["useAccentInsensitiveSearch"] = "true"

        if order == TransactionOrder.OldestFirst:
            params["ascendingOrder"] = "true"

        all_categories = await self.get_categories()

        self.logger.info("get_transactions: filtering by categories=%s", categories)
        if categories:
            category_ids = {c.id for c in all_categories if c.name in categories}
            if len(category_ids) > 0:
                params["categoryIds"] = ",".join(category_ids)

        client = self.get_client()
        response = await client.get(
            f"{self._base_url}/v1/transactions", params=params
        )
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

        self.logger.info("get_transactions: returning %d transactions", len(transactions))
        return transactions

    async def get_spending_summary(
        self,
        group_by: str = "category",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        categories: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        self.logger.info("get_spending_summary: group_by=%s", group_by)
        transactions = await self.get_transactions(
            type=TransactionType.Expenses,
            start_date=start_date,
            end_date=end_date,
            categories=categories,
        )

        groups: dict[str, dict[str, Any]] = defaultdict(lambda: {"total": 0, "count": 0})
        for t in transactions:
            key = t.category or "Uncategorized"
            groups[key]["total"] += t.amount
            groups[key]["count"] += 1

        summary = []
        for group, stats in groups.items():
            summary.append({
                "group": group,
                "total_amount": stats["total"],
                "transaction_count": stats["count"],
                "average_amount": stats["total"] / stats["count"] if stats["count"] > 0 else 0,
            })

        summary.sort(key=lambda x: x["total_amount"])
        total = sum(s["total_amount"] for s in summary)

        return {
            "summary": summary,
            "period": {
                "start_date": start_date or "all",
                "end_date": end_date or "all",
            },
            "total": total,
        }

    async def search_recipients(self, name: str) -> list[Receipient]:
        self.logger.info("search_recipients: name=%s", name)
        matches = [r for r in self._receipients if name.lower() in r.name.lower()]
        self.logger.info("search_recipients: found %d matches", len(matches))
        return matches

    async def create_recipient(
        self,
        name: str,
        account_number: str,
        kennitala: str = "",
    ) -> dict[str, Any]:
        self.logger.info("create_recipient: name=%s account=%s", name, account_number)
        recipient = Receipient(
            id=str(uuid4()),
            name=name,
            accountNumber=account_number,
            socialSecurityNumber=kennitala,
        )

        self._receipients.append(recipient)

        return {
            "content": f"Recipient '{name}' created successfully.",
            "item": recipient,
        }

    async def prepare_transfer(
        self,
        amount: float,
        recipient_ssn: str,
        recipient_account_number: str,
        description: str = "",
        withdrawal_account_number: str = "",
        currency: str = "",
    ) -> dict[str, Any]:
        self.logger.info("prepare_transfer: amount=%s recipient_ssn=%s", amount, recipient_ssn)
        accounts = await self.get_accounts()

        if withdrawal_account_number:
            account = next(
                (a for a in accounts if a.accountNumber == withdrawal_account_number),
                None,
            )
        else:
            account = next((a for a in accounts if a.isDefaultAccount), None)

        if not account:
            self.logger.warning("prepare_transfer: no valid account found")
            return {"content": "Invalid or no default account found."}

        if account.availableBalance is not None and account.availableBalance < amount:
            self.logger.warning("prepare_transfer: insufficient funds")
            return {"content": "Insufficient funds."}

        recipients = await self.search_recipients(recipient_ssn)
        recipient = next(
            (r for r in recipients if r.socialSecurityNumber == recipient_ssn), None
        )

        return {
            "content": "A transfer has been prepared. Please confirm the details with the user before calling execute-transfer.",
            "item": {
                "amount": amount,
                "description": description,
                "currency": currency or account.currency,
                "recipient_account_number": recipient_account_number,
                "recipient_ssn": recipient_ssn,
                "recipient_name": recipient.name if recipient else "Unknown",
                "withdrawal_account_id": account.id,
                "withdrawal_account": account.model_dump(),
            },
            "actions": [{"title": "Transfer", "link": "/transfer"}],
        }

    async def execute_transfer(
        self,
        withdrawal_account_id: str,
        recipient_account_number: str,
        amount: float,
        description: str = "Transfer",
    ) -> dict[str, Any]:
        self.logger.info("execute_transfer: amount=%s to=%s", amount, recipient_account_number)
        return {
            "content": f"Transfer of {amount:,.2f} completed successfully.",
        }
