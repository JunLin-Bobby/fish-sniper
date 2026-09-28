from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """提供 deployment 與監控系統使用的基本存活檢查。"""

    return {"status": "ok"}
