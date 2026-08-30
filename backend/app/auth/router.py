from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.google_oauth import (
    GoogleOAuthConfigurationError,
    GoogleOAuthIdentityError,
    GoogleOAuthTokenExchangeError,
)
from app.auth.jwt import JwtConfigurationError
from app.auth.schemas import AuthTokenResponse, GoogleOAuthExchangeRequest
from app.auth.service import exchange_google_oauth_code
from app.core.config import Settings, get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google/exchange", response_model=AuthTokenResponse)
async def exchange_google_authorization_code(
    payload: GoogleOAuthExchangeRequest,
    settings: Settings = Depends(get_settings),
) -> AuthTokenResponse:
    try:
        return await exchange_google_oauth_code(settings, payload)
    except (GoogleOAuthConfigurationError, JwtConfigurationError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except GoogleOAuthTokenExchangeError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except GoogleOAuthIdentityError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        ) from error
