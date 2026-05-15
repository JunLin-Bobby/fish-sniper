"""FishSniper FastAPI application entrypoint."""

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from deps import get_fish_sniper_backend_settings
from error_envelopes import invalid_payload_response
from rate_limiting import fish_sniper_api_limiter, fish_sniper_handle_rate_limit_exceeded
from routes.agent_routes import router as agent_router
from routes.auth_routes import router as auth_router
from routes.log_routes import router as log_router
from routes.user_preferences_routes import router as user_preferences_router
from routes.users_account_routes import router as users_account_router
from routes.weather_routes import router as weather_router


def create_fish_sniper_app() -> FastAPI:
    """Construct the FastAPI app with routers, CORS, and consistent error envelopes."""

    fish_sniper_backend_settings = get_fish_sniper_backend_settings()
    app = FastAPI(title="FishSniper API")
    app.state.limiter = fish_sniper_api_limiter
    fish_sniper_api_limiter.enabled = fish_sniper_backend_settings.rate_limit_enabled
    app.add_exception_handler(RateLimitExceeded, fish_sniper_handle_rate_limit_exceeded)

    @app.exception_handler(HTTPException)
    def fish_sniper_http_exception_handler(
        _request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        """Match product API errors as top-level `{ \"error\": ... }` when applicable."""

        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    def fish_sniper_request_validation_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Translate FastAPI's default 422 into our product 400 INVALID_PAYLOAD envelope."""

        # `exc.errors()` returns Pydantic-style dicts (loc, msg, type, …) which are
        # serializable as-is; we forward them under `errors` so clients can show
        # field-level messages without exposing internal Python paths.
        return invalid_payload_response(errors=list(exc.errors()))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[fish_sniper_backend_settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(user_preferences_router, prefix="/users", tags=["users"])
    app.include_router(users_account_router, prefix="/users", tags=["users"])
    app.include_router(log_router, prefix="/logs", tags=["logs"])
    app.include_router(weather_router, prefix="/weather", tags=["weather"])
    app.include_router(agent_router, prefix="/agent", tags=["agent"])

    @app.get("/health", tags=["health"])
    def handle_health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_fish_sniper_app()
