"""Authentication dependencies for protected routes.

Protected route ?典??詨?摰?? UserIdDep ?喳嚗astAPI ? handler ?瑁???
靘?頝璅∠???Depends嚗仃???湔 401/503嚗??脣 route 璆剖??摩??
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status

from app.auth.jwt import decode_user_id_from_access_token
from app.core.settings import AppSettings, SettingsDep, get_settings
from app.db.deps import get_persistence
from app.db.errors import PersistenceUnavailableError
from app.db.ports import PersistencePort

# ---------------------------------------------------------------------------
# ?蔭瑼Ｘ嚗uthorization header ?澆?嚗? Bearer ???駁?DB嚗?
# ---------------------------------------------------------------------------


def _ensure_bearer_authorization_header_or_skip_auth(
    authorization: Annotated[str | None, Header()] = None,
    settings: SettingsDep = ...,
) -> None:
    """Reject missing Bearer before any DB dependency runs (401 without Supabase in CI)."""

    if settings.skip_auth:
        return
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


# ---------------------------------------------------------------------------
# 頨怠?撽?嚗WT ??user id ??DB 蝣箄?撣唾?隞???
# ---------------------------------------------------------------------------


def get_current_user_id_from_authorization_header(
    _: Annotated[None, Depends(_ensure_bearer_authorization_header_or_skip_auth)],
    authorization: Annotated[str | None, Header()] = None,  # 隢??嚗uthorization header
    settings: Annotated[AppSettings, Depends(get_settings)] = ...,
    persistence: Annotated[PersistencePort, Depends(get_persistence)] = ...,
) -> UUID:
    """Resolve the caller's user id from `Authorization: Bearer`, or SKIP_AUTH in dev."""

    # ?璅∪?嚗??JWT嚗蝙?典摰?dev user id
    if settings.skip_auth:
        return UUID(settings.skip_auth_dev_user_id)

    # 閫?? JWT嚗?蝪?+ ??瑼Ｘ嚗???sub嚗UID嚗?
    access_token_jwt = authorization.removeprefix("Bearer ").strip()
    user_id = decode_user_id_from_access_token(
        access_token_jwt=access_token_jwt,
        settings=settings,
    )

    # ?澆 persistence嚗WT ??銝誨銵典董???剁??芸董敺?token ?航?芷??????亦 user ??401
    try:
        user_row = persistence.fetch_user_row_for_user_id(
            user_id=user_id,
        )
    except PersistenceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Database is temporarily unavailable"},
        ) from exc
    if user_row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user_id


# 頝舐?典??亙??Annotated[UUID, Depends(...)]嚗? protected route ?湔瘜典
UserIdDep = Annotated[
    UUID,
    Depends(get_current_user_id_from_authorization_header),
]
