import asyncio
import json

from app.catch_logs.dependencies import get_catch_logs_repository, get_catch_photo_service
from app.catch_logs.service import CatchLogService
from app.core.config import get_settings


async def run_cleanup() -> None:
    """重跑可恢復的草稿、整筆魚獲與單張照片清理；不輸出個資與憑證。"""

    settings = get_settings()
    service = CatchLogService(
        get_catch_logs_repository(settings), get_catch_photo_service(settings)
    )
    results = await service.recover_pending()
    print(json.dumps(results))
    if results["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(run_cleanup())
