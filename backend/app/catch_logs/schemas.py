from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

SpeciesName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
PositiveMeasurement = Annotated[float, Field(gt=0, allow_inf_nan=False)]
FishingMethod = Literal["lure", "front_strike", "bottom", "hand_pole", "fly_fishing", "other"]


class CatchLogOptionalFields(BaseModel):
    """共用選填欄位；2B 不接受照片、座標或由前端指定的擁有者。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    length_cm: PositiveMeasurement | None = None
    weight_g: PositiveMeasurement | None = None
    fishing_method: FishingMethod | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        """將空白備註統一視為未填，避免儲存沒有內容的字串。"""

        return value or None


class CatchLogCreate(CatchLogOptionalFields):
    """建立一隻魚的紀錄，魚種與含時區的釣獲時間必填。"""

    species_name: SpeciesName
    caught_at: AwareDatetime


class CatchLogPatch(CatchLogOptionalFields):
    """只修改有傳入的欄位；選填值可用 null 清空，必填值不可清空。"""

    species_name: SpeciesName | None = None
    caught_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> Self:
        """拒絕空修改與清空必填欄位，並區分未傳入和明確傳入 null。"""

        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied.")
        for field in ("species_name", "caught_at"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class CatchLogRecord(CatchLogCreate):
    """驗證資料庫回傳的完整紀錄，並作為私人 API 的 response。"""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    id: UUID
    user_id: UUID
    created_at: AwareDatetime
    updated_at: AwareDatetime


class CatchLogPage(BaseModel):
    """回傳有上限的紀錄列表；has_more 表示下一頁是否仍有資料。"""

    items: list[CatchLogRecord]
    limit: int
    offset: int
    has_more: bool
