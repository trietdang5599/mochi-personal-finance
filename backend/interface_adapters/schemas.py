from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Protocol

from pydantic import BaseModel, Field

from backend.domain.entities import Transaction, TransactionType


class GoogleUserLike(Protocol):
    email: str
    name: str
    picture: str
    sub: str
    provider: str


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


class GoogleUserResponse(BaseModel):
    email: str
    name: str
    picture: str
    sub: str
    provider: str

    @classmethod
    def from_google_user(cls, user: GoogleUserLike) -> "GoogleUserResponse":
        return cls(
            email=user.email,
            name=user.name,
            picture=user.picture,
            sub=user.sub,
            provider=user.provider,
        )


class GoogleDriveFileResponse(BaseModel):
    id: str
    name: str
    mime_type: str
    download_path: str
    size: int | None = None


class GoogleDriveFileMetadataResponse(BaseModel):
    id: str
    name: str
    mime_type: str
    size: int | None = None
    is_google_sheet: bool
    is_excel_file: bool


class GoogleSheetMetadataResponse(BaseModel):
    spreadsheet_id: str
    title: str
    sheets: list[dict[str, Any]]


class GoogleSheetOverwriteRequest(BaseModel):
    range: str = Field(default="A1", min_length=1)
    values: list[list[Any]]
    clear_range: str | None = Field(default=None, min_length=1)
    value_input_option: str = Field(default="USER_ENTERED")


class GoogleSheetOverwriteResponse(BaseModel):
    spreadsheet_id: str
    updated_range: str
    updated_rows: int
    updated_columns: int
    updated_cells: int
    cleared_range: str | None = None


class GoogleSheetData(BaseModel):
    name: str = Field(min_length=1)
    values: list[list[Any]]


class GoogleSheetBatchOverwriteRequest(BaseModel):
    sheets: list[GoogleSheetData]
    value_input_option: str = Field(default="RAW")


class GoogleSheetBatchOverwriteResponse(BaseModel):
    spreadsheet_id: str
    added_sheets: list[str]
    cleared_ranges: list[str]
    total_updated_rows: int
    total_updated_columns: int
    total_updated_cells: int


class GoogleDriveOverwriteResponse(BaseModel):
    file_id: str
    size: int
