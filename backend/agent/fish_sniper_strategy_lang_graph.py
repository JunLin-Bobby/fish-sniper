"""LangGraph orchestration for P2 bass strategy (Step 3 RAG short-circuited)."""

from __future__ import annotations

import logging
from contextlib import nullcontext
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from agent.fish_sniper_strategy_prompt_assembler import (
    build_battle_plan_system_prompt_for_markdown_summary,
    build_general_best_practice_system_prompt_for_bass_strategy,
    build_shared_user_prompt_for_environmental_json_strategy,
)
from agent.gemini_text_generation import (
    FishSniperGeminiInvocationError,
    generate_text_from_gemini_with_system_and_user_prompts,
)
from agent.json_payload_extraction import (
    extract_first_json_object_dict_from_llm_text,
    validate_non_empty_string_fields_exist,
)
from agent.langfuse_observability import (
    build_langfuse_client_or_none,
    flush_langfuse_client_best_effort,
)
from persistence.errors import FishSniperPersistenceUnavailableError
from persistence.port import FishSniperPersistencePort
from schemas.agent_schemas import (
    GenerateBassStrategyFallbackResponseBody,
    GenerateBassStrategyRequestBody,
    GenerateBassStrategySuccessResponseBody,
    ManualWeatherPayload,
    WeatherSnapshotPayload,
)
from settings import FishSniperBackendSettings
from weather.port import WeatherSnapshotCachePort
from weather.weather_errors import FishSniperWeatherUnavailableError
from weather.weather_service import fetch_or_refresh_cached_current_weather_snapshot_for_region

logger = logging.getLogger(__name__)

FishSniperStrategyGraphState = dict[str, Any]


class FishSniperStrategyGraphStateSchema(TypedDict, total=False):
    """Per-key channels for LangGraph; avoids ``StateGraph(dict)`` __root__ replacement bug.

    LangGraph treats plain ``dict`` as a single ``__root__`` ``LastValue`` channel, so each
    node update **replaced** the entire state and dropped keys like ``parsed_request_body``.
    Declared keys get independent LastValue channels and merge as intended.
    """

    fish_sniper_user_id: UUID
    parsed_request_body: GenerateBassStrategyRequestBody
    fish_sniper_backend_settings: FishSniperBackendSettings
    persistence_port: FishSniperPersistencePort
    weather_snapshot_cache_port: WeatherSnapshotCachePort
    reference_time_utc: datetime
    langfuse_client: Any
    structured_json_retry_count: int
    terminal_http_status: int
    terminal_error_envelope: dict[str, Any]
    profile_region_display_name: str
    temperature_celsius: float
    pressure_hectopascals: int
    wind_speed_meters_per_second: float
    condition_code: str
    retrieved_log_count: int
    retrieved_logs: list[Any]
    has_personal_log: bool
    structured_strategy_system_prompt: str
    structured_strategy_user_prompt: str
    raw_structured_strategy_llm_output: str
    structured_json_valid: bool
    strategy_fallback: bool
    structured_strategy_parsed_dict: dict[str, Any]
    battle_plan_summary_markdown: str
    success_response_body: dict[str, Any]
    fallback_response_body: dict[str, Any]

_STRUCTURED_STRATEGY_JSON_FIELD_NAME_LIST = [
    "lure_type",
    "lure_color",
    "retrieve_speed",
    "target_zone",
    "time_window",
    "confidence_note",
]


def _read_terminal_http_status_from_state(state: FishSniperStrategyGraphState) -> int | None:
    return state.get("terminal_http_status")


