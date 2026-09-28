from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt import JwtAuthenticationError, JwtConfigurationError, decode_access_token
from app.core.config import Settings, get_settings
from app.db.dependencies import UsersRepositoryDependency
from app.db.errors import DatabaseUnavailableError
from app.db.users import UserRecord

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    users_repository: UsersRepositoryDependency,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> UserRecord:
    """驗證 Bearer JWT、載入對應 user，並將使用者注入 protected route。"""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="FishSniper access token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = decode_access_token(settings, access_token=credentials.credentials)
        user = await users_repository.get_user_by_id(claims.user_id)
    except JwtConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except DatabaseUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User database is temporarily unavailable.",
        ) from error
    except JwtAuthenticationError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The user for this access token no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


CurrentUserDependency = Annotated[UserRecord, Depends(get_current_user)]
