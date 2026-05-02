"""Abstract base class for bank adapters."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from adapters.models import *

class BankAdapter(ABC):
    """Interface that all bank adapters must implement.

    Each method corresponds to one Bank2AI MCP tool.
    Methods are async to support adapters that make HTTP calls to bank APIs.
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    @abstractmethod
    async def authenticate(self, param_values: list[AuthParamValue]) -> AuthResponse:
        ...

    @abstractmethod
    async def get_accounts(
        self,
        only_withdrawal: bool = False,
        account_type: Optional[str] = None,
    ) -> list[Account]:
        ...

    @abstractmethod
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
        ...

    @abstractmethod
    async def get_categories(self) -> list[Category]:
        ...

    @abstractmethod
    async def get_spending_summary(
        self,
        group_by: str = "category",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        categories: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        ...

    @abstractmethod
    async def search_recipients(self, name: str) -> list[Receipient]:
        ...

    @abstractmethod
    async def create_recipient(
        self,
        name: str,
        account_number: str,
        kennitala: str = "",
    ) -> dict[str, Any]:
        ...

    @abstractmethod
    async def prepare_transfer(
        self,
        amount: float,
        recipient_ssn: str,
        recipient_account_number: str,
        description: str = "",
        withdrawal_account_number: str = "",
        currency: str = "",
    ) -> dict[str, Any]:
        ...

    @abstractmethod
    async def execute_transfer(
        self,
        withdrawal_account_id: str,
        recipient_account_number: str,
        amount: float,
        description: str = "Transfer",
    ) -> dict[str, Any]:
        ...
