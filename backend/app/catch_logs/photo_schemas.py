from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PhotoMetadata(BaseModel):
    """僅保留必要的候選資訊；GPS 不代表使用者已確認的釣點。"""

    captured_at: datetime | None = None
    local_captured_at: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    longitude: float | None = Field(default=None, ge=-180, le=180, allow_inf_nan=False)


@dataclass(frozen=True, slots=True)
class PreparedPhoto:
    """圖片處理完成後的 JPEG 與擷取資訊；不包含原始 EXIF。"""

    content: bytes
    width: int
    height: int
    metadata: PhotoMetadata


class CatchPhotoRecord(BaseModel):
    """資料庫照片紀錄，只保存路徑與最小必要資訊。"""

    model_config = ConfigDict(extra="ignore")
    id: UUID
    catch_log_id: UUID
    photo_order: int = Field(ge=1, le=2)
    bucket: str
    object_path: str
    width: int
    height: int
    size_bytes: int
    status: str
    metadata: PhotoMetadata


class CatchPhotoResponse(BaseModel):
    """不暴露 bucket 路徑，以有期限的網址顯示私人照片。"""

    id: UUID
    photo_order: int
    width: int
    height: int
    url: str
    expires_at: datetime
    metadata: PhotoMetadata


class CatchPhotoValidationError(ValueError):
    """照片格式、大小、張數或像素不符合限制。"""


class CatchSubmissionConflict(RuntimeError):
    """同次提交仍在執行、需要清理，或識別碼被用於不同內容。"""
