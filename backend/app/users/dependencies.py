from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.db.client import create_supabase_rest_client
from app.db.errors import DatabaseConfigurationError
from app.users.supabase_repository import SupabaseUsersRepository


def get_users_repository(settings: Settings = Depends(get_settings)) -> SupabaseUsersRepository:
    """直接建立 request 使用的 Supabase repository，並將缺少設定轉成 HTTP 503。"""

    try:
        client = create_supabase_rest_client(settings)
    except DatabaseConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    return SupabaseUsersRepository(client)


UsersRepositoryDependency = Annotated[SupabaseUsersRepository, Depends(get_users_repository)]
