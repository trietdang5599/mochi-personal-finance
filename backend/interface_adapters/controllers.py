from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from backend.application.use_cases import CreateTransaction, CreateTransactionInput, ListTransactions
from backend.infrastructure.google_oauth import GoogleAPIError, GoogleOAuthError, GoogleOAuthService
from backend.interface_adapters.schemas import (
    GoogleDriveFileResponse,
    GoogleDriveFileMetadataResponse,
    GoogleDriveOverwriteResponse,
    GoogleSheetBatchOverwriteRequest,
    GoogleSheetBatchOverwriteResponse,
    GoogleSheetMetadataResponse,
    GoogleSheetOverwriteRequest,
    GoogleSheetOverwriteResponse,
    GoogleUserResponse,
    TransactionCreateRequest,
    TransactionResponse,
)


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
    def google_login(
        return_to: str | None = Query(default=None),
        scope: str | None = Query(default=None),
        prompt: str | None = Query(default=None),
    ) -> RedirectResponse:
        try:
            return RedirectResponse(google_oauth.build_login_url(return_to=return_to, requested_scope=scope, prompt=prompt))
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

    @router.post("/google/drive/excel", response_model=GoogleDriveFileResponse)
    def google_drive_excel(authorization: str | None = Header(default=None)) -> GoogleDriveFileResponse:
        access_token = bearer_token_from_header(authorization)
        try:
            drive_file = google_oauth.download_configured_excel(access_token)
        except GoogleOAuthError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not drive_file:
            raise HTTPException(status_code=400, detail="GOOGLE_DRIVE_FILE_ID or GOOGLE_DRIVE_FILE_NAME is not configured")
        return GoogleDriveFileResponse(
            id=drive_file.id,
            name=drive_file.name,
            mime_type=drive_file.mime_type,
            download_path=drive_file.download_path,
            size=drive_file.size,
        )

    @router.get("/google/drive/files/{file_id}/metadata", response_model=GoogleDriveFileMetadataResponse)
    def google_drive_file_metadata(file_id: str, authorization: str | None = Header(default=None)) -> GoogleDriveFileMetadataResponse:
        access_token = bearer_token_from_header(authorization)
        try:
            metadata = google_oauth.fetch_drive_file_metadata(access_token, file_id)
        except GoogleAPIError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        except GoogleOAuthError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        mime_type = str(metadata.get("mimeType") or "")
        size = metadata.get("size")
        return GoogleDriveFileMetadataResponse(
            id=str(metadata.get("id") or file_id),
            name=str(metadata.get("name") or ""),
            mime_type=mime_type,
            size=int(size) if isinstance(size, str) and size.isdigit() else None,
            is_google_sheet=mime_type == google_oauth.google_sheets_mime_type,
            is_excel_file=mime_type in google_oauth.excel_mime_types,
        )

    @router.get("/google/sheets/{spreadsheet_id}/metadata", response_model=GoogleSheetMetadataResponse)
    def google_sheet_metadata(spreadsheet_id: str, authorization: str | None = Header(default=None)) -> GoogleSheetMetadataResponse:
        access_token = bearer_token_from_header(authorization)
        try:
            metadata = google_oauth.fetch_spreadsheet_metadata(access_token, spreadsheet_id)
        except GoogleAPIError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        except GoogleOAuthError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return GoogleSheetMetadataResponse(
            spreadsheet_id=str(metadata.get("spreadsheetId") or spreadsheet_id),
            title=str((metadata.get("properties") or {}).get("title") if isinstance(metadata.get("properties"), dict) else ""),
            sheets=metadata.get("sheets") if isinstance(metadata.get("sheets"), list) else [],
        )

    @router.put("/google/sheets/{spreadsheet_id}/values", response_model=GoogleSheetOverwriteResponse)
    def google_sheet_overwrite(
        spreadsheet_id: str,
        payload: GoogleSheetOverwriteRequest,
        authorization: str | None = Header(default=None),
    ) -> GoogleSheetOverwriteResponse:
        access_token = bearer_token_from_header(authorization)
        try:
            result = google_oauth.overwrite_spreadsheet_values(
                access_token=access_token,
                spreadsheet_id=spreadsheet_id,
                value_range=payload.range,
                values=payload.values,
                value_input_option=payload.value_input_option,
                clear_range=payload.clear_range,
            )
        except GoogleAPIError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        except GoogleOAuthError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return GoogleSheetOverwriteResponse(
            spreadsheet_id=str(result.get("spreadsheetId") or spreadsheet_id),
            updated_range=str(result.get("updatedRange") or payload.range),
            updated_rows=int(result.get("updatedRows") or 0),
            updated_columns=int(result.get("updatedColumns") or 0),
            updated_cells=int(result.get("updatedCells") or 0),
            cleared_range=str(result["clearedRange"]) if result.get("clearedRange") else None,
        )

    @router.put("/google/sheets/{spreadsheet_id}/overwrite", response_model=GoogleSheetBatchOverwriteResponse)
    def google_sheet_batch_overwrite(
        spreadsheet_id: str,
        payload: GoogleSheetBatchOverwriteRequest,
        authorization: str | None = Header(default=None),
    ) -> GoogleSheetBatchOverwriteResponse:
        access_token = bearer_token_from_header(authorization)
        try:
            result = google_oauth.overwrite_spreadsheet_sheets(
                access_token=access_token,
                spreadsheet_id=spreadsheet_id,
                sheets=[sheet.model_dump() for sheet in payload.sheets],
                value_input_option=payload.value_input_option,
            )
        except GoogleAPIError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        except GoogleOAuthError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return GoogleSheetBatchOverwriteResponse(
            spreadsheet_id=str(result.get("spreadsheetId") or spreadsheet_id),
            added_sheets=[str(item) for item in result.get("addedSheets", [])],
            cleared_ranges=[str(item) for item in result.get("clearedRanges", [])],
            total_updated_rows=int(result.get("totalUpdatedRows") or 0),
            total_updated_columns=int(result.get("totalUpdatedColumns") or 0),
            total_updated_cells=int(result.get("totalUpdatedCells") or 0),
        )

    @router.patch("/google/drive/files/{file_id}", response_model=GoogleDriveOverwriteResponse)
    async def google_drive_file_overwrite(
        file_id: str,
        request: Request,
        authorization: str | None = Header(default=None),
        content_type: str | None = Header(default=None),
    ) -> GoogleDriveOverwriteResponse:
        access_token = bearer_token_from_header(authorization)
        body = await request.body()
        try:
            google_oauth.overwrite_drive_file(
                access_token=access_token,
                file_id=file_id,
                content=body,
                content_type=content_type or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except GoogleAPIError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        except GoogleOAuthError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return GoogleDriveOverwriteResponse(file_id=file_id, size=len(body))

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
