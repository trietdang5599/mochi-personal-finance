from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.application.use_cases import CreateTransaction, ListTransactions
from backend.infrastructure.repositories import InMemoryTransactionRepository
from backend.interface_adapters.controllers import transaction_router


def create_app() -> FastAPI:
    repository = InMemoryTransactionRepository()
    app = FastAPI(title="Finova API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(
        transaction_router(
            create_transaction=CreateTransaction(repository),
            list_transactions=ListTransactions(repository),
        )
    )
    return app


app = create_app()
