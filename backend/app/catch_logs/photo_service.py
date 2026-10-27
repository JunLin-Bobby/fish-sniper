import hashlib
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from app.catch_logs.photo_processing import prepare_photo
from app.catch_logs.photo_schemas import (
    CatchPhotoResponse,
    CatchPhotoValidationError,
    PreparedPhoto,
)
from app.catch_logs.supabase_photo_repository import SupabaseCatchPhotoRepository
from app.core.config import Settings
from app.db.errors import DatabaseUnavailableError
from app.storage.client import StorageUnavailableError, SupabaseStorageClient

logger = logging.getLogger(__name__)


class CatchPhotoService:
    """只管理照片工作，不反向呼叫 CatchLogService 或修改魚獲業務欄位。"""

    def __init__(
        self,
        repository: SupabaseCatchPhotoRepository,
        storage: SupabaseStorageClient,
        settings: Settings,
    ) -> None:
        """注入照片資料存取與 Storage，讓圖片處理不依賴資料庫連線。"""

        self._repository = repository
        self._storage = storage
        self._settings = settings

    async def validate_and_prepare(
        self, files: list[UploadFile]
    ) -> tuple[list[PreparedPhoto], list[str]]:
        """有界讀取每張原檔並在 worker thread 轉檔；全部驗證完成才建立草稿。"""

        if len(files) > 2:
            raise CatchPhotoValidationError("At most two photos are allowed.")
        photos, hashes = [], []
        for file in files:
            content = await file.read(self._settings.catch_photo_max_bytes + 1)
            photos.append(await run_in_threadpool(prepare_photo, content, self._settings))
            hashes.append(hashlib.sha256(content).hexdigest())
        return photos, hashes

    def build_manifest(
        self, user_id: UUID, log_id: UUID, photos: list[PreparedPhoto]
    ) -> list[dict[str, Any]]:
        """事先安排所有唯一檔案路徑，讓程序中斷後仍有可清理的完整 manifest。"""

        manifest = []
        for index, photo in enumerate(photos, start=1):
            photo_id = uuid4()
            manifest.append(
                {
                    "id": str(photo_id),
                    "photo_order": index,
                    "bucket": self._settings.catch_photo_bucket,
                    "object_path": f"{user_id}/{log_id}/{photo_id}.jpg",
                    "size_bytes": len(photo.content),
                    "width": photo.width,
                    "height": photo.height,
                    "metadata": photo.metadata.model_dump(mode="json"),
                }
            )
        return manifest

    async def upload_all(
        self,
        user_id: UUID,
        log_id: UUID,
        photos: list[PreparedPhoto],
        manifest: list[dict[str, Any]],
    ) -> None:
        """逐張上傳並記錄 uploaded；uploaded 不是可見狀態，必須等待整筆發布。"""

        for photo, entry in zip(photos, manifest, strict=True):
            await self._storage.upload(entry["bucket"], entry["object_path"], photo.content)
            marked = await self._repository.mark_uploaded(user_id, log_id, UUID(entry["id"]))
            if marked is not True:
                raise DatabaseUnavailableError("Draft no longer accepts uploads.")

    async def cleanup_files(self, log_id: UUID) -> None:
        """清理所有已安排路徑（包含未收到成功回應的上傳），失敗時不刪除 manifest。"""

        photos = await self._repository.list_for_log(log_id)
        buckets: dict[str, list[str]] = {}
        for photo in photos:
            buckets.setdefault(photo.bucket, []).append(photo.object_path)
        for bucket, paths in buckets.items():
            await self._storage.delete(bucket, paths)

    async def list_ready(self, log_id: UUID) -> list[CatchPhotoResponse]:
        """僅為已發布照片建立短效連結，網址不寫入資料庫。"""

        seconds = self._settings.catch_photo_signed_url_seconds
        results = []
        for photo in await self._repository.list_for_log(log_id):
            if photo.status == "ready":
                url = await self._storage.signed_url(photo.bucket, photo.object_path, seconds)
                results.append(
                    CatchPhotoResponse(
                        id=photo.id,
                        photo_order=photo.photo_order,
                        width=photo.width,
                        height=photo.height,
                        url=url,
                        expires_at=datetime.now(UTC) + timedelta(seconds=seconds),
                        metadata=photo.metadata,
                    )
                )
        return results

    async def delete_photo(self, user_id: UUID, log_id: UUID, photo_id: UUID) -> bool:
        """先持久標記刪除意圖，再刪檔與資料列；失敗保留 deleting 以供重試。"""

        photo = await self._repository.begin_delete(user_id, log_id, photo_id)
        if photo is None:
            return False
        await self._storage.delete(photo.bucket, [photo.object_path])
        await self._repository.remove_deleted_photo(log_id, photo_id)
        return True

    async def recover_deleting_photos(self) -> dict[str, int]:
        """重跑單張照片清理；整筆魚獲的恢復流程交給 CatchLogService 協調。"""

        counts = {"cleaned": 0, "retained": 0, "errors": 0}
        for row in await self._repository.deleting_photos():
            try:
                await self.delete_photo(
                    UUID(row["catch_logs"]["user_id"]), UUID(row["catch_log_id"]), UUID(row["id"])
                )
                counts["cleaned"] += 1
            except (DatabaseUnavailableError, StorageUnavailableError):
                logger.warning("Photo cleanup failed: category=provider")
                counts["errors"] += 1
        return counts
