from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.application.use_cases import CreateTransaction, ListTransactions
from backend.infrastructure.repositories import InMemoryTransactionRepository
from backend.interface_adapters.controllers import auth_router, transaction_router


def create_app() -> FastAPI:
    repository = InMemoryTransactionRepository()
    app = FastAPI(title="Finova API")

    allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in allowed_origins if origin.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router())
    app.include_router(
        transaction_router(
            create_transaction=CreateTransaction(repository),
            list_transactions=ListTransactions(repository),
        )
    )
    return app


app = create_app()
