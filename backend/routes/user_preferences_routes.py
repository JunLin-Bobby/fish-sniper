"""User onboarding preferences routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from deps import FishSniperPersistenceDep, ReferenceTimeUtcCallableDep
from persistence.errors import FishSniperPersistenceUnavailableError
from schemas.user_preferences_schemas import (
    SaveUserPreferencesRequestBody,
    SaveUserPreferencesResponseBody,
    UserPreferencesResponseBody,
)
from security import FishSniperUserIdDep

router = APIRouter()


@router.get(
    "/preferences",
    summary="Get the signed-in user's saved fishing region preferences",
    description=(
        "Reads `user_preferences` for the JWT subject. "
        "If no row exists yet, returns `region=null` and `onboarding_completed=false`."
    ),
    response_model=UserPreferencesResponseBody,
    response_description="Region label and onboarding completion flag for the current user.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid bearer token."},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Database is not configured or could not read preferences.",
        },
    },
)
def handle_get_user_preferences_request(
    fish_sniper_user_id: FishSniperUserIdDep,
    fish_sniper_persistence: FishSniperPersistenceDep,
) -> UserPreferencesResponseBody:
    try:
        preferences_row = fish_sniper_persistence.fetch_user_preferences_row_for_user_id(
            fish_sniper_user_id=fish_sniper_user_id,
        )
        if preferences_row is None:
            return UserPreferencesResponseBody(region=None, onboarding_completed=False)
        return UserPreferencesResponseBody(
            region=preferences_row.profile_region_display_name,
            onboarding_completed=preferences_row.profile_onboarding_completed_flag,
        )
    except FishSniperPersistenceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Database is temporarily unavailable"},
        ) from exc


@router.post(
    "/preferences",
    summary="Save onboarding region used for weather lookup",
    description=(
        "Upserts `user_preferences` for the JWT subject, marks onboarding as completed, "
        "and updates `updated_at`."
    ),
    response_model=SaveUserPreferencesResponseBody,
    response_description="Confirms the preferences upsert succeeded.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid bearer token."},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Database is not configured or could not upsert preferences.",
        },
    },
)
def handle_save_user_preferences_request(
    request_body: SaveUserPreferencesRequestBody,
    fish_sniper_user_id: FishSniperUserIdDep,
    fish_sniper_persistence: FishSniperPersistenceDep,
    reference_time_utc_callable: ReferenceTimeUtcCallableDep,
) -> SaveUserPreferencesResponseBody:
    reference_time_utc = reference_time_utc_callable()
    try:
        fish_sniper_persistence.upsert_user_preferences_region_for_user_id(
            fish_sniper_user_id=fish_sniper_user_id,
            profile_region_display_name=request_body.region.strip(),
            profile_onboarding_completed_flag=True,
            preferences_updated_at_utc=reference_time_utc,
        )
    except FishSniperPersistenceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Database is temporarily unavailable"},
        ) from exc

    return SaveUserPreferencesResponseBody(message="Preferences saved")
