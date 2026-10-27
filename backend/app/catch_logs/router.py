import asyncio
import math
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from app.auth.dependencies import CurrentUserDependency
from app.catch_logs.dependencies import CatchLogServiceDependency
from app.catch_logs.photo_schemas import CatchPhotoResponse, CatchSubmissionConflict
from app.catch_logs.schemas import CatchLogCreate, CatchLogPage, CatchLogPatch, CatchLogRecord
from app.catch_logs.submission_schemas import SubmissionResult
from app.core.config import Settings, get_settings
from app.db.errors import DatabaseUnavailableError

router = APIRouter(prefix="/api/v1/catch-logs", tags=["catch-logs"])


@router.post("/submissions/{submission_id}/resolve", response_model=SubmissionResult)
async def resolve_submission(
    submission_id: UUID,
    current_user: CurrentUserDependency,
    service: CatchLogServiceDependency,
) -> SubmissionResult:
    """只在原 POST 失聯後由 App 呼叫；可寫入終結收據，所以不是 GET。"""

    return await service.resolve_submission(current_user.id, submission_id)


@router.get("/submissions/{submission_id}")
async def get_submission_status(
    submission_id: UUID,
    current_user: CurrentUserDependency,
    service: CatchLogServiceDependency,
) -> dict[str, object]:
    """重新整理後確認自己的提交結果，避免回應遺失後直接重建魚獲。"""

    return await service.submission_status(current_user.id, submission_id)


@router.post("/with-photos", response_model=CatchLogRecord, status_code=201)
async def create_catch_log_with_photos(
    request: Request,
    current_user: CurrentUserDependency,
    service: CatchLogServiceDependency,
    submission_key: Annotated[UUID, Header(alias="Idempotency-Key")],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CatchLogRecord:
    """同一表單接受 JSON 欄位與最多兩張檔案，先解析驗證再進入協調 service。"""

    attempt_id = uuid4()
    registration = await service.register_submission(
        current_user.id,
        submission_key,
        attempt_id,
        math.ceil(settings.catch_upload_receive_seconds),
    )
    outcome = registration.get("outcome")
    if outcome not in ("new", "ready"):
        raise CatchSubmissionConflict(str(outcome))
    try:
        async with asyncio.timeout(settings.catch_upload_receive_seconds):
            form = await request.form(max_files=2, max_fields=2, max_part_size=16_384)
        try:
            if set(form) - {"payload", "submission_id", "photos"}:
                raise ValueError()
            if len(form.getlist("payload")) != 1 or len(form.getlist("submission_id")) != 1:
                raise ValueError()
            payload = CatchLogCreate.model_validate_json(str(form["payload"]))
            submission_id = UUID(str(form["submission_id"]))
            if submission_id != submission_key:
                raise ValueError()
            files = form.getlist("photos")
            if any(not isinstance(file, UploadFile) for file in files):
                raise ValueError()
            async with asyncio.timeout(settings.catch_upload_processing_seconds):
                if outcome == "new":
                    await service.start_processing(
                        current_user.id,
                        submission_key,
                        attempt_id,
                        math.ceil(settings.catch_upload_processing_seconds),
                    )
                return await service.create_with_photos(
                    current_user.id,
                    payload,
                    submission_id,
                    files,
                    attempt_id if outcome == "new" else None,
                )
        finally:
            await form.close()
    except Exception as error:
        # Only our new attempt can fail; replay validation must never change committed success.
        result = await service.fail_attempt(current_user.id, submission_key, attempt_id)
        if isinstance(error, (ValidationError, ValueError)):
            raise HTTPException(422, detail="Invalid catch form or photos.") from error
        if isinstance(error, TimeoutError):
            raise HTTPException(503, detail="Catch upload could not be completed.") from error
        if result and result.status == "ready" and not isinstance(error, CatchSubmissionConflict):
            return await service.get_for_user(current_user.id, result.log_id)
        if result is None:
            raise DatabaseUnavailableError("Submission result is unavailable.") from error
        raise


@router.get("/{log_id}/photos", response_model=list[CatchPhotoResponse])
async def list_catch_photos(
    log_id: UUID,
    current_user: CurrentUserDependency,
    service: CatchLogServiceDependency,
) -> list[CatchPhotoResponse]:
    """檢查魚獲擁有權後載入照片與新連結，不從前端接受 Storage 路徑。"""

    return await service.list_photos(current_user.id, log_id)


@router.delete("/{log_id}/photos/{photo_id}", status_code=204)
async def delete_catch_photo(
    log_id: UUID,
    photo_id: UUID,
    current_user: CurrentUserDependency,
    service: CatchLogServiceDependency,
) -> Response:
    """單獨刪除自己的照片，清理失敗時保留刪除意圖。"""

    await service.delete_photo(current_user.id, log_id, photo_id)
    return Response(status_code=204)


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