def node_load_user_region_and_open_weather_map_snapshot(
    state: FishSniperStrategyGraphState,
) -> FishSniperStrategyGraphState:
    """Step 2 analogue: load `region` and weather (or manual weather) into graph state."""

    if _read_terminal_http_status_from_state(state) is not None:
        return {}

    fish_sniper_user_id: UUID = state["fish_sniper_user_id"]
    request_body: GenerateBassStrategyRequestBody = state["parsed_request_body"]
    persistence: FishSniperPersistencePort = state["persistence_port"]
    settings: FishSniperBackendSettings = state["fish_sniper_backend_settings"]
    weather_cache: WeatherSnapshotCachePort = state["weather_snapshot_cache_port"]
    reference_time_utc: datetime = state["reference_time_utc"]

    langfuse_client = state.get("langfuse_client")
    span_cm = (
        langfuse_client.start_as_current_span(
            name="fetch_weather_for_strategy", metadata={"step": "2"}
        )
        if langfuse_client is not None
        else nullcontext()
    )
    with span_cm:
        try:
            preferences_row = persistence.fetch_user_preferences_row_for_user_id(
                fish_sniper_user_id=fish_sniper_user_id,
            )
        except FishSniperPersistenceUnavailableError:
            return {
                "terminal_http_status": 503,
                "terminal_error_envelope": {"error": "Database is temporarily unavailable"},
            }

        if preferences_row is None or not preferences_row.profile_region_display_name.strip():
            return {
                "terminal_http_status": 400,
                "terminal_error_envelope": {"error": "User region is not configured"},
            }

        region = preferences_row.profile_region_display_name.strip()
        try:
            snapshot = fetch_or_refresh_cached_current_weather_snapshot_for_region(
                profile_region_display_name=region,
                fish_sniper_backend_settings=settings,
                weather_snapshot_cache_port=weather_cache,
                reference_time_utc=reference_time_utc,
            )
            return {
                "profile_region_display_name": region,
                "temperature_celsius": snapshot.temperature_celsius,
                "pressure_hectopascals": snapshot.pressure_hectopascals,
                "wind_speed_meters_per_second": snapshot.wind_speed_meters_per_second,
                "condition_code": snapshot.condition_code,
            }
        except FishSniperWeatherUnavailableError:
            manual_weather: ManualWeatherPayload | None = request_body.manual_weather
            if manual_weather is None:
                return {
                    "terminal_http_status": 503,
                    "terminal_error_envelope": {"error": "Weather service unavailable"},
                }
            return {
                "profile_region_display_name": region,
                "temperature_celsius": manual_weather.temperature_c,
                "pressure_hectopascals": manual_weather.pressure_hpa,
                "wind_speed_meters_per_second": manual_weather.wind_speed_ms,
                "condition_code": manual_weather.condition_code,
            }


def node_short_circuit_personal_log_retrieval_for_p2(
    state: FishSniperStrategyGraphState,
) -> FishSniperStrategyGraphState:
    """Step 3 stub: Pinecone/RAG is not wired in P2."""

    if _read_terminal_http_status_from_state(state) is not None:
        return {}

    langfuse_client = state.get("langfuse_client")
    span_cm = (
        langfuse_client.start_as_current_span(
            name="search_fishing_log_stub", metadata={"step": "3"}
        )
        if langfuse_client is not None
        else nullcontext()
    )
    with span_cm:
        return {
            "retrieved_log_count": 0,
            "retrieved_logs": [],
            "has_personal_log": False,
        }


def node_assemble_prompts_for_general_branch(
    state: FishSniperStrategyGraphState,
) -> FishSniperStrategyGraphState:
    """Step 4: prompts for the no-log branch."""

    if _read_terminal_http_status_from_state(state) is not None:
        return {}

    langfuse_client = state.get("langfuse_client")
    span_cm = (
        langfuse_client.start_as_current_span(name="build_system_prompt", metadata={"step": "4"})
        if langfuse_client is not None
        else nullcontext()
    )
    with span_cm:
        request_body: GenerateBassStrategyRequestBody = state["parsed_request_body"]
        system_prompt = build_general_best_practice_system_prompt_for_bass_strategy()
        user_prompt = build_shared_user_prompt_for_environmental_json_strategy(
            region=state["profile_region_display_name"],
            fishing_location=request_body.fishing_location.strip(),
            fishing_scene=request_body.fishing_scene.strip(),
            water_depth_m=request_body.water_depth_m,
            temperature_c=state["temperature_celsius"],
            pressure_hpa=state["pressure_hectopascals"],
            wind_speed_ms=state["wind_speed_meters_per_second"],
            condition_code=state["condition_code"],
        )
        return {
            "structured_strategy_system_prompt": system_prompt,
            "structured_strategy_user_prompt": user_prompt,
        }


