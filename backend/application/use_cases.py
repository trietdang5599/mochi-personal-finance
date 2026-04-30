from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import uuid4

from backend.application.ports import TransactionRepository
from backend.domain.entities import Transaction, TransactionType


@dataclass(frozen=True)
class CreateTransactionInput:
    type: TransactionType
    amount: Decimal
    date: date
    category_id: str
    description: str


class CreateTransaction:
    def __init__(self, repository: TransactionRepository) -> None:
        self.repository = repository

    def execute(self, payload: CreateTransactionInput) -> Transaction:
        transaction = Transaction(
            id=f"tx_{uuid4().hex}",
            type=payload.type,
            amount=payload.amount,
            date=payload.date,
            category_id=payload.category_id,
            description=payload.description,
        )
        return self.repository.save(transaction)


class ListTransactions:
    def __init__(self, repository: TransactionRepository) -> None:
        self.repository = repository

    def execute(self) -> list[Transaction]:
        return sorted(self.repository.list(), key=lambda item: item.date, reverse=True)
