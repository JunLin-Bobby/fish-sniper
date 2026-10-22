from uuid import UUID

from app.users.schemas import UserRecord


class InMemoryUsersRepository:
    """API 與 service tests 共用的記憶體 users repository。"""

    def __init__(self, users: list[UserRecord] | None = None) -> None:
        """以指定 users 建立可預測、且不需要 Supabase 的測試 repository。"""

        self.users_by_id = {user.id: user for user in users or []}
        self.last_google_identity: dict[str, str | None] | None = None

    async def find_or_create_google_user(
        self,
        *,
        google_sub: str,
        email: str,
        display_name: str | None,
        avatar_url: str | None,
    ) -> UserRecord:
        """記錄 Google identity，並回傳相同 google_sub 的既有測試 user。"""

        self.last_google_identity = {
            "google_sub": google_sub,
            "email": email,
            "display_name": display_name,
            "avatar_url": avatar_url,
        }
        for user in self.users_by_id.values():
            if user.google_sub == google_sub:
                return user
        raise AssertionError("Test repository has no user for this google_sub.")

    async def get_user_by_id(self, user_id: UUID) -> UserRecord | None:
        """依 UUID 回傳測試 user，模擬 protected route 的 database lookup。"""

        return self.users_by_id.get(user_id)
