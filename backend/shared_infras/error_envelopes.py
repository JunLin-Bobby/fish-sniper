"""Shared HTTP error envelopes used across all FishSniper routes (P4 Part 1).

Two response shapes are produced here:

* ``invalid_payload_response`` → 400 ``INVALID_PAYLOAD`` for any client-side
  validation failure (replaces FastAPI's default 422). Wired up via the
  global ``RequestValidationError`` handler in ``main.py``.

* ``service_temporarily_unavailable_response`` → 503
  ``SERVICE_TEMPORARILY_UNAVAILABLE`` for transient persistence failures that
  survive a single retry. The envelope intentionally hides backend details
  (stack traces, DB error codes) — those are emitted to logs only.
"""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse

_INVALID_PAYLOAD_MESSAGE = "欄位錯誤"
_SERVICE_TEMPORARILY_UNAVAILABLE_MESSAGE = "紀錄儲存失敗，請稍後再試"


def invalid_payload_response(
    *,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    """Build a 400 envelope for failed request-body validation."""

    payload: dict[str, Any] = {
        "code": "INVALID_PAYLOAD",
        "message": _INVALID_PAYLOAD_MESSAGE,
    }
    if errors is not None:
        payload["errors"] = errors
    return JSONResponse(status_code=400, content=payload)


def service_temporarily_unavailable_response(
    *,
    retry_after_seconds: int = 30,
) -> JSONResponse:
    """Build a 503 envelope for transient persistence failures (post-retry)."""

    payload: dict[str, Any] = {
        "code": "SERVICE_TEMPORARILY_UNAVAILABLE",
        "message": _SERVICE_TEMPORARILY_UNAVAILABLE_MESSAGE,
        "retryAfter": retry_after_seconds,
    }
    return JSONResponse(
        status_code=503,
        content=payload,
        headers={"Retry-After": str(retry_after_seconds)},
    )
