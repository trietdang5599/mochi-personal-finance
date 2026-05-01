from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import secrets
from urllib.parse import urlencode, urlparse

import requests
from dotenv import load_dotenv


def is_production() -> bool:
    return os.getenv("APP_ENV") == "production"


def env_value(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value:
        return value
    if is_production() and default is not None:
        raise GoogleOAuthError(f"{name} is not configured")
    return default


if not is_production():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class GoogleOAuthError(Exception):
    pass


@dataclass(frozen=True)
class GoogleUser:
    email: str
    name: str
    picture: str
    sub: str
    provider: str = "google"


@dataclass(frozen=True)
class GoogleDriveFile:
    id: str
    name: str
    mime_type: str
    download_path: str
    size: int | None = None


@dataclass(frozen=True)
class GoogleOAuthConfig:
    client_id: str | None
    client_secret: str | None
    redirect_uri: str
    frontend_url: str
    drive_file_id: str | None
    drive_file_name: str | None
    drive_download_dir: Path

    @classmethod
    def from_env(cls) -> "GoogleOAuthConfig":
        return cls(
            client_id=env_value("GOOGLE_CLIENT_ID"),
            client_secret=env_value("GOOGLE_CLIENT_SECRET"),
            redirect_uri=env_value("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback") or "",
            frontend_url=env_value("FRONTEND_URL", "http://localhost:5173") or "",
            drive_file_id=os.getenv("GOOGLE_DRIVE_FILE_ID"),
            drive_file_name=os.getenv("GOOGLE_DRIVE_FILE_NAME"),
            drive_download_dir=Path(
                os.getenv(
                    "GOOGLE_DRIVE_DOWNLOAD_DIR",
                    str(Path(__file__).resolve().parents[1] / "storage" / "google_drive"),
                )
            ),
        )


class GoogleOAuthService:
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"
    userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    revoke_url = "https://oauth2.googleapis.com/revoke"
    drive_files_url = "https://www.googleapis.com/drive/v3/files"
    drive_readonly_scope = "https://www.googleapis.com/auth/drive.readonly"
    spreadsheets_scope = "https://www.googleapis.com/auth/spreadsheets"
    google_sheets_mime_type = "application/vnd.google-apps.spreadsheet"
    excel_mime_types = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        google_sheets_mime_type,
    )

    def __init__(self, config: GoogleOAuthConfig | None = None) -> None:
        self.config = config or GoogleOAuthConfig.from_env()

    def build_login_url(self, return_to: str | None = None) -> str:
        self._require_client_id()
        state = secrets.token_urlsafe(24)
        if return_to:
            state = f"{state}:{return_to}"

        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": f"openid email profile {self.drive_readonly_scope} {self.spreadsheets_scope}",
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{self.auth_url}?{urlencode(params)}"

    def callback_redirect_url(self, code: str | None, state: str | None, error: str | None) -> str:
        if error:
            return self._frontend_error_url(error)
        if not code:
            return self._frontend_error_url("missing_code")

        try:
            token = self.exchange_code(code)
            user = self.fetch_userinfo(token["access_token"])
            drive_file = self.download_configured_excel(token["access_token"])
        except GoogleOAuthError as exc:
            return self._frontend_error_url(str(exc))

        return_to = self._return_to_from_state(state)
        redirect_params = {
            "auth": "google_success",
            "token": token["access_token"],
            "username": user.name,
            "email": user.email,
            "picture": user.picture,
            "sub": user.sub,
            "provider": user.provider,
        }
        if drive_file:
            redirect_params.update(
                {
                    "drive_download": "success",
                    "drive_file_id": drive_file.id,
                    "drive_file_name": drive_file.name,
                }
            )
        else:
            redirect_params["drive_download"] = "skipped"

        params = urlencode(redirect_params)
        return f"{return_to}?{params}"

    def exchange_code(self, code: str) -> dict[str, str]:
        self._require_client_id()
        self._require_client_secret()

        response = requests.post(
            self.token_url,
            data={
                "code": code,
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "redirect_uri": self.config.redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise GoogleOAuthError("google_token_invalid_response") from exc
        if response.status_code != 200 or "access_token" not in payload:
            raise GoogleOAuthError(payload.get("error_description") or payload.get("error") or "google_token_failed")
        return payload

    def fetch_userinfo(self, access_token: str) -> GoogleUser:
        response = requests.get(
            self.userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise GoogleOAuthError("google_userinfo_invalid_response") from exc
        if response.status_code != 200:
            raise GoogleOAuthError(payload.get("error_description") or payload.get("error") or "google_userinfo_failed")

        return GoogleUser(
            email=payload.get("email", ""),
            name=payload.get("name") or payload.get("email") or "Unknown",
            picture=payload.get("picture", ""),
            sub=payload.get("sub", ""),
        )

    def revoke_token(self, access_token: str) -> None:
        response = requests.post(
            self.revoke_url,
            params={"token": access_token},
            timeout=10,
        )
        if response.status_code not in (200, 400):
            raise GoogleOAuthError("google_revoke_failed")

    def download_configured_excel(self, access_token: str) -> GoogleDriveFile | None:
        if self.config.drive_file_id:
            metadata = self.fetch_drive_file_metadata(access_token, self.config.drive_file_id)
        elif self.config.drive_file_name:
            metadata = self.find_excel_file(access_token, self.config.drive_file_name)
        else:
            return None

        if not metadata:
            raise GoogleOAuthError("google_drive_excel_file_not_found")

        return self.download_excel_file(access_token, metadata)

    def find_excel_file(self, access_token: str, file_name: str | None = None) -> dict[str, object] | None:
        mime_query = " or ".join(f"mimeType='{mime_type}'" for mime_type in self.excel_mime_types)
        query = f"trashed=false and ({mime_query})"
        if file_name:
            query = f"{query} and name='{self._escape_drive_query_value(file_name)}'"

        response = requests.get(
            self.drive_files_url,
            headers=self._authorization_header(access_token),
            params={
                "q": query,
                "fields": "files(id,name,mimeType,size,modifiedTime)",
                "orderBy": "modifiedTime desc",
                "pageSize": 1,
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
            },
            timeout=10,
        )
        payload = self._json_payload(response, "google_drive_files_invalid_response")
        if response.status_code != 200:
            raise GoogleOAuthError(self._google_error_message(payload, "google_drive_files_failed"))

        files = payload.get("files", [])
        if not isinstance(files, list) or not files:
            return None
        first_file = files[0]
        return first_file if isinstance(first_file, dict) else None

    def fetch_drive_file_metadata(self, access_token: str, file_id: str) -> dict[str, object]:
        response = requests.get(
            f"{self.drive_files_url}/{file_id}",
            headers=self._authorization_header(access_token),
            params={
                "fields": "id,name,mimeType,size",
                "supportsAllDrives": "true",
            },
            timeout=10,
        )
        payload = self._json_payload(response, "google_drive_file_invalid_response")
        if response.status_code != 200:
            raise GoogleOAuthError(self._google_error_message(payload, "google_drive_file_failed"))
        return payload

    def download_excel_file(self, access_token: str, metadata: dict[str, object]) -> GoogleDriveFile:
        file_id = str(metadata.get("id") or "")
        name = str(metadata.get("name") or file_id or "google-drive-file")
        mime_type = str(metadata.get("mimeType") or "")
        if not file_id:
            raise GoogleOAuthError("google_drive_file_missing_id")
        if mime_type not in self.excel_mime_types:
            raise GoogleOAuthError("google_drive_file_is_not_excel")

        if mime_type == self.google_sheets_mime_type:
            url = f"{self.drive_files_url}/{file_id}/export"
            params = {"mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
            filename = f"{Path(name).stem}.xlsx"
        else:
            url = f"{self.drive_files_url}/{file_id}"
            params = {"alt": "media", "supportsAllDrives": "true"}
            filename = name

        response = requests.get(
            url,
            headers=self._authorization_header(access_token),
            params=params,
            timeout=30,
            stream=True,
        )
        if response.status_code != 200:
            payload = self._safe_json_payload(response)
            raise GoogleOAuthError(self._google_error_message(payload, "google_drive_download_failed"))

        self.config.drive_download_dir.mkdir(parents=True, exist_ok=True)
        download_path = self.config.drive_download_dir / self._safe_filename(filename)
        with download_path.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)

        size = metadata.get("size")
        return GoogleDriveFile(
            id=file_id,
            name=name,
            mime_type=mime_type,
            download_path=str(download_path),
            size=int(size) if isinstance(size, str) and size.isdigit() else None,
        )

    def _frontend_error_url(self, message: str) -> str:
        return f"{self.config.frontend_url}?{urlencode({'auth': 'google_error', 'message': message})}"

    def _return_to_from_state(self, state: str | None) -> str:
        if state and ":" in state:
            candidate = state.split(":", 1)[1]
            if self._same_origin(candidate, self.config.frontend_url):
                return candidate
        return self.config.frontend_url

    def _same_origin(self, value: str, expected: str) -> bool:
        value_url = urlparse(value)
        expected_url = urlparse(expected)
        return value_url.scheme == expected_url.scheme and value_url.netloc == expected_url.netloc

    def _require_client_id(self) -> None:
        if not self.config.client_id:
            raise GoogleOAuthError("GOOGLE_CLIENT_ID is not configured")

    def _require_client_secret(self) -> None:
        if not self.config.client_secret:
            raise GoogleOAuthError("GOOGLE_CLIENT_SECRET is not configured")

    def _authorization_header(self, access_token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {access_token}"}

    def _json_payload(self, response: requests.Response, error_message: str) -> dict[str, object]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise GoogleOAuthError(error_message) from exc
        return payload if isinstance(payload, dict) else {}

    def _safe_json_payload(self, response: requests.Response) -> dict[str, object]:
        try:
            payload = response.json()
        except ValueError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _google_error_message(self, payload: dict[str, object], fallback: str) -> str:
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message:
                return message
        if isinstance(error, str) and error:
            return error
        error_description = payload.get("error_description")
        return error_description if isinstance(error_description, str) and error_description else fallback

    def _safe_filename(self, value: str) -> str:
        filename = Path(value).name.strip()
        safe = "".join(character if character.isalnum() or character in "._- " else "_" for character in filename)
        return safe or "google-drive-file.xlsx"

    def _escape_drive_query_value(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace("'", "\\'")
