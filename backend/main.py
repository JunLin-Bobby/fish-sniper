"""FishSniper FastAPI application entrypoint."""

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from deps import get_fish_sniper_backend_settings
from routes.auth_routes import router as auth_router
from routes.user_preferences_routes import router as user_preferences_router


def create_fish_sniper_app() -> FastAPI:
    """Construct the FastAPI app with routers, CORS, and consistent error envelopes."""

    fish_sniper_backend_settings = get_fish_sniper_backend_settings()
    app = FastAPI(title="FishSniper API")

    @app.exception_handler(HTTPException)
    def fish_sniper_http_exception_handler(
        _request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        """Match product API errors as top-level `{ \"error\": ... }` when applicable."""

        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[fish_sniper_backend_settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(user_preferences_router, prefix="/users", tags=["users"])

    @app.get("/health", tags=["health"])
    def handle_health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_fish_sniper_app()
