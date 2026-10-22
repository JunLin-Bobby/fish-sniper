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
from app.db.errors import DatabaseUnavailableError
from app.users.dependencies import UsersRepositoryDependency

router = APIRouter(prefix="/auth", tags=["auth"])


# 接收前端 callback 取得的授權碼，完成登入流程並將錯誤轉成對應的 HTTP 狀態碼。
@router.post("/google/exchange", response_model=AuthTokenResponse)
async def exchange_google_authorization_code(
    payload: GoogleOAuthExchangeRequest,
    users_repository: UsersRepositoryDependency,
    settings: Settings = Depends(get_settings),
) -> AuthTokenResponse:
    """接收 Google authorization code，完成內部 user 建立與 FishSniper token 簽發。"""

    try:
        return await exchange_google_oauth_code(settings, payload, users_repository)
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
    except DatabaseUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User database is temporarily unavailable.",
        ) from error
