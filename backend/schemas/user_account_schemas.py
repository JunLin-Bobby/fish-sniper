"""Account lifecycle schemas (delete account)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DeleteFishSniperAccountRequestBody(BaseModel):
    """Typed confirmation required to permanently delete the signed-in user."""

    confirmation: Literal["Delete"] = Field(
        ...,
        description='Must be exactly "Delete" (case-sensitive).',
    )
