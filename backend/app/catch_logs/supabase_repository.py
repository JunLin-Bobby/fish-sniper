from typing import Any
from uuid import UUID

from pydantic import ValidationError

from app.catch_logs.schemas import CatchLogRecord
from app.db.client import SupabaseRestClient
from app.db.errors import DatabaseUnavailableError

SELECT_COLUMNS = (
    "id,user_id,species_name,caught_at,length_cm,weight_g,"
    "fishing_method,notes,created_at,updated_at"
)


class SupabaseCatchLogsRepository:
    """透過固定的 PostgREST 查詢結構存取私人紀錄，不接受任意前端 filter。"""

    def __init__(self, client: SupabaseRestClient) -> None:
        """保存可替換與可測試的 Supabase REST client。"""

        self._client = client

    @staticmethod
    def _parse_rows(rows: Any) -> list[CatchLogRecord]:
        """拒絕非列表或欄位無效的供應商回應，不能把異常誤認成空紀錄。"""

        if not isinstance(rows, list):
            raise DatabaseUnavailableError("Supabase returned invalid catch log rows.")
        try:
            return [CatchLogRecord.model_validate(row) for row in rows]
        except ValidationError as error:
            raise DatabaseUnavailableError("Supabase returned an invalid catch log.") from error

    @staticmethod
    def _owned_params(user_id: UUID, log_id: UUID) -> dict[str, str]:
        """讓讀取、更新和刪除在同一個資料庫操作內同時限定擁有者與紀錄。"""

        return {"user_id": f"eq.{user_id}", "id": f"eq.{log_id}", "select": SELECT_COLUMNS}

    async def create(self, user_id: UUID, values: dict[str, Any]) -> CatchLogRecord:
        """以後端驗證的 user UUID 建立紀錄，並要求資料庫回傳新資料。"""

        rows = self._parse_rows(
            await self._client.request(
                "POST",
                "catch_logs",
                params={"select": SELECT_COLUMNS},
                json={**values, "user_id": str(user_id)},
                prefer="return=representation",
            )
        )
        if len(rows) != 1:
            raise DatabaseUnavailableError("Supabase catch log creation returned no single row.")
        return rows[0]

    async def list_for_user(
        self, user_id: UUID, *, limit: int, offset: int
    ) -> list[CatchLogRecord]:
        """只讀取目前 user 的指定頁，避免將全部私人紀錄載入記憶體。"""

        return self._parse_rows(
            await self._client.request(
                "GET",
                "catch_logs",
                params={
                    "select": SELECT_COLUMNS,
                    "user_id": f"eq.{user_id}",
                    "order": "caught_at.desc,id.desc",
                    "limit": str(limit),
                    "offset": str(offset),
                },
            )
        )

    async def get_for_user(self, user_id: UUID, log_id: UUID) -> CatchLogRecord | None:
        """查詢一筆屬於目前 user 的紀錄，無權限與不存在都回傳 None。"""

        rows = self._parse_rows(
            await self._client.request(
                "GET",
                "catch_logs",
                params={**self._owned_params(user_id, log_id), "limit": "1"},
            )
        )
        return rows[0] if rows else None

    async def update_for_user(
        self, user_id: UUID, log_id: UUID, values: dict[str, Any]
    ) -> CatchLogRecord | None:
        """以原子性的 owner filter 更新紀錄，避免先查詢再寫入的權限缺口。"""

        rows = self._parse_rows(
            await self._client.request(
                "PATCH",
                "catch_logs",
                params=self._owned_params(user_id, log_id),
                json=values,
                prefer="return=representation",
            )
        )
        return rows[0] if rows else None

    async def delete_for_user(self, user_id: UUID, log_id: UUID) -> bool:
        """要求刪除結果以區分真正刪除與找不到資料，不先執行獨立的存在檢查。"""

        rows = self._parse_rows(
            await self._client.request(
                "DELETE",
                "catch_logs",
                params=self._owned_params(user_id, log_id),
                prefer="return=representation",
            )
        )
        return bool(rows)
