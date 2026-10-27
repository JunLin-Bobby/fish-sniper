import asyncio
import hashlib
import json
import logging
from uuid import UUID, uuid4

from starlette.datastructures import UploadFile

from app.catch_logs.photo_schemas import CatchPhotoResponse, CatchSubmissionConflict
from app.catch_logs.photo_service import CatchPhotoService
from app.catch_logs.schemas import CatchLogCreate, CatchLogPage, CatchLogPatch, CatchLogRecord
from app.catch_logs.submission_schemas import SubmissionResult
from app.catch_logs.supabase_repository import SupabaseCatchLogsRepository
from app.db.errors import DatabaseUnavailableError
from app.storage.client import StorageUnavailableError

logger = logging.getLogger(__name__)


class CatchLogNotFoundError(RuntimeError):
    """不存在與不屬於目前 user 的紀錄使用同一種結果，避免洩漏紀錄存在性。"""


class CatchLogService:
    """處理一筆代表一隻魚的私人紀錄，將資料存取委派給 Supabase repository。"""

    def __init__(self, repository: SupabaseCatchLogsRepository, photos: CatchPhotoService) -> None:
        """注入具體 repository，service 不自行讀取連線設定或建立傳輸 client。"""

        self._repository = repository
        self._photos = photos

    async def create_with_photos(
        self,
        user_id: UUID,
        payload: CatchLogCreate,
        submission_id: UUID,
        files: list[UploadFile],
        attempt_id: UUID | None = None,
    ) -> CatchLogRecord:
        """先驗證全部內容，再建立隱藏草稿、上傳，最後以單筆 DB 交易一起發布。"""

        photos_service = self._photos
        prepared, hashes = await photos_service.validate_and_prepare(files)
        values = payload.model_dump(mode="json")
        fingerprint = hashlib.sha256(
            json.dumps(
                {"values": values, "photos": hashes},
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode()
        ).hexdigest()
        log_id = uuid4()
        manifest = photos_service.build_manifest(user_id, log_id, prepared)
        claim = await self._repository.begin_submission(
            user_id,
            submission_id,
            fingerprint,
            log_id,
            values,
            manifest,
            attempt_id,
        )
        if claim.get("outcome") == "ready":
            return await self.get_for_user(user_id, UUID(claim["log_id"]))
        if claim.get("outcome") != "new":
            raise CatchSubmissionConflict(str(claim.get("outcome", "pending")))
        try:
            await photos_service.upload_all(user_id, log_id, prepared, manifest)
            return await self._repository.publish_submission(user_id, log_id)
        except (DatabaseUnavailableError, StorageUnavailableError):
            # A lost publish response may mean COMMIT succeeded. Never delete files until
            # the DB atomically confirms that this catch is still an unpublished draft.
            await self._compensate_failed_submission(user_id, log_id)
            raise

    async def submission_status(self, user_id: UUID, submission_id: UUID) -> dict[str, object]:
        """讀取登入者自己的提交收據；尚未寫入不代表請求永遠不會完成。"""

        receipt = await self._repository.get_submission(user_id, submission_id)
        return receipt or {"status": "not_found", "log_id": None}

    async def register_submission(
        self, user_id: UUID, submission_id: UUID, attempt_id: UUID, seconds: int
    ) -> dict[str, object]:
        """先登記再接收照片，重複操作只允許讀回結果，不接管另一個 attempt。"""

        return await self._repository.register_submission(
            user_id, submission_id, attempt_id, seconds
        )

    async def start_processing(
        self, user_id: UUID, submission_id: UUID, attempt_id: UUID, seconds: int
    ) -> None:
        """由 DB 設定處理期限；已過期或已被恢復流程終結時禁止開始工作。"""

        if not await self._repository.start_processing(user_id, submission_id, attempt_id, seconds):
            raise CatchSubmissionConflict("pending")

    async def resolve_submission(self, user_id: UUID, submission_id: UUID) -> SubmissionResult:
        """由 App 自動恢復結果；未知 ID 的終結也必須持久化，不能只回 not_found。"""

        return SubmissionResult.model_validate(
            await self._repository.resolve_submission(user_id, submission_id)
        )

    async def fail_attempt(
        self, user_id: UUID, submission_id: UUID, attempt_id: UUID
    ) -> SubmissionResult | None:
        """先固定終局，再有界清理；無法聯絡 DB 時交給期限恢復，不假造失敗。"""

        try:
            result = SubmissionResult.model_validate(
                await self._repository.fail_submission(user_id, submission_id, attempt_id)
            )
            if result.status == "failed" and result.log_id:
                try:
                    async with asyncio.timeout(5):
                        await self._photos.cleanup_files(result.log_id)
                        await self._repository.finish_cleanup(user_id, result.log_id)
                except (DatabaseUnavailableError, StorageUnavailableError, TimeoutError):
                    logger.warning("Catch cleanup deferred: category=provider")
            return result
        except DatabaseUnavailableError:
            logger.warning("Catch terminal state deferred: category=database")
            return None

    async def _compensate_failed_submission(self, user_id: UUID, log_id: UUID) -> None:
        """持久取消待發布草稿再清理，DB 不可用時保留 manifest 給恢復指令處理。"""

        try:
            if await self._repository.claim_cleanup(user_id, log_id):
                await self._photos.cleanup_files(log_id)
                await self._repository.finish_cleanup(user_id, log_id)
        except (DatabaseUnavailableError, StorageUnavailableError):
            logger.warning("Catch compensation deferred: category=provider")

    async def list_photos(self, user_id: UUID, log_id: UUID) -> list[CatchPhotoResponse]:
        """先驗證已發布魚獲的擁有權，再交由照片 service 產生私人連結。"""

        await self.get_for_user(user_id, log_id)
        return await self._photos.list_ready(log_id)

    async def delete_photo(self, user_id: UUID, log_id: UUID, photo_id: UUID) -> None:
        """透過 owner-scoped DB 操作刪除照片，其他帳號一律得到找不到。"""

        if not await self._photos.delete_photo(user_id, log_id, photo_id):
            raise CatchLogNotFoundError()

    async def create(self, user_id: UUID, payload: CatchLogCreate) -> CatchLogRecord:
        """只接受白名單欄位，擁有者固定由已驗證的登入身分決定。"""

        return await self._repository.create(user_id, payload.model_dump(mode="json"))

    async def list_for_user(self, user_id: UUID, *, limit: int, offset: int) -> CatchLogPage:
        """多取一筆判斷下一頁，避免額外執行全表筆數查詢。"""

        rows = await self._repository.list_for_user(user_id, limit=limit + 1, offset=offset)
        return CatchLogPage(
            items=rows[:limit], limit=limit, offset=offset, has_more=len(rows) > limit
        )

    async def get_for_user(self, user_id: UUID, log_id: UUID) -> CatchLogRecord:
        """讀取自己的紀錄，沒有符合 owner 的資料時回報找不到。"""

        record = await self._repository.get_for_user(user_id, log_id)
        if record is None:
            raise CatchLogNotFoundError()
        return record

    async def update_for_user(
        self, user_id: UUID, log_id: UUID, payload: CatchLogPatch
    ) -> CatchLogRecord:
        """保留未傳入欄位，僅將明確提交的選填 null 寫入以清空資料。"""

        record = await self._repository.update_for_user(
            user_id,
            log_id,
            payload.model_dump(mode="json", exclude_unset=True),
        )
        if record is None:
            raise CatchLogNotFoundError()
        return record

    async def delete_for_user(self, user_id: UUID, log_id: UUID) -> None:
        """先持久標記刪除並隱藏魚獲，清理檔案後才刪資料，失敗可以重試。"""

        if not await self._repository.claim_cleanup(user_id, log_id, delete=True):
            raise CatchLogNotFoundError()
        await self._photos.cleanup_files(log_id)
        await self._repository.finish_cleanup(user_id, log_id)

    async def recover_pending(self) -> dict[str, int]:
        """重跑未完成的補償與刪除；DB 鎖及期限防止清理正在正常執行的提交。"""

        await self._repository.expire_submissions()
        counts = {"cleaned": 0, "retained": 0, "errors": 0}
        for row in await self._repository.cleanup_candidates():
            user_id, log_id = UUID(row["user_id"]), UUID(row["id"])
            try:
                if await self._repository.claim_cleanup(user_id, log_id, stale=True):
                    await self._photos.cleanup_files(log_id)
                    done = await self._repository.finish_cleanup(user_id, log_id)
                    counts["cleaned" if done else "retained"] += 1
            except (DatabaseUnavailableError, StorageUnavailableError):
                logger.warning("Catch cleanup failed: category=provider")
                counts["errors"] += 1
        photo_counts = await self._photos.recover_deleting_photos()
        return {key: value + photo_counts[key] for key, value in counts.items()}
