"""Orchestrate the Google OAuth exchange flow.

Steps (matches design spec 禮2 / 禮5):

1. Validate ``redirect_uri`` against the configured whitelist.
2. Call Google's token endpoint (PKCE) ??``id_token``.
3. Verify ``id_token`` signature + claims via JWKS.
4. Gate on ``email_verified is True``.
5. Find or create a ``users`` row by normalized email.
6. Issue an access JWT and return ``is_new_user``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from app.auth.email import normalize_email
from app.auth.google_id_token import (
    GoogleIdTokenInvalidError,
    GoogleJwksKeyResolver,
    GoogleVerifiedIdentity,
    verify_google_id_token_and_extract_identity,
)
from app.auth.google_oauth import (
    GoogleOAuthClientError,
    GoogleOAuthCodeRejectedError,
    GoogleOAuthIdentityServiceUnavailableError,
)
from app.auth.jwt import issue_access_token
from app.auth.schemas import LoginResponseBody
from app.core.settings import AppSettings
from app.db.ports import PersistencePort

logger = logging.getLogger(__name__)


class GoogleOAuthExchangeConfigurationError(Exception):
    """Backend is missing required Google OAuth settings ??HTTP 500."""


class GoogleOAuthExchangeRedirectUriRejectedError(Exception):
    """Caller-supplied redirect_uri is not in the configured whitelist ??HTTP 400."""


class GoogleOAuthExchangeEmailNotVerifiedError(Exception):
    """Google asserts email_verified != true for this account ??HTTP 403."""


def _parse_redirect_uri_whitelist(*, raw_value: str) -> list[str]:
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def perform_google_oauth_exchange(
    *,
    authorization_code: str,
    pkce_code_verifier: str,
    redirect_uri: str,
    settings: AppSettings,
    persistence: PersistencePort,
    reference_time_utc: datetime,
    google_oauth_token_exchange_callable: Callable[..., dict[str, Any]],
    google_jwks_key_resolver: GoogleJwksKeyResolver,
) -> LoginResponseBody:
    """Run steps 1?? of the Google OAuth identity flow and return an access JWT."""

    client_id = settings.google_oauth_client_id
    client_secret = settings.google_oauth_client_secret
    if not client_id or not client_secret:
        logger.error("Google OAuth settings missing (client_id or client_secret unset)")
        raise GoogleOAuthExchangeConfigurationError(
            "Google OAuth is not configured for this environment"
        )

    allowed_redirect_uris = _parse_redirect_uri_whitelist(
        raw_value=settings.google_oauth_allowed_redirect_uris,
    )
    if redirect_uri not in allowed_redirect_uris:
        raise GoogleOAuthExchangeRedirectUriRejectedError(
            "redirect_uri is not in the allowed list"
        )

    token_response = google_oauth_token_exchange_callable(
        authorization_code=authorization_code,
        pkce_code_verifier=pkce_code_verifier,
        redirect_uri=redirect_uri,
        google_oauth_client_id=client_id,
        google_oauth_client_secret=client_secret,
    )
    id_token_value = token_response.get("id_token")
    if not isinstance(id_token_value, str) or not id_token_value.strip():
        raise GoogleOAuthCodeRejectedError(
            "Google token response did not include an id_token"
        )

    identity: GoogleVerifiedIdentity = verify_google_id_token_and_extract_identity(
        id_token=id_token_value,
        google_oauth_client_id=client_id,
        reference_time_utc=reference_time_utc,
        jwks_key_resolver=google_jwks_key_resolver,
    )
    if identity.email_verified is not True:
        raise GoogleOAuthExchangeEmailNotVerifiedError(
            "Google account email is not verified"
        )

    normalized_email_address = normalize_email(identity.email)

    existing_user_row = persistence.fetch_user_row_by_normalized_email(
        normalized_email_address=normalized_email_address,
    )
    if existing_user_row is None:
        created_user_row = persistence.insert_user_row_for_normalized_email(
            normalized_email_address=normalized_email_address,
        )
        user_id = created_user_row.user_id
        is_new_user = True
    else:
        user_id = existing_user_row.user_id
        is_new_user = False

    access_token = issue_access_token(
        user_id=user_id,
        normalized_email_address=normalized_email_address,
        settings=settings,
    )
    return LoginResponseBody(access_token=access_token, is_new_user=is_new_user)


__all__ = [
    "GoogleOAuthClientError",
    "GoogleOAuthCodeRejectedError",
    "GoogleOAuthExchangeConfigurationError",
    "GoogleOAuthExchangeEmailNotVerifiedError",
    "GoogleOAuthExchangeRedirectUriRejectedError",
    "GoogleOAuthIdentityServiceUnavailableError",
    "GoogleIdTokenInvalidError",
    "perform_google_oauth_exchange",
]
