"""Bass lure strategy agent route (LangGraph + multi-provider LLM)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from agent.fish_sniper_strategy_lang_graph import invoke_fish_sniper_strategy_graph
from deps import (
    FishSniperEmbeddingClientDep,
    FishSniperPersistenceDep,
    FishSniperSettingsDep,
    ReferenceTimeUtcCallableDep,
    TextGenerationRouterDep,
    get_fish_sniper_weather_snapshot_cache_port,
)
from llm.strategy_model_resolution import (
    StrategyLlmModelResolutionError,
    resolve_strategy_llm_model_id,
)
from rate_limiting import fish_sniper_apply_api_rate_limit
from schemas.agent_schemas import (
    GenerateBassStrategyFallbackResponseBody,
    GenerateBassStrategyRequestBody,
    GenerateBassStrategySuccessResponseBody,
    ListAgentLlmModelsResponseBody,
    ListedAgentLlmModelItem,
)
from security import FishSniperUserIdDep

router = APIRouter()


@router.get(
    "/models",
    summary="List strategy text-generation models available in this environment",
    description=(
        "Returns catalog models whose API keys are configured in server settings. "
        "Use `default_model_id` when the client omits `llm_model_id` on POST /agent/strategy."
    ),
    response_model=ListAgentLlmModelsResponseBody,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid bearer token."},
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Per-email rate limit exceeded."},
    },
)
@fish_sniper_apply_api_rate_limit("120/minute")
def handle_list_agent_llm_models_request(
    request: Request,
    fish_sniper_user_id: FishSniperUserIdDep,
    fish_sniper_backend_settings: FishSniperSettingsDep,
    text_generation_router: TextGenerationRouterDep,
) -> ListAgentLlmModelsResponseBody:
    _ = request
    _ = fish_sniper_user_id
    model_registry = text_generation_router.model_registry
    listed_models = model_registry.list_available(
        backend_settings=fish_sniper_backend_settings,
    )
    return ListAgentLlmModelsResponseBody(
        models=[
            ListedAgentLlmModelItem(
                id=listed_model.id,
                display_name=listed_model.display_name,
                provider=listed_model.provider,
            )
            for listed_model in listed_models
        ],
        default_model_id=model_registry.default_model_id(),
    )


@router.post(
    "/strategy",
    response_model=None,
    summary="Generate a bass lure strategy via LangGraph",
    description=(
        "Runs the FishSniper agent pipeline (weather, optional RAG over fishing logs, "
        "single structured LLM JSON strategy). "
        "Send `region` for OpenWeatherMap; provide `manual_weather` to override OWM "
        "(e.g. what-if analysis or when OWM is unavailable). "
        "Optional `llm_model_id` selects a catalog model (see GET /agent/models)."
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
            "description": (
                "Database, weather, or the strategy LLM is unavailable for this request."
            ),
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
    text_generation_router: TextGenerationRouterDep,
) -> (
    GenerateBassStrategySuccessResponseBody
    | GenerateBassStrategyFallbackResponseBody
    | JSONResponse
):
    _ = request
    model_resolution = resolve_strategy_llm_model_id(
        requested_llm_model_id=request_body.llm_model_id,
        model_registry=text_generation_router.model_registry,
        backend_settings=fish_sniper_backend_settings,
    )
    if isinstance(model_resolution, StrategyLlmModelResolutionError):
        if model_resolution.http_status == 400:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=model_resolution.envelope,
            )
        raise HTTPException(
            status_code=model_resolution.http_status,
            detail=model_resolution.envelope,
        )

    reference_time_utc = reference_time_utc_callable()
    final_state = await invoke_fish_sniper_strategy_graph(
        fish_sniper_user_id=fish_sniper_user_id,
        parsed_request_body=request_body,
        fish_sniper_backend_settings=fish_sniper_backend_settings,
        persistence_port=fish_sniper_persistence,
        weather_snapshot_cache_port=get_fish_sniper_weather_snapshot_cache_port(),
        reference_time_utc=reference_time_utc,
        embedding_client=embedding_client,
        text_generation_router=text_generation_router,
        llm_model_id=model_resolution.model_id,
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
