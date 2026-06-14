"""Per-email rate limiting (slowapi for Bearer routes; limits MovingWindow for auth body routes)."""

# ---------------------------------------------------------------------------
# 限流模組概覽
#
# 兩套機制並存：
#   1. slowapi（fish_sniper_api_limiter）— 掛在需 JWT 的路由上，以 email 為 key。
#   2. limits MovingWindow — 用在 auth 請求體路由（OTP / Google OAuth），key 為 email 或 IP。
#
# 對外主要入口：
#   - fish_sniper_api_limiter.limit(...)     → 路由 decorator（Bearer 保護的 API）
#   - enforce_*_rate_limit_or_raise_429      → 路由 handler 內手動檢查（auth 流程）
#   - fish_sniper_handle_rate_limit_exceeded → main.py 註冊的全域 429 處理
# ---------------------------------------------------------------------------

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, Request, status
from limits import parse
from limits.storage import memory as limits_memory
from limits.strategies import MovingWindowRateLimiter
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from starlette import config as starlette_config
from starlette.responses import JSONResponse

from auth.jwt_tokens import decode_fish_sniper_rate_limit_key_from_access_token_jwt
from settings import FishSniperBackendSettings, get_fish_sniper_backend_settings
from text_normalization import normalize_email_address_for_otp_login

# ---------------------------------------------------------------------------
# 私有：Starlette .env 讀取 patch（僅供 slowapi 初始化期間使用）
# slowapi 建立 Limiter 時會讀 .env；Windows 預設 cp950 可能炸 UTF-8 的 .env。
# ---------------------------------------------------------------------------

_original_starlette_config_read_file = starlette_config.Config._read_file


# 以 UTF-8 解析 .env 行，取代 Starlette Config 的預設讀檔邏輯。
def _read_env_file_with_utf8_encoding(
    self: starlette_config.Config,
    file_name: str | Path,
) -> dict[str, str]:
    file_values: dict[str, str] = {}
    with open(file_name, encoding="utf-8") as input_file:
        for line in input_file.readlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("\"'")
                file_values[key] = value
    return file_values


starlette_config.Config._read_file = _read_env_file_with_utf8_encoding


# ---------------------------------------------------------------------------
# 模組級基礎設施（私有 storage / 預先 parse 的限流規則）
# auth 路由（OTP 發送／驗證、Google OAuth）在使用者登入前執行，
# 此時還沒有 JWT token，所以無法用 slowapi decorator 從 token 拿 email 當 key。
# 改用 limits 套件的 MovingWindowRateLimiter 手動檢查：
# 在每個 route handler 內呼叫 .hit()，超過限制就直接拋出 429。
# ---------------------------------------------------------------------------

# 第一組：storage — 計數器存在哪裡
_auth_route_rate_limit_storage = limits_memory.MemoryStorage()
# 就是一個 in-memory 的字典，記錄每個 email/IP 打了幾次

# 第二組：strategy — 用什麼演算法計算限流
_auth_route_moving_window_rate_limiter = MovingWindowRateLimiter(_auth_route_rate_limit_storage)
# Moving Window = 滑動視窗，比固定視窗更精確
# 例如 30/hour 不是「每整點重置」，而是「過去60分鐘內最多30次」

_send_otp_per_email_rate_limit_item = parse("30/hour")
_verify_otp_per_email_rate_limit_item = parse("60/minute")
_google_oauth_exchange_per_ip_rate_limit_item = parse("30/minute")


