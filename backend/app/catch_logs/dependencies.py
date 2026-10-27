import logging
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.catch_logs.photo_schemas import CatchPhotoValidationError, CatchSubmissionConflict
from app.catch_logs.photo_service import CatchPhotoService
from app.catch_logs.service import CatchLogNotFoundError, CatchLogService
from app.catch_logs.supabase_photo_repository import SupabaseCatchPhotoRepository
from app.catch_logs.supabase_repository import SupabaseCatchLogsRepository
from app.core.config import Settings, get_settings
from app.db.client import create_supabase_rest_client
from app.db.errors import DatabaseConfigurationError, DatabaseUnavailableError
from app.storage.client import StorageUnavailableError, SupabaseStorageClient

logger = logging.getLogger(__name__)


def get_catch_logs_repository(
    settings: Settings = Depends(get_settings),
) -> SupabaseCatchLogsRepository:
    """直接建立 Supabase repository，缺少資料庫設定時回覆不含 secret 的錯誤。"""

    try:
        return SupabaseCatchLogsRepository(create_supabase_rest_client(settings))
    except DatabaseConfigurationError as error:
        logger.warning("Catch log database failed: category=configuration")
        raise HTTPException(
            status_code=503, detail="Catch logs are temporarily unavailable."
        ) from error


def get_catch_photo_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> CatchPhotoService:
    """組裝具體照片 repository 與 Storage client，不新增 repository 契約。"""

    try:
        return CatchPhotoService(
            SupabaseCatchPhotoRepository(create_supabase_rest_client(settings)),
            SupabaseStorageClient(settings),
            settings,
        )
    except DatabaseConfigurationError as error:
        raise HTTPException(503, detail="Photos are temporarily unavailable.") from error


def get_catch_log_service(
    repository: Annotated[SupabaseCatchLogsRepository, Depends(get_catch_logs_repository)],
    photos: Annotated[CatchPhotoService, Depends(get_catch_photo_service)],
) -> Iterator[CatchLogService]:
    """提供 service 並統一轉換端點執行期間的業務與資料庫錯誤，不洩漏私人資料。"""

    try:
        yield CatchLogService(repository, photos)
    except CatchLogNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Catch log not found."
        ) from error
    except CatchPhotoValidationError as error:
        raise HTTPException(422, detail=str(error)) from error
    except CatchSubmissionConflict as error:
        raise HTTPException(409, detail={"code": "submission_" + str(error)}) from error
    except (DatabaseUnavailableError, StorageUnavailableError) as error:
        logger.warning(
            "Catch request failed: category=%s status=%s",
            "storage" if isinstance(error, StorageUnavailableError) else "database",
            getattr(error, "http_status", None),
        )
        raise HTTPException(
            status_code=503, detail="Catch logs are temporarily unavailable."
        ) from error


CatchLogServiceDependency = Annotated[CatchLogService, Depends(get_catch_log_service)]
