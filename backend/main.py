"""FishSniper FastAPI application entrypoint."""

# ---------------------------------------------------------------------------
# 1. 環境變數載入
#    在 import 其他模組前先讀取 .env，讓 deps / settings 能拿到 API keys 等設定。
# ---------------------------------------------------------------------------
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# 2. 依賴匯入
#    - FastAPI 核心與中介層
#    - 專案設定、錯誤格式、限流
#    - 各功能路由（auth / users / logs / weather / agent）
# ---------------------------------------------------------------------------
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

    # -----------------------------------------------------------------------
    # 3. 讀取後端設定 & 建立 App 實例
    #    settings 來自 deps（底層是 settings.py + 環境變數）。
    # -----------------------------------------------------------------------
    fish_sniper_backend_settings = get_fish_sniper_backend_settings()
    app = FastAPI(title="FishSniper API")

    # -----------------------------------------------------------------------
    # 4. 全局限流（Rate Limiting）
    #    將 slowapi limiter 掛到 app.state，並依設定開關是否啟用。
    #    超過限制時由 fish_sniper_handle_rate_limit_exceeded 回傳統一錯誤格式。
    # -----------------------------------------------------------------------
    app.state.limiter = fish_sniper_api_limiter
    fish_sniper_api_limiter.enabled = fish_sniper_backend_settings.rate_limit_enabled
    app.add_exception_handler(RateLimitExceeded, fish_sniper_handle_rate_limit_exceeded)

    # -----------------------------------------------------------------------
    # 5. 全域例外處理（Error Envelopes）
    #    把 FastAPI / HTTP 錯誤轉成前端預期的 JSON 結構，避免各路由各自定義格式。
    # -----------------------------------------------------------------------

    @app.exception_handler(HTTPException)
    def fish_sniper_http_exception_handler(
        _request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        """Match product API errors as top-level `{ \"error\": ... }` when applicable."""

        # 若 detail 已是產品格式 { "error": ... }，原樣回傳；否則包成 FastAPI 預設 { "detail": ... }。
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    def fish_sniper_request_validation_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Translate FastAPI's default 422 into our product 400 INVALID_PAYLOAD envelope."""

        # Pydantic 驗證失敗（422）→ 產品定義的 400 INVALID_PAYLOAD，並附上欄位級 errors。
        return invalid_payload_response(errors=list(exc.errors()))

    # -----------------------------------------------------------------------
    # 6. CORS 中介層
    #    只允許設定中的 frontend_origin 跨域存取，並支援 credentials（cookie / auth header）。
    # -----------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[fish_sniper_backend_settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------------
    # 7. 路由註冊（Routers）
    #    各 router 定義在 routes/ 下，main.py 只負責掛載前綴與 OpenAPI tag。
    #
    #    /auth   → 登入、OAuth、OTP 等認證流程
    #    /users  → 使用者偏好設定、帳號管理（刪除等）
    #    /logs   → 釣魚紀錄 CRUD 與向量搜尋
    #    /weather→ 天氣查詢（供策略建議使用）
    #    /agent  → LLM 策略生成（LangGraph pipeline）
    # -----------------------------------------------------------------------
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(user_preferences_router, prefix="/users", tags=["users"])
    app.include_router(users_account_router, prefix="/users", tags=["users"])
    app.include_router(log_router, prefix="/logs", tags=["logs"])
    app.include_router(weather_router, prefix="/weather", tags=["weather"])
    app.include_router(agent_router, prefix="/agent", tags=["agent"])

    # -----------------------------------------------------------------------
    # 8. 健康檢查
    #    供部署平台 / 監控探針確認服務是否存活，不依賴資料庫或外部 API。
    # -----------------------------------------------------------------------
    @app.get("/health", tags=["health"])
    def handle_health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


# ---------------------------------------------------------------------------
# 9. 模組級 App 實例
#    uvicorn 啟動時使用：uvicorn main:app --reload
#    測試也可 import 此 app 或呼叫 create_fish_sniper_app() 建立獨立實例。
# ---------------------------------------------------------------------------
app = create_fish_sniper_app()
