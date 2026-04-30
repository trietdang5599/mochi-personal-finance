from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


@dataclass(frozen=True)
class Transaction:
    id: str
    type: TransactionType
    amount: Decimal
    date: date
    category_id: str
    description: str

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("Transaction amount must be greater than zero")
        if not self.category_id:
            raise ValueError("Transaction category is required")
        if not self.description.strip():
            raise ValueError("Transaction description is required")


@dataclass(frozen=True)
class Category:
    id: str
    name: str
    type: str
    color: str
    budget: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Category name is required")
        if self.type not in {"income", "expense", "both"}:
            raise ValueError("Category type must be income, expense, or both")
