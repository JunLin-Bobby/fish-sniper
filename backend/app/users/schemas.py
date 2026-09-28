from uuid import UUID

from pydantic import BaseModel


class CurrentUserResponse(BaseModel):
    """回傳給已驗證 frontend 的安全使用者欄位。"""

    id: UUID
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
