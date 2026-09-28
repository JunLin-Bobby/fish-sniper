from app.auth.google_oauth import (
    exchange_authorization_code_for_google_tokens,
    verify_google_id_token,
)
from app.auth.jwt import create_access_token
from app.auth.schemas import AuthTokenResponse, GoogleOAuthExchangeRequest
from app.core.config import Settings
from app.db.users import UsersRepository


# 統整 Google token 交換、身分驗證與 FishSniper access token 簽發三個步驟。
async def exchange_google_oauth_code(
    settings: Settings,
    payload: GoogleOAuthExchangeRequest,
    users_repository: UsersRepository,
) -> AuthTokenResponse:
    """驗證 Google identity、建立內部 user，並簽發以 user UUID 為 sub 的 JWT。"""

    google_tokens = await exchange_authorization_code_for_google_tokens(
        settings,
        code=payload.code,
        code_verifier=payload.code_verifier,
        redirect_uri=payload.redirect_uri,
    )
    google_claims = verify_google_id_token(settings, google_id_token=google_tokens["id_token"])


    display_name = google_claims.get("name")
    avatar_url = google_claims.get("picture")
    user = await users_repository.find_or_create_google_user(
        google_sub=str(google_claims["sub"]),
        email=str(google_claims["email"]),
        display_name=str(display_name) if display_name else None,
        avatar_url=str(avatar_url) if avatar_url else None,
    )


    access_token = create_access_token(
        settings,
        user_id=user.id,
        email=user.email,
    )
    return AuthTokenResponse(access_token=access_token)