def node_invoke_gemini_for_structured_json_strategy(
    state: FishSniperStrategyGraphState,
) -> FishSniperStrategyGraphState:
    """Step 5: first Gemini call."""

    if _read_terminal_http_status_from_state(state) is not None:
        return {}

    settings: FishSniperBackendSettings = state["fish_sniper_backend_settings"]
    langfuse_client = state.get("langfuse_client")
    span_cm = (
        langfuse_client.start_as_current_span(name="generate_lure_strategy", metadata={"step": "5"})
        if langfuse_client is not None
        else nullcontext()
    )
    with span_cm:
        system_prompt = state["structured_strategy_system_prompt"]
        user_prompt = state["structured_strategy_user_prompt"]
        try:
            raw_text = generate_text_from_gemini_with_system_and_user_prompts(
                fish_sniper_backend_settings=settings,
                system_instruction=system_prompt,
                user_prompt=user_prompt,
            )
        except FishSniperGeminiInvocationError:
            logger.exception("Gemini structured strategy call failed")
            return {
                "terminal_http_status": 503,
                "terminal_error_envelope": {"error": "Strategy model is temporarily unavailable"},
                "raw_structured_strategy_llm_output": "",
            }

        gen_cm = (
            langfuse_client.start_as_current_generation(
                name="gemini_structured_strategy",
                model=settings.gemini_model,
                input=f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}",
                output=raw_text,
            )
            if langfuse_client is not None
            else nullcontext()
        )
        with gen_cm:
            pass

        return {"raw_structured_strategy_llm_output": raw_text}


def node_parse_and_validate_structured_json_strategy(
    state: FishSniperStrategyGraphState,
) -> FishSniperStrategyGraphState:
    """Step 6: JSON validation with bounded retries (retry_count)."""

    if _read_terminal_http_status_from_state(state) is not None:
        return {}

    langfuse_client = state.get("langfuse_client")
    span_cm = (
        langfuse_client.start_as_current_span(name="validate_llm_output", metadata={"step": "6"})
        if langfuse_client is not None
        else nullcontext()
    )
    with span_cm:
        raw_text = state.get("raw_structured_strategy_llm_output") or ""
        retry_count = int(state.get("structured_json_retry_count") or 0)
        try:
            parsed = extract_first_json_object_dict_from_llm_text(raw_llm_text=raw_text)
            validate_non_empty_string_fields_exist(
                parsed_json_object=parsed,
                required_field_name_list=_STRUCTURED_STRATEGY_JSON_FIELD_NAME_LIST,
            )
            return {
                "structured_json_retry_count": retry_count,
                "structured_strategy_parsed_dict": parsed,
                "structured_json_valid": True,
                "strategy_fallback": False,
            }
        except ValueError as exc:
            logger.info("Structured JSON validation failed (attempt=%s): %s", retry_count + 1, exc)
            next_retry = retry_count + 1
            if next_retry >= 2:
                return {
                    "structured_json_retry_count": next_retry,
                    "structured_json_valid": False,
                    "strategy_fallback": True,
                }
            return {
                "structured_json_retry_count": next_retry,
                "structured_json_valid": False,
                "strategy_fallback": False,
            }


def route_after_structured_json_validation(
    state: FishSniperStrategyGraphState,
) -> Literal[
    "retry_structured_generation",
    "battle_plan",
    "fallback_done",
    "terminal_stop",
]:
    if _read_terminal_http_status_from_state(state) is not None:
        return "terminal_stop"
    if state.get("strategy_fallback") is True:
        return "fallback_done"
    if state.get("structured_json_valid") is True:
        return "battle_plan"
    return "retry_structured_generation"


def route_after_load_region_and_weather(
    state: FishSniperStrategyGraphState,
) -> Literal["continue", "terminal_stop"]:
    if _read_terminal_http_status_from_state(state) is not None:
        return "terminal_stop"
    return "continue"


def node_no_op_pipeline_terminal_stop(
    state: FishSniperStrategyGraphState,
) -> FishSniperStrategyGraphState:
    """LangGraph requires a node for early exits; terminal metadata already lives on state."""

    _ = state
    return {}


