"""JWT access tokens for FishSniper users."""

# ---------------------------------------------------------------------------
# JWT 為何同時放 UUID（sub）與 email？
#
#   sub — 代表資料庫裡的使用者 id，protected route 用它確認「你是誰」、查詢你的資料；
#         刪除帳號後 token 可能尚未過期，仍會用 sub 查 DB 並拒絕已刪除的帳號。
#
#   email — 代表登入用的信箱；API 限流用同一個 email 分桶。
#
# 授權與限流需求不同，因此拆成兩個 decode：一個驗證失敗就 401，一個只產生限流 key、
# 失敗時回傳固定字串（仍算進限流，但不代替登入檢查）。
# ---------------------------------------------------------------------------

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from fastapi import HTTPException, status

from auth.email import normalize_email
from shared_infras.settings import AppSettings


def issue_access_token_jwt_for_fish_sniper_user_id(
    *,
    fish_sniper_user_id: UUID,
    normalized_email_address: str,
    fish_sniper_backend_settings: AppSettings,
) -> str:
    """Sign a JWT for the user id and normalized email (rate-limit key and auditing)."""

    now_utc = datetime.now(tz=UTC)
    expire_utc = now_utc + timedelta(days=fish_sniper_backend_settings.jwt_expire_days)
    # sub 供授權查 DB；email 供限流與紀錄登入身份
    payload = {
        "sub": str(fish_sniper_user_id),
        "email": normalized_email_address,
        "iat": int(now_utc.timestamp()),
        "exp": int(expire_utc.timestamp()),
    }
    return jwt.encode(
        payload,
        fish_sniper_backend_settings.jwt_secret,
        algorithm=fish_sniper_backend_settings.jwt_algorithm,
    )


def decode_fish_sniper_user_id_from_access_token_jwt(
    *,
    access_token_jwt: str,
    fish_sniper_backend_settings: AppSettings,
) -> UUID:
    """Validate JWT and return the embedded user id (authorization only — not for rate limits)."""

    try:
        # 用 jwt_secret 驗簽，確認 token 由本系統簽發且未被竄改
        decoded_payload = jwt.decode(
            access_token_jwt,
            fish_sniper_backend_settings.jwt_secret,
            algorithms=[fish_sniper_backend_settings.jwt_algorithm],
        )
        # 授權綁定 DB 主鍵 UUID（sub），不用 email（信箱可能變更，且非所有表的查詢鍵）
        subject = decoded_payload.get("sub")
        if not subject or not isinstance(subject, str):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token subject",
            )
        return UUID(subject)

    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token expired",
        ) from exc
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        ) from exc


def decode_fish_sniper_rate_limit_key_from_access_token_jwt(
    *,
    access_token_jwt: str,
    fish_sniper_backend_settings: AppSettings,
) -> str:
    """Decode JWT without raising HTTPException — used only for rate-limit keying."""

    try:
        # 與授權 decode 相同驗簽；這裡只為 slowapi 產生 key，失敗不回 401
        decoded_payload = jwt.decode(
            access_token_jwt,
            fish_sniper_backend_settings.jwt_secret,
            algorithms=[fish_sniper_backend_settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        # 過期 token 仍計入限流，避免靠過期 token 繞過次數上限
        return "__fish_sniper_expired_jwt__"
    except jwt.InvalidTokenError:
        # 無效 token 歸入同一類 bucket
        return "__fish_sniper_invalid_jwt__"

    email_claim = decoded_payload.get("email")
    if isinstance(email_claim, str) and email_claim.strip():
        # 與登入限流相同：正規化後的 email 作為「同一帳號」的 key
        return normalize_email(email_claim)

    # [已停用] 早期 token payload 只有 sub、沒有 email 時，曾用 legacy_sub:{uuid} 限流。
    # 現行簽發一定包含 email；舊 token 超過 jwt_expire_days 後應已失效，
    # 故保留程式供參考、不再執行。
    # 若 token 合法但缺 email，改回傳下方 sentinel（多人共用同一限流桶，不影響登入授權）。
    #
    # subject = decoded_payload.get("sub")
    # if isinstance(subject, str) and subject.strip():
    #     return f"legacy_sub:{subject.strip()}"

    return "__fish_sniper_missing_jwt_claims__"
