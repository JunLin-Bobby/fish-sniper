"""Authentication dependencies for protected routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status

from auth.jwt_tokens import decode_fish_sniper_user_id_from_access_token_jwt
from settings import FishSniperBackendSettings, get_fish_sniper_backend_settings


def get_current_fish_sniper_user_id_from_authorization_header(
    authorization: Annotated[str | None, Header()] = None,
    fish_sniper_backend_settings: Annotated[
        FishSniperBackendSettings,
        Depends(get_fish_sniper_backend_settings),
    ] = ...,
) -> UUID:
    """Resolve the caller's user id from `Authorization: Bearer`, or SKIP_AUTH in dev."""

    if fish_sniper_backend_settings.skip_auth:
        return UUID(fish_sniper_backend_settings.skip_auth_dev_user_id)

    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        
    access_token_jwt = authorization.removeprefix("Bearer ").strip()
    return decode_fish_sniper_user_id_from_access_token_jwt(
        access_token_jwt=access_token_jwt,
        fish_sniper_backend_settings=fish_sniper_backend_settings,
    )


FishSniperUserIdDep = Annotated[
    UUID,
    Depends(get_current_fish_sniper_user_id_from_authorization_header),
]
