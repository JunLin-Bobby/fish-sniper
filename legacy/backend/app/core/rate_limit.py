"""Per-email rate limiting (slowapi for Bearer routes; limits MovingWindow for auth body routes)."""

# ---------------------------------------------------------------------------
# ??璅∠?璁汗
#
# ?拙?璈銝血?嚗?
#   1. slowapi嚗pi_limiter嚗??? JWT ?楝?曹?嚗誑 email ??key??
#   2. limits MovingWindow ???典 Google OAuth exchange嚗ey ??IP??
#
# 撠?銝餉??亙嚗?
#   - api_limiter.limit(...)     ??頝舐 decorator嚗earer 靽風??API嚗?
#   - enforce_*_rate_limit_or_raise_429      ??頝舐 handler ?扳??炎?伐?auth 瘚?嚗?
#   - handle_rate_limit_exceeded ??main.py 閮餃????429 ??
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

from app.auth.email import normalize_email
from app.auth.jwt import decode_rate_limit_key_from_access_token

from .settings import AppSettings, get_settings

# ---------------------------------------------------------------------------
# 蝘?嚗tarlette .env 霈??patch嚗?靘?slowapi ?????蝙?剁?
# slowapi 撱箇? Limiter ??霈 .env嚗indows ?身 cp950 ?航??UTF-8 ??.env??
# ---------------------------------------------------------------------------

_original_starlette_config_read_file = starlette_config.Config._read_file


# 隞?UTF-8 閫?? .env 銵??誨 Starlette Config ??閮剛?瑼?頛胯?
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
# 璅∠?蝝蝷身?踝?蝘? storage / ?? parse ??瘚???
# Google OAuth exchange ?其蝙?刻?亙??瑁?嚗迨??瘝? JWT token??
# ---------------------------------------------------------------------------

# 蝚砌?蝯?storage ??閮?典??典鋆?
_auth_route_rate_limit_storage = limits_memory.MemoryStorage()
# 撠望銝??in-memory ???賂?閮?瘥?email/IP ??撟暹活

# 蝚砌?蝯?strategy ???其?暻潭?蝞?閮???
_auth_route_moving_window_rate_limiter = MovingWindowRateLimiter(_auth_route_rate_limit_storage)
# Moving Window = 皛?閬?嚗??箏?閬??渡移蝣?
# 靘? 30/hour 銝???湧??蔭???????0???扳?憭?0甈～?

_google_oauth_exchange_per_ip_rate_limit_item = parse("30/minute")


# ---------------------------------------------------------------------------
# ?祇?嚗lowapi嚗WT / Bearer 頝舐嚗?
# ---------------------------------------------------------------------------
# 敺?JWT ? normalized email 雿 slowapi ?? key嚗KIP_AUTH ??? email??
def jwt_email_slowapi_key_func(request: Request) -> str:
    #Skip Auth when testing
    settings = get_settings()
    if settings.skip_auth:
        return normalize_email(settings.skip_auth_rate_limit_email)

    # 敺?request header ?? Authorization 甈?
    # ?澆?? "Bearer <JWT>"嚗銝??冽??澆??航炊???喲?閮?key
    authorization_header_value = request.headers.get("Authorization")
    if authorization_header_value is None or not authorization_header_value.startswith("Bearer "):
        return "__missing_bearer__"

    # "Bearer eyJhbGci..." ???餅? "Bearer " ?韌嚗??箇? JWT 摮葡
    access_token_jwt = authorization_header_value.removeprefix("Bearer ").strip()

    # 閫?? JWT嚗???email ?嗡?????key
    # 靘?? "user@example.com"
    rate_limit_key =    decode_rate_limit_key_from_access_token(
        access_token_jwt=access_token_jwt,
        settings=settings,
    )
    return rate_limit_key


# Bearer 頝舐??routes/*.py ?湔雿輻 @api_limiter.limit("??)嚗?
# ?踹閰脫?獢??其蝙??from __future__ import annotations嚗??slowapi wrapper
# ?? FastAPI ?⊥?閫?? Depends ?嚗?00/422嚗?
api_limiter = Limiter(
    key_func=jwt_email_slowapi_key_func,
    default_limits=[],
    storage_uri="memory://",
    strategy="moving-window",
    # FastAPI ? Pydantic model ?? Response嚗lowapi 瘜典 X-RateLimit-* ??荔?????
    headers_enabled=False,
)

# slowapi Limiter 撱箇?摰嚗???Starlette ?? _read_file嚗?蔣?踹隞芋蝯?
starlette_config.Config._read_file = _original_starlette_config_read_file

# ---------------------------------------------------------------------------
# Google OAuth ?? per-IP ??
# ---------------------------------------------------------------------------


# ? Google OAuth code ?? endpoint ??per-IP 隢?嚗???撠 email嚗?
def enforce_google_oauth_exchange_ip_rate_limit_or_raise_429(
    *,
    settings: AppSettings,
    client_ip_address: str,
) -> None:
    if not settings.rate_limit_enabled:
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
# ?祇?嚗??憭???
# ---------------------------------------------------------------------------


# 撠?slowapi ??RateLimitExceeded 頧??Ｗ?蝯曹???{ "error": "Too many requests" } JSON??
def handle_rate_limit_exceeded(
    _request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    _ = exc
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"error": "Too many requests"},
    )
