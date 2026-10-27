from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.auth.router import router as auth_router
from app.catch_logs.recovery import catch_cleanup_lifespan
from app.catch_logs.router import router as catch_logs_router
from app.catch_logs.upload_limits import CatchUploadLimitMiddleware
from app.core.config import get_settings
from app.users.router import router as users_router
from app.weather.router import router as weather_router


def create_app() -> FastAPI:
    """建立 FastAPI app，註冊共用 middleware、登入、天氣與私人漁獲 routers。"""

    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=catch_cleanup_lifespan)
    app.add_middleware(
        CatchUploadLimitMiddleware, max_bytes=2 * settings.catch_photo_max_bytes + 65_536
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(weather_router)
    app.include_router(catch_logs_router)
    return app


app = create_app()
