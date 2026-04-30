from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from backend.domain.entities import Transaction


class TransactionRepository(ABC):
    @abstractmethod
    def list(self) -> Iterable[Transaction]:
        raise NotImplementedError

    @abstractmethod
    def save(self, transaction: Transaction) -> Transaction:
        raise NotImplementedError

    @abstractmethod
    def delete(self, transaction_id: str) -> None:
        raise NotImplementedError
