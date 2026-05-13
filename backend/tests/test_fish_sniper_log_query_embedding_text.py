"""Tests for the RAG query-side embedding text composer (P4 Part 2)."""

from __future__ import annotations

from embedding.fish_sniper_log_embedding_text import compose_fishing_log_embedding_text
from embedding.fish_sniper_log_query_embedding_text import compose_fishing_log_query_embedding_text


def _shared_env_kwargs() -> dict:
    return dict(
        fishing_location="Charles River",
        fishing_scene="river",
        target_species="Largemouth Bass",
        water_depth_m=3.0,
        temperature_c=18.5,
        wind_speed_ms=2.1,
        pressure_hpa=1008,
        condition_code="cloudy",
    )


def test_query_text_first_six_segments_match_document_prefix_and_weather_line() -> None:
    """Query omits lure/catch/notes but must mirror document lines 0–4 and the weather line."""

    doc = compose_fishing_log_embedding_text(
        **_shared_env_kwargs(),
        lure_type="Soft plastic swimbait",
        lure_color="Green pumpkin",
        retrieve_speed="Slow",
        caught_count=2,
        weight_lb=3.09,
        length_cm=38.0,
        notes="Best action near the bridge pillars at 6am",
    )
    doc_lines = doc.splitlines()
    assert len(doc_lines) >= 8
    expected = doc_lines[0:5] + [doc_lines[7]]

    query = compose_fishing_log_query_embedding_text(**_shared_env_kwargs())
    assert query.splitlines() == expected


def test_query_text_omits_outcome_field_labels() -> None:
    """Do not leak lure/catch/weight/length/notes labels into the query string."""

    text = compose_fishing_log_query_embedding_text(**_shared_env_kwargs())
    for forbidden in ("Lure:", "Retrieve:", "Catch:", "Weight:", "Length:", "Notes:"):
        assert forbidden not in text


def test_query_text_is_shorter_than_full_document_for_same_env_fields() -> None:
    doc = compose_fishing_log_embedding_text(
        **_shared_env_kwargs(),
        lure_type="Jig",
        lure_color="Black",
        retrieve_speed="Fast",
        caught_count=0,
        weight_lb=None,
        length_cm=None,
        notes="",
    )
    query = compose_fishing_log_query_embedding_text(**_shared_env_kwargs())
    assert len(query) < len(doc)
