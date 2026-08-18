"""HTTPS client for Google's OAuth 2.0 token endpoint (identity-only flow).

Wraps a single `POST https://oauth2.googleapis.com/token` round-trip with PKCE
and raises typed errors so the calling route can map cleanly to HTTP status:

* ``GoogleOAuthCodeRejectedError`` ??401 (Google refused the code or returned 4xx /
  the response lacks ``id_token``).
* ``GoogleOAuthIdentityServiceUnavailableError`` ??502 (5xx, network error, timeout).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GOOGLE_OAUTH_TOKEN_ENDPOINT_URL = "https://oauth2.googleapis.com/token"
GOOGLE_OAUTH_TOKEN_ENDPOINT_TIMEOUT_SECONDS = 8.0


class GoogleOAuthClientError(Exception):
    """Base class for Google OAuth client failures."""


class GoogleOAuthCodeRejectedError(GoogleOAuthClientError):
    """Raised when Google rejects the authorization code (4xx) or omits ``id_token``."""


class GoogleOAuthIdentityServiceUnavailableError(GoogleOAuthClientError):
    """Raised when the Google token endpoint is unreachable, times out, or returns 5xx."""


def exchange_authorization_code_for_token_response(
    *,
    authorization_code: str,
    pkce_code_verifier: str,
    redirect_uri: str,
    google_oauth_client_id: str,
    google_oauth_client_secret: str,
) -> dict[str, Any]:
    """Exchange an authorization code (+ PKCE verifier) for Google's token response."""

    form_data = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "client_id": google_oauth_client_id,
        "client_secret": google_oauth_client_secret,
        "redirect_uri": redirect_uri,
        "code_verifier": pkce_code_verifier,
    }
    try:
        response = httpx.post(
            GOOGLE_OAUTH_TOKEN_ENDPOINT_URL,
            data=form_data,
            timeout=GOOGLE_OAUTH_TOKEN_ENDPOINT_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        logger.exception("Google token endpoint network error")
        raise GoogleOAuthIdentityServiceUnavailableError(
            "Google token endpoint network error"
        ) from exc

    if 500 <= response.status_code < 600:
        logger.error("Google token endpoint returned 5xx: %s", response.status_code)
        raise GoogleOAuthIdentityServiceUnavailableError(
            f"Google token endpoint returned {response.status_code}"
        )

    if 400 <= response.status_code < 500:
        # Google returns a JSON body like {"error": "invalid_grant",
        # "error_description": "..."} ??surface it so the operator can tell
        # invalid_grant (code reuse / expired) apart from redirect_uri_mismatch /
        # invalid_client (bad credentials). PKCE verifier issues also land here.
        google_error_body_excerpt = response.text[:500] if response.text else "<empty>"
        logger.warning(
            "Google rejected authorization code: HTTP %s body=%s",
            response.status_code,
            google_error_body_excerpt,
        )
        raise GoogleOAuthCodeRejectedError(
            f"Google rejected authorization code (HTTP {response.status_code})"
        )

    try:
        payload: dict[str, Any] = response.json()
    except ValueError as exc:
        raise GoogleOAuthIdentityServiceUnavailableError(
            "Google token endpoint returned non-JSON body"
        ) from exc

    id_token_value = payload.get("id_token")
    if not isinstance(id_token_value, str) or not id_token_value.strip():
        raise GoogleOAuthCodeRejectedError(
            "Google token response did not include an id_token"
        )

    return payload
