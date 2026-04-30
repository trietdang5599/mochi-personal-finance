from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import RedirectResponse

from backend.application.use_cases import CreateTransaction, CreateTransactionInput, ListTransactions
from backend.infrastructure.google_oauth import GoogleOAuthError, GoogleOAuthService
from backend.interface_adapters.schemas import GoogleUserResponse, TransactionCreateRequest, TransactionResponse


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


def auth_router(google_oauth: GoogleOAuthService | None = None) -> APIRouter:
    google_oauth = google_oauth or GoogleOAuthService()
    router = APIRouter(prefix="/auth", tags=["auth"])

    @router.get("/google/login")
    def google_login(return_to: str | None = Query(default=None)) -> RedirectResponse:
        try:
            return RedirectResponse(google_oauth.build_login_url(return_to=return_to))
        except GoogleOAuthError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.get("/google/callback")
    def google_callback(code: str | None = None, state: str | None = None, error: str | None = None) -> RedirectResponse:
        return RedirectResponse(google_oauth.callback_redirect_url(code=code, state=state, error=error))

    @router.get("/google/me", response_model=GoogleUserResponse)
    def google_me(authorization: str | None = Header(default=None)) -> GoogleUserResponse:
        access_token = bearer_token_from_header(authorization)
        try:
            return GoogleUserResponse.from_google_user(google_oauth.fetch_userinfo(access_token))
        except GoogleOAuthError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    @router.post("/google/logout")
    def google_logout(authorization: str | None = Header(default=None)) -> dict[str, str]:
        access_token = bearer_token_from_header(authorization)
        try:
            google_oauth.revoke_token(access_token)
        except GoogleOAuthError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"message": "Logout google success"}

    return router


def bearer_token_from_header(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return authorization.removeprefix("Bearer ").strip()
