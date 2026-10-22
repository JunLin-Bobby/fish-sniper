from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserRecord(BaseModel):
    """users 功能共用的內部使用者資料，供 repository 與登入驗證使用。"""

    model_config = ConfigDict(extra="ignore")

    id: UUID
    google_sub: str
    email: str
    display_name: str | None = None
    avatar_url: str | None = None


class CurrentUserResponse(BaseModel):
    """回傳給已驗證 frontend 的安全使用者欄位。"""

    id: UUID
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
