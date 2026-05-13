"""Query-side natural language for RAG similarity search (P4 Part 2).

The first five lines plus the ``Weather:`` line must stay byte-identical to the
corresponding segments emitted by ``compose_fishing_log_embedding_text`` so
Gemini embeddings for query and document share the same prefix semantics.
Outcome fields (lure, catch, notes) are intentionally omitted.
"""

from __future__ import annotations

from embedding.fish_sniper_log_embedding_text import EMBEDDING_TEXT_VERSION

__all__ = ["EMBEDDING_TEXT_VERSION", "compose_fishing_log_query_embedding_text"]


def compose_fishing_log_query_embedding_text(
    *,
    fishing_location: str,
    fishing_scene: str,
    target_species: str,
    water_depth_m: float,
    temperature_c: float,
    wind_speed_ms: float,
    pressure_hpa: int,
    condition_code: str,
) -> str:
    """Render the short RETRIEVAL_QUERY text for strategy-time vector search."""

    return (
        "FishSniper fishing log.\n"
        f"Location: {fishing_location}.\n"
        f"Scene: {fishing_scene}.\n"
        f"Target species: {target_species}.\n"
        f"Depth meters: {repr(water_depth_m)}.\n"
        "Weather: "
        f"temp_c {repr(temperature_c)}, wind_ms {repr(wind_speed_ms)}, "
        f"pressure_hpa {pressure_hpa}, condition {condition_code}."
    )
