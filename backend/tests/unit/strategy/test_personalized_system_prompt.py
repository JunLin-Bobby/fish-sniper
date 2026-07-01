"""Tests for personalized bass strategy prompts (P4 Part 2)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

from persistence.port import FishSniperFishingLogRow
from strategy.prompt_assembler import (
    build_general_system_prompt,
    build_personalized_system_prompt,
    build_user_prompt,
)


def _sample_reference_row() -> FishSniperFishingLogRow:
    now = datetime(2026, 4, 15, 8, 0, 0, tzinfo=UTC)
    return FishSniperFishingLogRow(
        log_id=uuid4(),
        fish_sniper_user_id=uuid4(),
        log_date=date(2026, 4, 15),
        fishing_location="Charles River — upstream flat",
        fishing_scene="river",
        target_species="Largemouth Bass",
        water_depth_m=1.8,
        lure_type="Jig",
        lure_color="Green Pumpkin",
        retrieve_speed="Slow drag",
        caught_count=3,
        weight_lb=None,
        length_cm=None,
        temperature_c=17.0,
        wind_speed_ms=2.5,
        pressure_hpa=1012,
        condition_code="cloudy",
        notes="Hits on the pause.",
        embedding_status="done",
        embedding_text_version=1,
        embedding_attempt_count=0,
        created_at_utc=now,
        updated_at_utc=now,
    )


def test_personalized_system_prompt_contains_reference_block_and_fields() -> None:
    row = _sample_reference_row()
    text = build_personalized_system_prompt(
        target_species="Largemouth Bass",
        reference_log=row,
    )
    assert "PERSONAL REFERENCE LOG:" in text
    assert "Use this past trip as the primary reference" in text
    assert "2026-04-15" in text
    assert row.fishing_location in text
    assert "Jig" in text and "Green Pumpkin" in text
    assert "Slow drag" in text
    assert "caught 3 fish" in text
    assert "Hits on the pause." in text


def test_general_system_prompt_unchanged() -> None:
    prompt_text = build_general_system_prompt(
        target_species="Largemouth Bass",
    )
    assert "no past records" in prompt_text


def test_shared_user_prompt_default_matches_non_personalized_confidence_instruction() -> None:
    base = build_user_prompt(
        region="Boston",
        fishing_location="Charles",
        fishing_scene="river",
        water_depth_m=2.0,
        temperature_c=18.0,
        pressure_hpa=1010,
        wind_speed_ms=3.0,
        condition_code="cloudy",
        target_species="Largemouth Bass",
    )
    explicit = build_user_prompt(
        region="Boston",
        fishing_location="Charles",
        fishing_scene="river",
        water_depth_m=2.0,
        temperature_c=18.0,
        pressure_hpa=1010,
        wind_speed_ms=3.0,
        condition_code="cloudy",
        target_species="Largemouth Bass",
        personalized=False,
    )
    assert base == explicit
    assert "no past trips on file" in base


def test_shared_user_prompt_personalized_branch_mentions_reference_trip() -> None:
    text = build_user_prompt(
        region="Boston",
        fishing_location="Charles",
        fishing_scene="river",
        water_depth_m=2.0,
        temperature_c=18.0,
        pressure_hpa=1010,
        wind_speed_ms=3.0,
        condition_code="cloudy",
        target_species="Largemouth Bass",
        personalized=True,
    )
    assert "no past trips on file" not in text
    assert "reference past trip" in text.lower()
