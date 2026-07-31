"""Shared HTTP error envelopes.

Two response shapes are produced here:

* ``invalid_payload_response``: 400 ``INVALID_PAYLOAD`` for client-side
  validation failures, replacing FastAPI's default 422 response.
* ``service_temporarily_unavailable_response``: 503
  ``SERVICE_TEMPORARILY_UNAVAILABLE`` for transient persistence failures.
"""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse

_INVALID_PAYLOAD_MESSAGE = "Invalid request payload."
_SERVICE_TEMPORARILY_UNAVAILABLE_MESSAGE = "Service is temporarily unavailable."


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
    """Build a 503 envelope for transient persistence failures."""

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