from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.auth.router import router as auth_router
from app.core.config import get_settings
from app.users.router import router as users_router
from app.weather.router import router as weather_router


def create_app() -> FastAPI:
    """建立 FastAPI app，註冊 middleware 與所有 Phase 0 routers。"""

    settings = get_settings()
    app = FastAPI(title=settings.app_name)
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
    return app


app = create_app()
