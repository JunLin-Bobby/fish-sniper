"""Per-email rate limiting (slowapi for Bearer routes; limits MovingWindow for auth body routes)."""

from __future__ import annotations

import functools
import types
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

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

_original_starlette_config_read_file = starlette_config.Config._read_file


def _read_env_file_with_utf8_encoding(
    self: starlette_config.Config,
    file_name: str | Path,
) -> dict[str, str]:
    """Match Starlette's parser but force UTF-8 so Windows cp950 default cannot break `.env`."""

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

_auth_route_rate_limit_storage = limits_memory.MemoryStorage()
_auth_route_moving_window_rate_limiter = MovingWindowRateLimiter(_auth_route_rate_limit_storage)

_send_otp_per_email_rate_limit_item = parse("30/hour")
_verify_otp_per_email_rate_limit_item = parse("60/minute")
_google_oauth_exchange_per_ip_rate_limit_item = parse("30/minute")


def fish_sniper_jwt_email_slowapi_key_func(request: Request) -> str:
    """slowapi key: normalized email from JWT, or synthetic key when SKIP_AUTH."""

    settings = get_fish_sniper_backend_settings()
    if settings.skip_auth:
        return normalize_email_address_for_otp_login(settings.skip_auth_rate_limit_email)

    authorization_header_value = request.headers.get("Authorization")
    if authorization_header_value is None or not authorization_header_value.startswith("Bearer "):
        return "__fish_sniper_missing_bearer__"

    access_token_jwt = authorization_header_value.removeprefix("Bearer ").strip()
    rate_limit_key = decode_fish_sniper_rate_limit_key_from_access_token_jwt(
        access_token_jwt=access_token_jwt,
        fish_sniper_backend_settings=settings,
    )
    return rate_limit_key


fish_sniper_api_limiter = Limiter(
    key_func=fish_sniper_jwt_email_slowapi_key_func,
    default_limits=[],
    storage_uri="memory://",
    strategy="moving-window",
    # FastAPI returns Pydantic models, not ``Response``. slowapi then tries
    # ``kwargs["response"]`` for header injection, which FastAPI does not set →
    # "parameter `response` must be an instance of ... Response". Disable
    # X-RateLimit-* on success responses; 429 handler still builds a JSONResponse.
    headers_enabled=False,
)

FishSniperSlowapiLimitedRoute = TypeVar(
    "FishSniperSlowapiLimitedRoute", bound=Callable[..., object]
)


def fish_sniper_apply_api_rate_limit(
    limit_value: str,
) -> Callable[[FishSniperSlowapiLimitedRoute], FishSniperSlowapiLimitedRoute]:
    """Apply slowapi limits without breaking FastAPI dependency injection.

    slowapi's ``@limit`` defines its wrapper in ``slowapi.extension``, so the wrapped
    endpoint's ``__globals__`` point at that module. ``from __future__ import annotations``
    leaves hints as strings; FastAPI then fails to resolve ``FishSniperUserIdDep`` etc.
    and treats them as query parameters (422). Re-bind the wrapper's code object so
    **type hints** resolve in the route module.

    The wrapper bytecode still does ``isinstance(..., Response)`` etc.; those names live
    in ``slowapi.extension``. Using **only** the route module as ``__globals__`` causes
    ``NameError: Response is not defined``. Merge slowapi's globals with the route module,
    with the route module winning on duplicate keys so FastAPI dependencies keep working.
    """

    slowapi_route_decorator = fish_sniper_api_limiter.limit(limit_value)

    def decorator(route_handler: FishSniperSlowapiLimitedRoute) -> FishSniperSlowapiLimitedRoute:
        wrapped_by_slowapi = slowapi_route_decorator(route_handler)
        if wrapped_by_slowapi.__globals__ is route_handler.__globals__:
            return wrapped_by_slowapi
        merged_route_endpoint_globals = dict(wrapped_by_slowapi.__globals__)
        merged_route_endpoint_globals.update(route_handler.__globals__)
        repaired = types.FunctionType(
            wrapped_by_slowapi.__code__,
            merged_route_endpoint_globals,
            wrapped_by_slowapi.__name__,
            wrapped_by_slowapi.__defaults__,
            wrapped_by_slowapi.__closure__,
        )
        repaired.__kwdefaults__ = wrapped_by_slowapi.__kwdefaults__
        repaired.__annotations__ = route_handler.__annotations__
        repaired.__module__ = route_handler.__module__
        repaired.__qualname__ = route_handler.__qualname__
        repaired.__doc__ = route_handler.__doc__
        functools.update_wrapper(repaired, route_handler)
        return repaired  # type: ignore[return-value]

    return decorator


starlette_config.Config._read_file = _original_starlette_config_read_file


def enforce_send_otp_email_rate_limit_or_raise_429(
    *,
    fish_sniper_backend_settings: FishSniperBackendSettings,
    normalized_email_address: str,
) -> None:
    """Extra per-email cap for send-otp (in addition to the 60s DB cooldown)."""

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


def enforce_verify_otp_email_rate_limit_or_raise_429(
    *,
    fish_sniper_backend_settings: FishSniperBackendSettings,
    normalized_email_address: str,
) -> None:
    """Brute-force protection per email on verify-otp."""

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


def enforce_google_oauth_exchange_ip_rate_limit_or_raise_429(
    *,
    fish_sniper_backend_settings: FishSniperBackendSettings,
    client_ip_address: str,
) -> None:
    """Per-IP cap for the Google OAuth exchange endpoint (we have no email pre-token)."""

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


def fish_sniper_handle_rate_limit_exceeded(
    _request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Map slowapi RateLimitExceeded to FishSniper `{ \"error\": ... }` envelope."""

    _ = exc
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"error": "Too many requests"},
    )
