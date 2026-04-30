from __future__ import annotations

from backend.application.ports import TransactionRepository
from backend.domain.entities import Transaction


class InMemoryTransactionRepository(TransactionRepository):
    def __init__(self) -> None:
        self._items: dict[str, Transaction] = {}

    def list(self) -> list[Transaction]:
        return list(self._items.values())

    def save(self, transaction: Transaction) -> Transaction:
        self._items[transaction.id] = transaction
        return transaction

    def delete(self, transaction_id: str) -> None:
        self._items.pop(transaction_id, None)
