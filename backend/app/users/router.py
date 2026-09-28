from fastapi import APIRouter

from app.auth.dependencies import CurrentUserDependency
from app.users.schemas import CurrentUserResponse

router = APIRouter(prefix="/api/v1", tags=["users"])


@router.get("/me", response_model=CurrentUserResponse)
def get_current_user_profile(current_user: CurrentUserDependency) -> CurrentUserResponse:
    """回傳 Bearer token 所代表的 FishSniper 使用者基本資料。"""

    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url,
    )
