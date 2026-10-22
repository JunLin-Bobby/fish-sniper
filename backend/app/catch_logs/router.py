from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.auth.dependencies import CurrentUserDependency
from app.catch_logs.dependencies import CatchLogServiceDependency
from app.catch_logs.schemas import CatchLogCreate, CatchLogPage, CatchLogPatch, CatchLogRecord

router = APIRouter(prefix="/api/v1/catch-logs", tags=["catch-logs"])


@router.post("", response_model=CatchLogRecord, status_code=status.HTTP_201_CREATED)
async def create_catch_log(
    current_user: CurrentUserDependency,
    service: CatchLogServiceDependency,
    payload: CatchLogCreate,
) -> CatchLogRecord:
    """為目前登入使用者建立一隻魚的紀錄，不接受外部 user_id。"""

    return await service.create(current_user.id, payload)


@router.get("", response_model=CatchLogPage)
async def list_catch_logs(
    current_user: CurrentUserDependency,
    service: CatchLogServiceDependency,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> CatchLogPage:
    """只列出目前使用者的紀錄，限制單頁大小並支援下一頁。"""

    return await service.list_for_user(current_user.id, limit=limit, offset=offset)


@router.get("/{log_id}", response_model=CatchLogRecord)
async def get_catch_log(
    log_id: UUID,
    current_user: CurrentUserDependency,
    service: CatchLogServiceDependency,
) -> CatchLogRecord:
    """取得自己的單筆紀錄，不揭露其他使用者是否擁有此 UUID。"""

    return await service.get_for_user(current_user.id, log_id)


@router.patch("/{log_id}", response_model=CatchLogRecord)
async def update_catch_log(
    log_id: UUID,
    current_user: CurrentUserDependency,
    service: CatchLogServiceDependency,
    payload: CatchLogPatch,
) -> CatchLogRecord:
    """修改自己的紀錄，保留未傳入的欄位並允許清空選填資料。"""

    return await service.update_for_user(current_user.id, log_id, payload)


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_catch_log(
    log_id: UUID,
    current_user: CurrentUserDependency,
    service: CatchLogServiceDependency,
) -> Response:
    """刪除自己的紀錄，成功時不回傳 JSON body。"""

    await service.delete_for_user(current_user.id, log_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
