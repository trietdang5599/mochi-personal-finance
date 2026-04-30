from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from backend.domain.entities import Transaction, TransactionType


class TransactionCreateRequest(BaseModel):
    type: TransactionType
    amount: Decimal = Field(gt=0)
    date: date
    category_id: str = Field(min_length=1)
    description: str = Field(min_length=1, max_length=80)


class TransactionResponse(BaseModel):
    id: str
    type: TransactionType
    amount: Decimal
    date: date
    category_id: str
    description: str

    @classmethod
    def from_entity(cls, transaction: Transaction) -> "TransactionResponse":
        return cls(
            id=transaction.id,
            type=transaction.type,
            amount=transaction.amount,
            date=transaction.date,
            category_id=transaction.category_id,
            description=transaction.description,
        )
