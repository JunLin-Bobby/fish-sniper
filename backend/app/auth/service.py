from app.auth.google_oauth import (
    exchange_authorization_code_for_google_tokens,
    verify_google_id_token,
)
from app.auth.jwt import create_access_token
from app.auth.schemas import AuthTokenResponse, GoogleOAuthExchangeRequest
from app.core.config import Settings


async def exchange_google_oauth_code(
    settings: Settings,
    payload: GoogleOAuthExchangeRequest,
) -> AuthTokenResponse:
    google_tokens = await exchange_authorization_code_for_google_tokens(
        settings,
        code=payload.code,
        code_verifier=payload.code_verifier,
        redirect_uri=payload.redirect_uri,
    )
    google_claims = verify_google_id_token(settings, google_id_token=google_tokens["id_token"])
    access_token = create_access_token(
        settings,
        subject=f"google:{google_claims['sub']}",
        email=google_claims["email"],
    )
    return AuthTokenResponse(access_token=access_token)
