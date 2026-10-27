from typing import Any
from uuid import UUID

from pydantic import ValidationError

from app.catch_logs.photo_schemas import CatchPhotoRecord
from app.db.client import SupabaseRestClient
from app.db.errors import DatabaseUnavailableError


class SupabaseCatchPhotoRepository:
    """管理照片紀錄與生命週期 RPC，不讀取或上傳圖片內容。"""

    def __init__(self, client: SupabaseRestClient) -> None:
        """注入與其他 repository 共用的 Data API 傳輸。"""

        self._client = client

    async def mark_uploaded(self, user_id: UUID, log_id: UUID, photo_id: UUID) -> bool:
        """只在父紀錄仍待發布時標記上傳完成，不允許清理中的魚獲繼續寫入。"""

        return (
            await self._client.request(
                "POST",
                "rpc/mark_catch_photo_uploaded",
                json={
                    "p_user_id": str(user_id),
                    "p_log_id": str(log_id),
                    "p_photo_id": str(photo_id),
                },
            )
            is True
        )

    async def begin_delete(
        self,
        user_id: UUID,
        log_id: UUID,
        photo_id: UUID,
    ) -> CatchPhotoRecord | None:
        """由資料庫原子檢查 owner 與狀態，持久記錄單張照片的刪除意圖。"""

        row = await self._client.request(
            "POST",
            "rpc/begin_catch_photo_delete",
            json={
                "p_user_id": str(user_id),
                "p_log_id": str(log_id),
                "p_photo_id": str(photo_id),
            },
        )
        if row is None:
            return None
        try:
            return CatchPhotoRecord.model_validate(row)
        except ValidationError as error:
            raise DatabaseUnavailableError("Invalid photo deletion record.") from error

    async def list_for_log(self, log_id: UUID) -> list[CatchPhotoRecord]:
        """取得已由 service 驗證擁有權或清理權的魚獲照片，包含尚未完成的路徑。"""

        rows = await self._client.request(
            "GET",
            "catch_log_photos",
            params={"catch_log_id": f"eq.{log_id}", "order": "photo_order.asc"},
        )
        try:
            if not isinstance(rows, list):
                raise ValueError()
            return [CatchPhotoRecord.model_validate(row) for row in rows]
        except (ValueError, ValidationError) as error:
            raise DatabaseUnavailableError("Invalid photo records.") from error

    async def remove_deleted_photo(self, log_id: UUID, photo_id: UUID) -> None:
        """只移除已標成 deleting 的照片列，不能把尚未清理的檔案路徑弄丟。"""

        await self._client.request(
            "DELETE",
            "catch_log_photos",
            params={
                "catch_log_id": f"eq.{log_id}",
                "id": f"eq.{photo_id}",
                "status": "eq.deleting",
            },
        )

    async def deleting_photos(self) -> list[dict[str, Any]]:
        """取得獨立照片刪除失敗的工作及其擁有者，不使用前端提供的 owner。"""

        rows = await self._client.request(
            "GET",
            "catch_log_photos",
            params={
                "select": "id,catch_log_id,catch_logs!inner(user_id,status)",
                "status": "eq.deleting",
                "catch_logs.status": "eq.ready",
                "limit": "100",
            },
        )
        if not isinstance(rows, list):
            raise DatabaseUnavailableError("Invalid photo cleanup response.")
        return rows
