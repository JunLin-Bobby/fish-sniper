"""Bass lure strategy agent route (LangGraph + Gemini)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from agent.fish_sniper_strategy_lang_graph import invoke_fish_sniper_strategy_graph
from deps import (
    FishSniperEmbeddingClientDep,
    FishSniperPersistenceDep,
    FishSniperSettingsDep,
    ReferenceTimeUtcCallableDep,
    get_fish_sniper_weather_snapshot_cache_port,
)
from rate_limiting import fish_sniper_apply_api_rate_limit
from schemas.agent_schemas import (
    GenerateBassStrategyFallbackResponseBody,
    GenerateBassStrategyRequestBody,
    GenerateBassStrategySuccessResponseBody,
)
from security import FishSniperUserIdDep

router = APIRouter()


@router.post(
    "/strategy",
    summary="Generate a bass lure strategy via LangGraph and Gemini",
    description=(
        "Runs the FishSniper agent pipeline (weather, optional RAG over fishing logs, "
        "single Gemini JSON strategy). "
        "Send `region` for OpenWeatherMap; provide `manual_weather` to override OWM "
        "(e.g. what-if analysis or when OWM is unavailable)."
    ),
    responses={
        status.HTTP_200_OK: {
            "description": (
                "Structured strategy JSON or a fallback envelope when JSON validation fails."
            ),
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Region is missing or request fields are invalid."
        },
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid bearer token."},
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Per-email rate limit exceeded."},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Database, weather, or Gemini is unavailable for this request.",
        },
    },
)
@fish_sniper_apply_api_rate_limit("30/hour")
async def handle_generate_bass_lure_strategy_request(
    request: Request,
    request_body: GenerateBassStrategyRequestBody,
    fish_sniper_user_id: FishSniperUserIdDep,
    fish_sniper_persistence: FishSniperPersistenceDep,
    fish_sniper_backend_settings: FishSniperSettingsDep,
    reference_time_utc_callable: ReferenceTimeUtcCallableDep,
    embedding_client: FishSniperEmbeddingClientDep,
) -> GenerateBassStrategySuccessResponseBody | GenerateBassStrategyFallbackResponseBody:
    _ = request
    reference_time_utc = reference_time_utc_callable()
    final_state = await invoke_fish_sniper_strategy_graph(
        fish_sniper_user_id=fish_sniper_user_id,
        parsed_request_body=request_body,
        fish_sniper_backend_settings=fish_sniper_backend_settings,
        persistence_port=fish_sniper_persistence,
        weather_snapshot_cache_port=get_fish_sniper_weather_snapshot_cache_port(),
        reference_time_utc=reference_time_utc,
        embedding_client=embedding_client,
    )

    terminal_http_status = final_state.get("terminal_http_status")
    if isinstance(terminal_http_status, int):
        envelope = final_state.get("terminal_error_envelope")
        detail: dict | str = (
            envelope if isinstance(envelope, dict) else {"error": "Request cannot be completed"}
        )
        raise HTTPException(status_code=terminal_http_status, detail=detail)

    if final_state.get("success_response_body") is not None:
        return GenerateBassStrategySuccessResponseBody.model_validate(
            final_state["success_response_body"]
        )

    if final_state.get("fallback_response_body") is not None:
        return GenerateBassStrategyFallbackResponseBody.model_validate(
            final_state["fallback_response_body"]
        )

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"error": "Strategy pipeline returned no result"},
    )
