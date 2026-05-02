"""Demo adapter using hardcoded test data."""

from collections import defaultdict
from datetime import datetime
from typing import Any, Optional

from adapters.demo import data
from adapters.base import BankAdapter
from adapters.models import *


class DemoDataAdapter(BankAdapter):
    """Bank adapter backed by hardcoded demo data from data.py."""

    async def authenticate(self, param_values: list[AuthParamValue]) -> AuthResponse:
        return AuthResponse(
            authenticated=True,
        )

    async def get_accounts(
        self,
        only_withdrawal: bool = False,
        account_type: Optional[str] = None,
    ) -> list[Account]:
        accounts = data.ACCOUNTS.copy()

        if only_withdrawal:
            accounts = [a for a in accounts if a["isWithdrawalAccount"]]

        if account_type:
            accounts = [a for a in accounts if a["accountType"] == account_type]

        return [Account(**a) for a in accounts]

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
        transactions = data.TRANSACTIONS.copy()

        if type == "Income":
            transactions = [t for t in transactions if t["amount"] > 0]
        elif type == "Expenses":
            transactions = [t for t in transactions if t["amount"] < 0]

        if start_date:
            transactions = [t for t in transactions if t["transaction_date"] >= start_date]
        if end_date:
            transactions = [t for t in transactions if t["transaction_date"] <= end_date]

        if categories:
            lower_cats = {c.lower() for c in categories}
            transactions = [
                t for t in transactions if t.get("category", "").lower() in lower_cats
            ]

        if description:
            search = description.lower()
            transactions = [
                t for t in transactions if search in t["description"].lower()
            ]

        transactions.sort(
            key=lambda t: t["transaction_date"],
            reverse=(order == "NewestFirst"),
        )

        if count:
            transactions = transactions[:count]

        return [Transaction(**t) for t in transactions]

    async def get_categories(self) -> list[Category]:
        return [Category(**c) for c in data.CATEGORIES]

    async def get_spending_summary(
        self,
        group_by: str = "category",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        categories: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        transactions = data.TRANSACTIONS.copy()

        if start_date:
            transactions = [t for t in transactions if t["transaction_date"] >= start_date]
        if end_date:
            transactions = [t for t in transactions if t["transaction_date"] <= end_date]

        if categories:
            lower_cats = {c.lower() for c in categories}
            transactions = [
                t for t in transactions if t.get("category", "").lower() in lower_cats
            ]

        # Only include expenses
        transactions = [t for t in transactions if t["amount"] < 0]

        groups: dict[str, dict[str, Any]] = defaultdict(lambda: {"total": 0, "count": 0})
        for t in transactions:
            key = t.get("category", "Uncategorized")
            groups[key]["total"] += t["amount"]
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
        search_name = name.lower()
        matches = [r for r in data.RECIPIENTS if search_name in r["name"].lower()]
        return [Receipient(**r) for r in matches]

    async def create_recipient(
        self,
        name: str,
        account_number: str,
        kennitala: str = "",
    ) -> dict[str, Any]:
        new_recipient = {
            "id": f"rcpt_{len(data.RECIPIENTS) + 1:03d}",
            "name": name,
            "accountNumber": account_number,
            "socialSecurityNumber": kennitala,
            "accountNumberType": "Domestic",
            "bankInfo": "Demo Bank",
            "paymentType": "Domestic",
            "isFavorite": False,
        }

        return {
            "content": f"Recipient '{name}' created successfully.",
            "item": new_recipient,
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
        recipient = next(
            (r for r in data.RECIPIENTS if r["socialSecurityNumber"] == recipient_ssn),
            None,
        )

        if not recipient:
            return {"content": "Invalid social security number."}

        if withdrawal_account_number:
            account = next(
                (a for a in data.ACCOUNTS if a["accountNumber"] == withdrawal_account_number),
                None,
            )
        else:
            account = next((a for a in data.ACCOUNTS if a["isDefaultAccount"]), None)

        if not account:
            return {"content": "Invalid or no default account found."}

        if account["availableBalance"] < amount:
            return {"content": "Insufficient funds."}

        return {
            "content": "A transfer has been prepared. Please confirm the details with the user before calling execute-transfer.",
            "item": {
                "amount": amount,
                "description": description,
                "currency": currency or account["currency"],
                "recipient_account_number": recipient_account_number,
                "recipient_ssn": recipient_ssn,
                "recipient_name": recipient["name"],
                "withdrawal_account_id": account["id"],
                "withdrawal_account": account,
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
        return {
            "content": f"Transfer of {amount:,.2f} completed successfully.",
            "item": {
                "transfer_id": f"txfr_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
            },
        }
