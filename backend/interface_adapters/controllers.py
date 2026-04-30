from __future__ import annotations

from fastapi import APIRouter

from backend.application.use_cases import CreateTransaction, CreateTransactionInput, ListTransactions
from backend.interface_adapters.schemas import TransactionCreateRequest, TransactionResponse


def transaction_router(create_transaction: CreateTransaction, list_transactions: ListTransactions) -> APIRouter:
    router = APIRouter(prefix="/transactions", tags=["transactions"])

    @router.get("", response_model=list[TransactionResponse])
    def list_all() -> list[TransactionResponse]:
        return [TransactionResponse.from_entity(item) for item in list_transactions.execute()]

    @router.post("", response_model=TransactionResponse, status_code=201)
    def create(payload: TransactionCreateRequest) -> TransactionResponse:
        entity = create_transaction.execute(
            CreateTransactionInput(
                type=payload.type,
                amount=payload.amount,
                date=payload.date,
                category_id=payload.category_id,
                description=payload.description,
            )
        )
        return TransactionResponse.from_entity(entity)

    return router
