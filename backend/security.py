"""Authentication dependencies for protected routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status

from auth.jwt_tokens import decode_fish_sniper_user_id_from_access_token_jwt
from deps import get_fish_sniper_persistence_port
from persistence.errors import FishSniperPersistenceUnavailableError
from persistence.port import FishSniperPersistencePort
from settings import FishSniperBackendSettings, get_fish_sniper_backend_settings


def _ensure_bearer_authorization_header_or_skip_auth(
    authorization: Annotated[str | None, Header()] = None,
    fish_sniper_backend_settings: Annotated[
        FishSniperBackendSettings,
        Depends(get_fish_sniper_backend_settings),
    ] = ...,
) -> None:
    """Reject missing Bearer before any DB dependency runs (401 without Supabase in CI)."""

    if fish_sniper_backend_settings.skip_auth:
        return
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def get_current_fish_sniper_user_id_from_authorization_header(
    _: Annotated[None, Depends(_ensure_bearer_authorization_header_or_skip_auth)],
    authorization: Annotated[str | None, Header()] = None,
    fish_sniper_backend_settings: Annotated[
        FishSniperBackendSettings,
        Depends(get_fish_sniper_backend_settings),
    ] = ...,
    fish_sniper_persistence: Annotated[
        FishSniperPersistencePort,
        Depends(get_fish_sniper_persistence_port),
    ] = ...,
) -> UUID:
    """Resolve the caller's user id from `Authorization: Bearer`, or SKIP_AUTH in dev."""

    if fish_sniper_backend_settings.skip_auth:
        return UUID(fish_sniper_backend_settings.skip_auth_dev_user_id)

    access_token_jwt = authorization.removeprefix("Bearer ").strip()
    fish_sniper_user_id = decode_fish_sniper_user_id_from_access_token_jwt(
        access_token_jwt=access_token_jwt,
        fish_sniper_backend_settings=fish_sniper_backend_settings,
    )
    # JWT signature + exp only prove the token was issued by us; they do not reflect
    # account lifecycle. After DELETE /users/account the user row is gone but the JWT
    # may remain valid until jwt_expire_days. This lookup rejects those tokens (401)
    # so deleted accounts cannot keep calling protected routes. Cost: one DB read per
    # authenticated request; alternatives later include token_version or a denylist.
    try:
        user_row = fish_sniper_persistence.fetch_user_row_for_user_id(
            fish_sniper_user_id=fish_sniper_user_id,
        )
    except FishSniperPersistenceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Database is temporarily unavailable"},
        ) from exc
    if user_row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return fish_sniper_user_id


FishSniperUserIdDep = Annotated[
    UUID,
    Depends(get_current_fish_sniper_user_id_from_authorization_header),
]
