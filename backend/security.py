"""Authentication dependencies for protected routes.

Protected route 在參數列宣告 FishSniperUserIdDep 即可；FastAPI 會在 handler 執行前
依序跑本模組的 Depends，失敗則直接 401/503，不進入 route 業務邏輯。
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status

from auth.jwt_tokens import decode_fish_sniper_user_id_from_access_token_jwt
from deps import FishSniperPersistenceDep
from persistence.errors import FishSniperPersistenceUnavailableError
from settings import FishSniperSettingsDep

# ---------------------------------------------------------------------------
# 前置檢查：Authorization header 格式（避免無 Bearer 時仍去連 DB）
# ---------------------------------------------------------------------------


def _ensure_bearer_authorization_header_or_skip_auth(
    authorization: Annotated[str | None, Header()] = None,
    fish_sniper_backend_settings: FishSniperSettingsDep = ...,
) -> None:
    """Reject missing Bearer before any DB dependency runs (401 without Supabase in CI)."""

    if fish_sniper_backend_settings.skip_auth:
        return
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


# ---------------------------------------------------------------------------
# 身分驗證：JWT → user id → DB 確認帳號仍存在
# ---------------------------------------------------------------------------


def get_current_fish_sniper_user_id_from_authorization_header(
    _: Annotated[None, Depends(_ensure_bearer_authorization_header_or_skip_auth)],
    authorization: Annotated[str | None, Header()] = None,  # 請求參數：Authorization header
    fish_sniper_backend_settings: FishSniperSettingsDep = ...,
    fish_sniper_persistence: FishSniperPersistenceDep = ...,
) -> UUID:
    """Resolve the caller's user id from `Authorization: Bearer`, or SKIP_AUTH in dev."""

    # 開發模式：略過 JWT，使用固定 dev user id
    if fish_sniper_backend_settings.skip_auth:
        return UUID(fish_sniper_backend_settings.skip_auth_dev_user_id)

    # 解析 JWT：驗簽 + 過期檢查，取出 sub（UUID）
    access_token_jwt = authorization.removeprefix("Bearer ").strip()
    fish_sniper_user_id = decode_fish_sniper_user_id_from_access_token_jwt(
        access_token_jwt=access_token_jwt,
        fish_sniper_backend_settings=fish_sniper_backend_settings,
    )

    # 呼叫 persistence：JWT 有效不代表帳號仍在（刪帳後 token 可能未過期）→ 查無 user 則 401
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


# 路由用型別別名：Annotated[UUID, Depends(...)]，各 protected route 直接注入
FishSniperUserIdDep = Annotated[
    UUID,
    Depends(get_current_fish_sniper_user_id_from_authorization_header),
]
