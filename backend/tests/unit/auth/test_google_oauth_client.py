"""Unit tests for backend/auth/google_oauth_client.py (TDD RED ??GREEN)."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import httpx
import pytest

from app.auth.google_oauth import (
    GoogleOAuthCodeRejectedError,
    GoogleOAuthIdentityServiceUnavailableError,
    exchange_authorization_code_for_token_response,
)


class _FakeHttpxResponse:
    def __init__(self, *, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload

    @property
    def text(self) -> str:
        import json as _json

        return _json.dumps(self._payload)

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if 400 <= self.status_code < 600:
            raise httpx.HTTPStatusError(
                f"status {self.status_code}",
                request=httpx.Request("POST", "https://oauth2.googleapis.com/token"),
                response=httpx.Response(self.status_code),
            )


_PATCH_TARGET = "app.auth.google_oauth.httpx.post"


def _expected_form_data() -> dict[str, str]:
    return {
        "grant_type": "authorization_code",
        "code": "abc",
        "client_id": "cid",
        "client_secret": "sec",
        "redirect_uri": "http://localhost:5173/auth/google/callback",
        "code_verifier": "verifier",
    }


def test_exchange_returns_token_response_on_success() -> None:
    with patch(
        _PATCH_TARGET,
        return_value=_FakeHttpxResponse(
            status_code=200,
            payload={"id_token": "fake.jwt.id_token", "access_token": "ignored"},
        ),
    ) as mocked_post:
        result = exchange_authorization_code_for_token_response(
            authorization_code="abc",
            pkce_code_verifier="verifier",
            redirect_uri="http://localhost:5173/auth/google/callback",
            google_oauth_client_id="cid",
            google_oauth_client_secret="sec",
        )

    assert result["id_token"] == "fake.jwt.id_token"
    mocked_post.assert_called_once()
    _, kwargs = mocked_post.call_args
    assert kwargs["data"] == _expected_form_data()


def test_exchange_raises_rejected_when_google_returns_4xx() -> None:
    with patch(
        _PATCH_TARGET,
        return_value=_FakeHttpxResponse(
            status_code=400,
            payload={"error": "invalid_grant"},
        ),
    ):
        with pytest.raises(GoogleOAuthCodeRejectedError):
            exchange_authorization_code_for_token_response(
                authorization_code="abc",
                pkce_code_verifier="verifier",
                redirect_uri="http://localhost:5173/auth/google/callback",
                google_oauth_client_id="cid",
                google_oauth_client_secret="sec",
            )


def test_exchange_raises_unavailable_when_google_returns_5xx() -> None:
    with patch(
        _PATCH_TARGET,
        return_value=_FakeHttpxResponse(
            status_code=503,
            payload={},
        ),
    ):
        with pytest.raises(GoogleOAuthIdentityServiceUnavailableError):
            exchange_authorization_code_for_token_response(
                authorization_code="abc",
                pkce_code_verifier="verifier",
                redirect_uri="http://localhost:5173/auth/google/callback",
                google_oauth_client_id="cid",
                google_oauth_client_secret="sec",
            )


def test_exchange_raises_unavailable_on_network_error() -> None:
    with patch(
        _PATCH_TARGET,
        side_effect=httpx.ConnectError("connection refused"),
    ):
        with pytest.raises(GoogleOAuthIdentityServiceUnavailableError):
            exchange_authorization_code_for_token_response(
                authorization_code="abc",
                pkce_code_verifier="verifier",
                redirect_uri="http://localhost:5173/auth/google/callback",
                google_oauth_client_id="cid",
                google_oauth_client_secret="sec",
            )


def test_exchange_raises_rejected_when_id_token_missing() -> None:
    with patch(
        _PATCH_TARGET,
        return_value=_FakeHttpxResponse(
            status_code=200,
            payload={"access_token": "no_id_token_here"},
        ),
    ):
        with pytest.raises(GoogleOAuthCodeRejectedError):
            exchange_authorization_code_for_token_response(
                authorization_code="abc",
                pkce_code_verifier="verifier",
                redirect_uri="http://localhost:5173/auth/google/callback",
                google_oauth_client_id="cid",
                google_oauth_client_secret="sec",
            )
