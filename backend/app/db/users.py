from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserRecord(BaseModel):
    """FishSniper 在 Supabase users table 中使用的核心使用者資料。"""

    model_config = ConfigDict(extra="ignore")

    id: UUID
    google_sub: str
    email: str
    display_name: str | None = None
    avatar_url: str | None = None


class UsersRepository(Protocol):
    """Auth 與 protected routes 所依賴的 users persistence 介面。"""

    async def find_or_create_google_user(
        self,
        *,
        google_sub: str,
        email: str,
        display_name: str | None,
        avatar_url: str | None,
    ) -> UserRecord:
        """以 Google subject 原子性地尋找或建立 FishSniper user。"""

        ...

    async def get_user_by_id(self, user_id: UUID) -> UserRecord | None:
        """依 FishSniper 內部 UUID 查詢目前仍存在的使用者。"""

        ...