# ---------------------------------------------------------------------------
# 公開：slowapi（JWT / Bearer 路由）
# ---------------------------------------------------------------------------
# 從 JWT 取出 normalized email 作為 slowapi 限流 key；SKIP_AUTH 時用合成 email。
def fish_sniper_jwt_email_slowapi_key_func(request: Request) -> str:
    #Skip Auth when testing
    settings = get_fish_sniper_backend_settings()
    if settings.skip_auth:
        return normalize_email_address_for_otp_login(settings.skip_auth_rate_limit_email)

    # 從 request header 取得 Authorization 欄位
    # 格式應為 "Bearer <JWT>"，若不存在或格式錯誤則回傳預設 key
    authorization_header_value = request.headers.get("Authorization")
    if authorization_header_value is None or not authorization_header_value.startswith("Bearer "):
        return "__fish_sniper_missing_bearer__"

    # "Bearer eyJhbGci..." → 去掉 "Bearer " 前綴，取出純 JWT 字串
    access_token_jwt = authorization_header_value.removeprefix("Bearer ").strip()

    # 解析 JWT，取出 email 當作限流的 key
    # 例如回傳 "user@example.com"
    rate_limit_key =    decode_fish_sniper_rate_limit_key_from_access_token_jwt(
        access_token_jwt=access_token_jwt,
        fish_sniper_backend_settings=settings,
    )
    return rate_limit_key


# Bearer 路由在 routes/*.py 直接使用 @fish_sniper_api_limiter.limit("…")；
# 勿在該檔案頂部使用 from __future__ import annotations，否則 slowapi wrapper
# 會讓 FastAPI 無法解析 Depends 型別（400/422）。
fish_sniper_api_limiter = Limiter(
    key_func=fish_sniper_jwt_email_slowapi_key_func,
    default_limits=[],
    storage_uri="memory://",
    strategy="moving-window",
    # FastAPI 回傳 Pydantic model 而非 Response；slowapi 注入 X-RateLimit-* 會報錯，故關閉。
    headers_enabled=False,
)

# slowapi Limiter 建立完畢，還原 Starlette 原始 _read_file，避免影響其他模組。
starlette_config.Config._read_file = _original_starlette_config_read_file

# ---------------------------------------------------------------------------
# [暫時棄用 — Email OTP / Resend] send-otp / verify-otp（需 email 服務，目前未開通）
# Google OAuth 兌換仍使用下方 enforce_google_oauth_exchange_*（使用中）。
# ---------------------------------------------------------------------------


# 限制同一 email 發送 OTP 的頻率（30/小時），與 DB 60 秒冷卻互補。
def enforce_send_otp_email_rate_limit_or_raise_429(
    *,
    fish_sniper_backend_settings: FishSniperBackendSettings,
    normalized_email_address: str,
) -> None:
    if not fish_sniper_backend_settings.rate_limit_enabled:
        return
    bucket_key = f"send_otp:{normalized_email_address}"
    if not _auth_route_moving_window_rate_limiter.hit(
        _send_otp_per_email_rate_limit_item, bucket_key
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "Too many requests"},
        )


# 限制同一 email 驗證 OTP 的嘗試次數（60/分鐘），防暴力破解。
def enforce_verify_otp_email_rate_limit_or_raise_429(
    *,
    fish_sniper_backend_settings: FishSniperBackendSettings,
    normalized_email_address: str,
) -> None:
    if not fish_sniper_backend_settings.rate_limit_enabled:
        return
    bucket_key = f"verify_otp:{normalized_email_address}"
    if not _auth_route_moving_window_rate_limiter.hit(
        _verify_otp_per_email_rate_limit_item, bucket_key
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "Too many requests"},
        )


# 限制 Google OAuth code 兌換 endpoint 的 per-IP 請求（兌換前尚無 email）。
def enforce_google_oauth_exchange_ip_rate_limit_or_raise_429(
    *,
    fish_sniper_backend_settings: FishSniperBackendSettings,
    client_ip_address: str,
) -> None:
    if not fish_sniper_backend_settings.rate_limit_enabled:
        return
    bucket_key = f"google_oauth_exchange:{client_ip_address}"
    if not _auth_route_moving_window_rate_limiter.hit(
        _google_oauth_exchange_per_ip_rate_limit_item, bucket_key
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "Too many requests"},
        )


# ---------------------------------------------------------------------------
# 公開：全域例外處理
# ---------------------------------------------------------------------------


# 將 slowapi 的 RateLimitExceeded 轉成產品統一的 { "error": "Too many requests" } JSON。
def fish_sniper_handle_rate_limit_exceeded(
    _request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    _ = exc
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"error": "Too many requests"},
    )
