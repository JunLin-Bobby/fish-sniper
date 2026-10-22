from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from app.db.client import SupabaseRestClient
from app.db.errors import DatabaseUnavailableError
from app.users.schemas import UserRecord

USER_SELECT_COLUMNS = "id,google_sub,email,display_name,avatar_url"


class SupabaseUsersRepository:
    """以 Supabase PostgREST 實作 users table 的查詢與寫入。"""

    def __init__(self, client: SupabaseRestClient) -> None:
        """保存由 dependency 建立的 Supabase REST client。"""

        self._client = client

    async def find_or_create_google_user(
        self,
        *,
        google_sub: str,
        email: str,
        display_name: str | None,
        avatar_url: str | None,
    ) -> UserRecord:
        """用 google_sub upsert user，並同步 email、顯示名稱與最近登入時間。"""

        now = datetime.now(UTC).isoformat()
        payload: dict[str, Any] = {
            "google_sub": google_sub,
            "email": email.strip().lower(),
            "display_name": display_name,
            "avatar_url": avatar_url,
            "last_login_at": now,
            "updated_at": now,
        }
        rows = await self._client.request(
            "POST",
            "users",
            params={"on_conflict": "google_sub", "select": USER_SELECT_COLUMNS},
            json=payload,
            prefer="resolution=merge-duplicates,return=representation",
        )
        return self._parse_single_user(rows)

    async def get_user_by_id(self, user_id: UUID) -> UserRecord | None:
        """以 FishSniper user UUID 查詢單一使用者，找不到時回傳 None。"""

        rows = await self._client.request(
            "GET",
            "users",
            params={
                "select": USER_SELECT_COLUMNS,
                "id": f"eq.{user_id}",
                "limit": "1",
            },
        )
        if not isinstance(rows, list) or not rows:
            return None
        return self._parse_single_user(rows)

    @staticmethod
    def _parse_single_user(rows: Any) -> UserRecord:
        """將 Supabase list response 的第一筆資料驗證成 UserRecord。"""

        if not isinstance(rows, list) or not rows:
            raise DatabaseUnavailableError("Supabase user write returned no row.")
        try:
            return UserRecord.model_validate(rows[0])
        except ValidationError as error:
            raise DatabaseUnavailableError("Supabase returned an invalid user row.") from error
