"""Tests for the deterministic embedding-text composer (P4 Part 1, Task 3)."""

from __future__ import annotations

import pytest

from embedding.fish_sniper_log_embedding_text import (
    EMBEDDING_TEXT_VERSION,
    MAX_EMBEDDING_NOTES_CHARS,
    compose_fishing_log_embedding_text,
)


def _all_required_kwargs() -> dict:
    """Baseline kwargs used by tests; tests override individual fields as needed."""

    return dict(
        fishing_location="Charles River",
        fishing_scene="river",
        target_species="Largemouth Bass",
        water_depth_m=3.0,
        lure_type="Soft plastic swimbait",
        lure_color="Green pumpkin",
        retrieve_speed="Slow",
        caught_count=2,
        weight_lb=3.09,
        length_cm=38.0,
        temperature_c=18.5,
        wind_speed_ms=2.1,
        pressure_hpa=1008,
        condition_code="cloudy",
        notes="Best action near the bridge pillars at 6am",
    )


def test_template_version_constant_is_one() -> None:
    """Part 1 ships embedding text version 1; bumping the template requires bumping this."""

    assert EMBEDDING_TEXT_VERSION == 1


def test_compose_includes_every_field_in_fixed_order() -> None:
    """Composer emits each field in a stable, parseable order."""

    text = compose_fishing_log_embedding_text(**_all_required_kwargs())

    expected_substrings_in_order = [
        "FishSniper fishing log.",
        "Location: Charles River.",
        "Scene: river.",
        "Target species: Largemouth Bass.",
        "Depth meters: 3.0.",
        "Lure: Soft plastic swimbait / Green pumpkin.",
        "Retrieve: Slow.",
        "Catch: count 2",
        "weight_lb 3.09",
        "length_cm 38.0",
        "Weather: temp_c 18.5",
        "wind_ms 2.1",
        "pressure_hpa 1008",
        "condition cloudy",
        "Notes: Best action near the bridge pillars at 6am",
    ]

    last_index = -1
    for substring in expected_substrings_in_order:
        index = text.find(substring)
        assert index != -1, f"Missing substring: {substring!r} in:\n{text}"
        assert index > last_index, (
            f"Substring {substring!r} appeared out of order in:\n{text}"
        )
        last_index = index


def test_compose_emits_n_a_for_null_weight_and_length() -> None:
    """Null optional numerics serialize as the literal string `n/a`."""

    kwargs = _all_required_kwargs()
    kwargs["weight_lb"] = None
    kwargs["length_cm"] = None

    text = compose_fishing_log_embedding_text(**kwargs)

    assert "weight_lb n/a" in text
    assert "length_cm n/a" in text


def test_compose_truncates_long_notes_with_marker() -> None:
    """Notes longer than MAX_EMBEDDING_NOTES_CHARS are truncated and marked."""

    kwargs = _all_required_kwargs()
    long_notes = "x" * (MAX_EMBEDDING_NOTES_CHARS + 500)
    kwargs["notes"] = long_notes

    text = compose_fishing_log_embedding_text(**kwargs)

    assert "(truncated)" in text
    notes_segment_start = text.index("Notes: ") + len("Notes: ")
    notes_segment = text[notes_segment_start:].rstrip().rstrip(".")
    assert len(notes_segment) <= MAX_EMBEDDING_NOTES_CHARS + len("…(truncated)")
    assert "x" * 100 in notes_segment


def test_compose_is_deterministic_for_identical_inputs() -> None:
    """Two invocations with the same inputs produce byte-identical text."""

    kwargs = _all_required_kwargs()
    first = compose_fishing_log_embedding_text(**kwargs)
    second = compose_fishing_log_embedding_text(**kwargs)
    assert first == second


def test_compose_includes_smallmouth_target_species_verbatim() -> None:
    """Target species string is passed through unchanged (case-sensitive)."""

    kwargs = _all_required_kwargs()
    kwargs["target_species"] = "Smallmouth Bass"

    text = compose_fishing_log_embedding_text(**kwargs)

    assert "Target species: Smallmouth Bass." in text


def test_compose_handles_empty_notes_without_truncation_marker() -> None:
    """Empty notes (P3 schema default) round-trips cleanly without truncation."""

    kwargs = _all_required_kwargs()
    kwargs["notes"] = ""

    text = compose_fishing_log_embedding_text(**kwargs)

    assert "(truncated)" not in text
    assert "Notes: ." in text or "Notes:  " in text or text.rstrip().endswith("Notes:")


@pytest.mark.parametrize(
    "field",
    [
        "fishing_location",
        "fishing_scene",
        "lure_type",
        "lure_color",
        "retrieve_speed",
        "condition_code",
    ],
)
def test_compose_passes_string_fields_through_verbatim(field: str) -> None:
    """String fields are not stripped, lowercased, or otherwise normalized."""

    sentinel = "ZZ_DETECT_PASSTHROUGH_ZZ"
    kwargs = _all_required_kwargs()
    kwargs[field] = sentinel

    text = compose_fishing_log_embedding_text(**kwargs)

    assert sentinel in text
