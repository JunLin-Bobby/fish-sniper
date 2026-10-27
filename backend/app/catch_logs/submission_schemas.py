from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SubmissionResult(BaseModel):
    """只回傳恢復所需結果與再次確認時間，不暴露照片、路徑或 attempt token。"""

    status: Literal["pending", "ready", "failed", "deleted"]
    log_id: UUID | None = None
    retry_after_ms: int = Field(default=0, ge=0)
