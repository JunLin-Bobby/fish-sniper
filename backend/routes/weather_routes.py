"""Current weather route (OpenWeatherMap + TTL cache)."""

from datetime import UTC

from fastapi import APIRouter, HTTPException, Query, Request, status

from deps import (
    FishSniperPersistenceDep,
    FishSniperSettingsDep,
    ReferenceTimeUtcCallableDep,
    get_fish_sniper_weather_snapshot_cache_port,
)
from persistence.errors import FishSniperPersistenceUnavailableError
from rate_limiting import fish_sniper_api_limiter
from schemas.weather_schemas import CurrentWeatherResponseBody
from security import FishSniperUserIdDep
from weather.port import FishSniperOpenWeatherSnapshot
from weather.weather_errors import FishSniperWeatherUnavailableError
from weather.weather_service import fetch_or_refresh_cached_current_weather_snapshot_for_region

router = APIRouter()


def _map_snapshot_to_response_body(
    *, snapshot: FishSniperOpenWeatherSnapshot
) -> CurrentWeatherResponseBody:
    return CurrentWeatherResponseBody(
        temperature_c=snapshot.temperature_celsius,
        condition=snapshot.condition_label,
        condition_code=snapshot.condition_code,
        wind_speed_ms=snapshot.wind_speed_meters_per_second,
        pressure_hpa=snapshot.pressure_hectopascals,
        humidity_pct=snapshot.humidity_percent,
        fetched_at=snapshot.fetched_at_utc.astimezone(UTC),
    )


@router.get(
    "/current",
    summary="Fetch current weather for the signed-in user's saved region",
    description=(
        "Returns a cached OpenWeatherMap snapshot (30-minute TTL), or refreshes when stale. "
        "If the optional `region` query is provided, it is used as the lookup label; "
        "otherwise `user_preferences.region` must be configured."
    ),
    response_model=CurrentWeatherResponseBody,
    response_description="Metric weather snapshot including FishSniper condition_code mapping.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid bearer token."},
        status.HTTP_400_BAD_REQUEST: {"description": "User has not configured a region yet."},
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Per-email rate limit exceeded."},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Weather provider failed or OpenWeatherMap is not configured.",
        },
    },
)
@fish_sniper_api_limiter.limit("120/minute")
def handle_get_current_weather_for_signed_in_user_request(
    request: Request,
    fish_sniper_user_id: FishSniperUserIdDep,
    fish_sniper_persistence: FishSniperPersistenceDep,
    fish_sniper_backend_settings: FishSniperSettingsDep,
    reference_time_utc_callable: ReferenceTimeUtcCallableDep,
    region: str | None = Query(
        default=None,
        description="Optional override region label for this fetch (skips saved profile when set).",
    ),
) -> CurrentWeatherResponseBody:
    _ = request
    reference_time_utc = reference_time_utc_callable()
    if region is not None and region.strip():
        region_label = region.strip()
    else:
        try:
            preferences_row = fish_sniper_persistence.fetch_user_preferences_row_for_user_id(
                fish_sniper_user_id=fish_sniper_user_id,
            )
        except FishSniperPersistenceUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error": "Database is temporarily unavailable"},
            ) from exc

        if preferences_row is None or not preferences_row.profile_region_display_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "User region is not configured"},
            )
        region_label = preferences_row.profile_region_display_name

    try:
        snapshot = fetch_or_refresh_cached_current_weather_snapshot_for_region(
            profile_region_display_name=region_label,
            fish_sniper_backend_settings=fish_sniper_backend_settings,
            weather_snapshot_cache_port=get_fish_sniper_weather_snapshot_cache_port(),
            reference_time_utc=reference_time_utc,
        )
    except FishSniperWeatherUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Weather service unavailable"},
        ) from None

    return _map_snapshot_to_response_body(snapshot=snapshot)
