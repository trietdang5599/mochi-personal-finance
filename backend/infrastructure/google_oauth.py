from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import secrets
from urllib.parse import urlencode, urlparse

import requests
from dotenv import load_dotenv


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
class GoogleOAuthConfig:
    client_id: str | None
    client_secret: str | None
    redirect_uri: str
    frontend_url: str

    @classmethod
    def from_env(cls) -> "GoogleOAuthConfig":
        return cls(
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            redirect_uri=os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback"),
            frontend_url=os.getenv("FRONTEND_URL", "http://localhost:5173"),
        )


class GoogleOAuthService:
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"
    userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    revoke_url = "https://oauth2.googleapis.com/revoke"

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
            "scope": "openid email profile",
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
        except GoogleOAuthError as exc:
            return self._frontend_error_url(str(exc))

        return_to = self._return_to_from_state(state)
        params = urlencode(
            {
                "auth": "google_success",
                "token": token["access_token"],
                "username": user.name,
                "email": user.email,
                "picture": user.picture,
                "sub": user.sub,
                "provider": user.provider,
            }
        )
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
