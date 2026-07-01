"""Pydantic models for user preferences and account lifecycle."""

from typing import Literal

from pydantic import BaseModel, Field


class SaveUserPreferencesRequestBody(BaseModel):
    """Request body for saving the angler's home region used for weather lookup."""

    region: str = Field(
        min_length=1,
        description="City or region label stored on the user profile (e.g. Boston).",
    )


class SaveUserPreferencesResponseBody(BaseModel):
    """Response after preferences are persisted."""

    message: str = Field(description="Confirmation that preferences were saved.")


class UserPreferencesResponseBody(BaseModel):
    """User preferences returned to the client."""

    region: str | None = Field(
        description="Saved region label, or null when onboarding is not completed.",
    )
    onboarding_completed: bool = Field(
        description="True after the user has submitted onboarding at least once.",
    )


class DeleteFishSniperAccountRequestBody(BaseModel):
    """Typed confirmation required to permanently delete the signed-in user."""

    confirmation: Literal["Delete"] = Field(
        ...,
        description='Must be exactly "Delete" (case-sensitive).',
    )
