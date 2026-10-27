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

        return {
            "user_id": f"eq.{user_id}",
            "id": f"eq.{log_id}",
            "select": SELECT_COLUMNS,
            "status": "eq.ready",
        }

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
                    "status": "eq.ready",
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

    async def begin_submission(
        self,
        user_id: UUID,
        submission_id: UUID,
        fingerprint: str,
        log_id: UUID,
        values: dict[str, Any],
        photos: list[dict[str, Any]],
        attempt_id: UUID | None = None,
    ) -> dict[str, Any]:
        """用單筆交易建立草稿、照片 manifest 與去重收據，不公開未完成紀錄。"""

        result = await self._client.request(
            "POST",
            "rpc/begin_catch_submission",
            json={
                "p_user_id": str(user_id),
                "p_submission_id": str(submission_id),
                "p_fingerprint": fingerprint,
                "p_log_id": str(log_id),
                "p_values": values,
                "p_photos": photos,
                "p_attempt_id": str(attempt_id) if attempt_id else None,
            },
        )
        if not isinstance(result, dict):
            raise DatabaseUnavailableError("Invalid submission response.")
        return result

    async def register_submission(
        self, user_id: UUID, submission_id: UUID, attempt_id: UUID, seconds: int
    ) -> dict[str, Any]:
        """接收 multipart 前持久登記，只有本次 server attempt 可以繼續或標記失敗。"""

        result = await self._client.request(
            "POST",
            "rpc/register_catch_submission",
            json={
                "p_user_id": str(user_id),
                "p_submission_id": str(submission_id),
                "p_attempt_id": str(attempt_id),
                "p_seconds": seconds,
            },
        )
        if not isinstance(result, dict):
            raise DatabaseUnavailableError("Invalid registration response.")
        return result

    async def start_processing(
        self, user_id: UUID, submission_id: UUID, attempt_id: UUID, seconds: int
    ) -> bool:
        """收完整個請求後切換至處理期限，過期或非擁有 attempt 一律拒絕。"""

        return (
            await self._client.request(
                "POST",
                "rpc/start_catch_processing",
                json={
                    "p_user_id": str(user_id),
                    "p_submission_id": str(submission_id),
                    "p_attempt_id": str(attempt_id),
                    "p_seconds": seconds,
                },
            )
            is True
        )

    async def resolve_submission(self, user_id: UUID, submission_id: UUID) -> dict[str, Any]:
        """原子查詢並結束過期／不存在操作，阻擋回應遺失後的晚到請求。"""

        result = await self._client.request(
            "POST",
            "rpc/resolve_catch_submission",
            json={
                "p_user_id": str(user_id),
                "p_submission_id": str(submission_id),
            },
        )
        if not isinstance(result, dict):
            raise DatabaseUnavailableError("Invalid recovery response.")
        return result

    async def fail_submission(
        self, user_id: UUID, submission_id: UUID, attempt_id: UUID
    ) -> dict[str, Any]:
        """只終結自己的 attempt；如果發布已 COMMIT，必須保留成功結果。"""

        result = await self._client.request(
            "POST",
            "rpc/fail_catch_submission",
            json={
                "p_user_id": str(user_id),
                "p_submission_id": str(submission_id),
                "p_attempt_id": str(attempt_id),
            },
        )
        if not isinstance(result, dict):
            raise DatabaseUnavailableError("Invalid failure response.")
        return result

    async def expire_submissions(self) -> None:
        """恢復沒有 catch row 的過期登記，讓程序中斷也不會永久 pending。"""

        await self._client.request("POST", "rpc/expire_catch_submissions", json={})

    async def publish_submission(self, user_id: UUID, log_id: UUID) -> CatchLogRecord:
        """呼叫單一 PostgreSQL transaction，讓魚獲與全部照片一起變成 ready。"""

        row = await self._client.request(
            "POST",
            "rpc/publish_catch_submission",
            json={
                "p_user_id": str(user_id),
                "p_log_id": str(log_id),
            },
        )
        rows = self._parse_rows([row])
        return rows[0]

    async def claim_cleanup(
        self,
        user_id: UUID,
        log_id: UUID,
        *,
        delete: bool = False,
        stale: bool = False,
    ) -> bool:
        """持鎖取消草稿或標記整筆刪除；補償不能取得已發布紀錄的清理權。"""

        return (
            await self._client.request(
                "POST",
                "rpc/claim_catch_cleanup",
                json={
                    "p_user_id": str(user_id),
                    "p_log_id": str(log_id),
                    "p_delete": delete,
                    "p_stale": stale,
                },
            )
            is True
        )

    async def finish_cleanup(self, user_id: UUID, log_id: UUID) -> bool:
        """只有 service 確認檔案清理成功且過了寬限期，才移除草稿與路徑。"""

        return (
            await self._client.request(
                "POST",
                "rpc/finish_catch_cleanup",
                json={
                    "p_user_id": str(user_id),
                    "p_log_id": str(log_id),
                },
            )
            is True
        )

    async def cleanup_candidates(self) -> list[dict[str, Any]]:
        """有界載入隱藏紀錄；是否過期由持鎖的 DB 操作再次確認。"""

        rows = await self._client.request(
            "GET",
            "catch_logs",
            params={
                "select": "id,user_id,status",
                "status": "neq.ready",
                "order": "updated_at.asc",
                "limit": "100",
            },
        )
        if not isinstance(rows, list):
            raise DatabaseUnavailableError("Invalid cleanup response.")
        return rows

    async def get_submission(self, user_id: UUID, submission_id: UUID) -> dict[str, Any] | None:
        """只回目前擁有者的提交結果，不回傳魚獲內容或檔案路徑。"""

        rows = await self._client.request(
            "GET",
            "catch_log_submissions",
            params={
                "select": "status,log_id",
                "user_id": f"eq.{user_id}",
                "submission_id": f"eq.{submission_id}",
                "limit": "1",
            },
        )
        if not isinstance(rows, list):
            raise DatabaseUnavailableError("Invalid submission status.")
        return rows[0] if rows else None
