import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.catch_logs.dependencies import get_catch_logs_repository, get_catch_photo_service
from app.catch_logs.service import CatchLogService
from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def retry_cleanup() -> None:
    """定期重讀 DB 工作狀態；計時器重啟不會遺失清理工作，0 可關閉自動恢復。"""

    settings = get_settings()
    while True:
        await asyncio.sleep(settings.catch_cleanup_interval_seconds)
        try:
            service = CatchLogService(
                get_catch_logs_repository(settings), get_catch_photo_service(settings)
            )
            results = await service.recover_pending()
            if any(results.values()):
                logger.info("Catch cleanup results: %s", results)
        except Exception as error:
            # The health endpoint must not fail just because Storage/schema is unavailable.
            logger.warning("Catch cleanup deferred: category=%s", type(error).__name__)


@asynccontextmanager
async def catch_cleanup_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """隨 app 啟停清理計時器，關閉時取消等待；真正工作狀態永遠存於 DB。"""

    settings = get_settings()
    enabled = bool(
        settings.catch_cleanup_interval_seconds
        and settings.supabase_url
        and settings.supabase_secret_key
    )
    task = asyncio.create_task(retry_cleanup()) if enabled else None
    try:
        yield
    finally:
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
