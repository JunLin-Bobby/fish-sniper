from typing import Any

import httpx
from google.auth.transport import requests
from google.oauth2 import id_token

from app.core.config import Settings

GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"


class GoogleOAuthError(RuntimeError):
    pass


class GoogleOAuthConfigurationError(GoogleOAuthError):
    pass


class GoogleOAuthTokenExchangeError(GoogleOAuthError):
    pass


class GoogleOAuthIdentityError(GoogleOAuthError):
    pass


async def exchange_authorization_code_for_google_tokens(
    settings: Settings,
    *,
    code: str,
    code_verifier: str,
    redirect_uri: str,
) -> dict[str, Any]:
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise GoogleOAuthConfigurationError("Google OAuth client credentials are not configured.")
    if redirect_uri != settings.google_oauth_redirect_uri:
        raise GoogleOAuthTokenExchangeError("OAuth redirect URI does not match this environment.")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            GOOGLE_TOKEN_ENDPOINT,
            data={
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "code": code,
                "code_verifier": code_verifier,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )

    if response.status_code >= 400:
        raise GoogleOAuthTokenExchangeError("Google rejected the authorization code exchange.")

    token_payload = response.json()
    if not token_payload.get("id_token"):
        raise GoogleOAuthTokenExchangeError("Google token response did not include an id_token.")
    return token_payload


def verify_google_id_token(settings: Settings, *, google_id_token: str) -> dict[str, Any]:
    try:
        claims = id_token.verify_oauth2_token(
            google_id_token,
            requests.Request(),
            settings.google_oauth_client_id,
        )
    except ValueError as error:
        raise GoogleOAuthIdentityError("Google id_token could not be verified.") from error

    if claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise GoogleOAuthIdentityError("Google id_token issuer is invalid.")
    if claims.get("aud") != settings.google_oauth_client_id:
        raise GoogleOAuthIdentityError("Google id_token audience is invalid.")
    if claims.get("email_verified") is not True:
        raise GoogleOAuthIdentityError("Google account email is not verified.")
    if not claims.get("sub") or not claims.get("email"):
        raise GoogleOAuthIdentityError("Google id_token is missing required identity claims.")

    return claims