def node_invoke_gemini_for_battle_plan_markdown(
    state: FishSniperStrategyGraphState,
) -> FishSniperStrategyGraphState:
    """Step 7a: second Gemini call for markdown battle plan."""

    if _read_terminal_http_status_from_state(state) is not None:
        return {}

    settings: FishSniperBackendSettings = state["fish_sniper_backend_settings"]
    request_body: GenerateBassStrategyRequestBody = state["parsed_request_body"]
    parsed = state["structured_strategy_parsed_dict"]

    langfuse_client = state.get("langfuse_client")
    span_cm = (
        langfuse_client.start_as_current_span(name="format_final_response", metadata={"step": "7"})
        if langfuse_client is not None
        else nullcontext()
    )
    with span_cm:
        system_prompt = build_battle_plan_system_prompt_for_markdown_summary(
            fishing_location=request_body.fishing_location.strip(),
            temperature_c=state["temperature_celsius"],
            condition_code=state["condition_code"],
            wind_speed_ms=state["wind_speed_meters_per_second"],
            fishing_scene=request_body.fishing_scene.strip(),
            water_depth_m=request_body.water_depth_m,
            lure_type=str(parsed["lure_type"]),
            lure_color=str(parsed["lure_color"]),
            retrieve_speed=str(parsed["retrieve_speed"]),
            target_zone=str(parsed["target_zone"]),
            time_window=str(parsed["time_window"]),
        )
        user_prompt = (
            "Write the battle plan now. "
            "Remember: markdown headings, four sections, English, no emoji."
        )
        try:
            battle_plan_markdown = generate_text_from_gemini_with_system_and_user_prompts(
                fish_sniper_backend_settings=settings,
                system_instruction=system_prompt,
                user_prompt=user_prompt,
            )
        except FishSniperGeminiInvocationError:
            battle_plan_markdown = (
                "Battle plan could not be generated; use the structured fields above."
            )

        gen_cm = (
            langfuse_client.start_as_current_generation(
                name="gemini_battle_plan_summary",
                model=settings.gemini_model,
                input=f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}",
                output=battle_plan_markdown,
            )
            if langfuse_client is not None
            else nullcontext()
        )
        with gen_cm:
            pass

        return {"battle_plan_summary_markdown": battle_plan_markdown}


def node_finalize_success_response_model(
    state: FishSniperStrategyGraphState,
) -> FishSniperStrategyGraphState:
    """Build Pydantic success response."""

    if _read_terminal_http_status_from_state(state) is not None:
        return {}

    parsed = state["structured_strategy_parsed_dict"]
    generated_at_utc = datetime.now(tz=UTC)
    success = GenerateBassStrategySuccessResponseBody(
        lure_type=str(parsed["lure_type"]),
        lure_color=str(parsed["lure_color"]),
        retrieve_speed=str(parsed["retrieve_speed"]),
        target_zone=str(parsed["target_zone"]),
        time_window=str(parsed["time_window"]),
        confidence_note=str(parsed["confidence_note"]),
        battle_plan_summary=str(state.get("battle_plan_summary_markdown") or ""),
        weather_snapshot=WeatherSnapshotPayload(
            temperature_c=state["temperature_celsius"],
            pressure_hpa=state["pressure_hectopascals"],
            wind_speed_ms=state["wind_speed_meters_per_second"],
            condition_code=state["condition_code"],
        ),
        rag_logs_used=0,
        generated_at=generated_at_utc,
        fallback=False,
    )
    return {"success_response_body": success.model_dump(mode="json")}


def node_finalize_fallback_response_model(
    state: FishSniperStrategyGraphState,
) -> FishSniperStrategyGraphState:
    """Build fallback envelope after JSON validation exhausts retries."""

    if _read_terminal_http_status_from_state(state) is not None:
        return {}

    if state.get("strategy_fallback") is not True:
        return {}

    generated_at_utc = datetime.now(tz=UTC)
    fallback = GenerateBassStrategyFallbackResponseBody(
        fallback=True,
        message="Could not generate a confident strategy. Try again or adjust your input.",
        generated_at=generated_at_utc,
    )
    return {"fallback_response_body": fallback.model_dump(mode="json")}


