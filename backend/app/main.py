"""FastAPI application entrypoint (Google OAuth auth only)."""

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.auth.router import router as auth_router
from app.core.errors import invalid_payload_response
from app.core.rate_limit import (
    api_limiter,
    handle_rate_limit_exceeded,
)
from app.core.settings import get_settings


def create_app() -> FastAPI:
    """Construct the FastAPI app with auth router, CORS, and consistent error envelopes."""

    settings = get_settings()
    app = FastAPI(title="FishSniper API")

    app.state.limiter = api_limiter
    api_limiter.enabled = settings.rate_limit_enabled
    app.add_exception_handler(RateLimitExceeded, handle_rate_limit_exceeded)

    @app.exception_handler(HTTPException)
    def http_exception_handler(
        _request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    def request_validation_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return invalid_payload_response(errors=list(exc.errors()))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router, prefix="/auth", tags=["auth"])

    @app.get("/health", tags=["health"])
    def handle_health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
