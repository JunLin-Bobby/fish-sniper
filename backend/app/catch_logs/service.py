from uuid import UUID

from app.catch_logs.schemas import CatchLogCreate, CatchLogPage, CatchLogPatch, CatchLogRecord
from app.catch_logs.supabase_repository import SupabaseCatchLogsRepository


class CatchLogNotFoundError(RuntimeError):
    """不存在與不屬於目前 user 的紀錄使用同一種結果，避免洩漏紀錄存在性。"""


class CatchLogService:
    """處理一筆代表一隻魚的私人紀錄，將資料存取委派給 Supabase repository。"""

    def __init__(self, repository: SupabaseCatchLogsRepository) -> None:
        """注入具體 repository，service 不自行讀取連線設定或建立傳輸 client。"""

        self._repository = repository

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
        """刪除自己的純文字紀錄；照片清理流程保留給後續 2C 階段。"""

        if not await self._repository.delete_for_user(user_id, log_id):
            raise CatchLogNotFoundError()