def build_fish_sniper_strategy_state_graph() -> StateGraph:
    """Wire LangGraph nodes and conditional retry routing for Step 5–6."""

    graph_builder = StateGraph(FishSniperStrategyGraphStateSchema)
    graph_builder.add_node(
        "load_region_and_weather", node_load_user_region_and_open_weather_map_snapshot
    )
    graph_builder.add_node("rag_short_circuit_p2", node_short_circuit_personal_log_retrieval_for_p2)
    graph_builder.add_node("assemble_prompts", node_assemble_prompts_for_general_branch)
    graph_builder.add_node("structured_generation", node_invoke_gemini_for_structured_json_strategy)
    graph_builder.add_node(
        "validate_structured_json", node_parse_and_validate_structured_json_strategy
    )
    graph_builder.add_node("battle_plan_generation", node_invoke_gemini_for_battle_plan_markdown)
    graph_builder.add_node("finalize_success", node_finalize_success_response_model)
    graph_builder.add_node("finalize_fallback", node_finalize_fallback_response_model)
    graph_builder.add_node("pipeline_terminal_stop", node_no_op_pipeline_terminal_stop)

    graph_builder.set_entry_point("load_region_and_weather")
    graph_builder.add_conditional_edges(
        "load_region_and_weather",
        route_after_load_region_and_weather,
        {
            "terminal_stop": "pipeline_terminal_stop",
            "continue": "rag_short_circuit_p2",
        },
    )
    graph_builder.add_edge("rag_short_circuit_p2", "assemble_prompts")
    graph_builder.add_edge("assemble_prompts", "structured_generation")
    graph_builder.add_edge("structured_generation", "validate_structured_json")
    graph_builder.add_conditional_edges(
        "validate_structured_json",
        route_after_structured_json_validation,
        {
            "retry_structured_generation": "structured_generation",
            "battle_plan": "battle_plan_generation",
            "fallback_done": "finalize_fallback",
            "terminal_stop": "pipeline_terminal_stop",
        },
    )
    graph_builder.add_edge("battle_plan_generation", "finalize_success")
    graph_builder.add_edge("finalize_success", END)
    graph_builder.add_edge("finalize_fallback", END)
    graph_builder.add_edge("pipeline_terminal_stop", END)
    return graph_builder


_compiled_fish_sniper_strategy_graph = build_fish_sniper_strategy_state_graph().compile()


def invoke_fish_sniper_strategy_graph(
    *,
    fish_sniper_user_id: UUID,
    parsed_request_body: GenerateBassStrategyRequestBody,
    fish_sniper_backend_settings: FishSniperBackendSettings,
    persistence_port: FishSniperPersistencePort,
    weather_snapshot_cache_port: WeatherSnapshotCachePort,
    reference_time_utc: datetime,
) -> FishSniperStrategyGraphState:
    """Return the graph final state (terminal errors or success/fallback JSON bodies)."""

    langfuse_client = build_langfuse_client_or_none(
        fish_sniper_backend_settings=fish_sniper_backend_settings,
    )
    initial_state: FishSniperStrategyGraphState = {
        "fish_sniper_user_id": fish_sniper_user_id,
        "parsed_request_body": parsed_request_body,
        "fish_sniper_backend_settings": fish_sniper_backend_settings,
        "persistence_port": persistence_port,
        "weather_snapshot_cache_port": weather_snapshot_cache_port,
        "reference_time_utc": reference_time_utc,
        "langfuse_client": langfuse_client,
        "structured_json_retry_count": 0,
    }
    root_cm = (
        langfuse_client.start_as_current_span(
            name="fish_sniper_strategy_trace_root",
            metadata={"user_id": str(fish_sniper_user_id)},
        )
        if langfuse_client is not None
        else nullcontext()
    )
    try:
        with root_cm:
            final_state = _compiled_fish_sniper_strategy_graph.invoke(initial_state)
    finally:
        flush_langfuse_client_best_effort(langfuse_client=langfuse_client)

    return final_state
