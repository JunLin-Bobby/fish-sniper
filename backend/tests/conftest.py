"""Shared pytest fixtures for FishSniper backend tests."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from persistence.port import FishSniperUserPreferencesRow, FishSniperUserRow
from settings import get_fish_sniper_backend_settings


class InMemoryFishSniperPersistenceAdapter:
    """In-memory persistence for fast, deterministic API tests."""

    def __init__(self) -> None:
        self._otp_challenge_row_list: list[dict[str, object]] = []
        self._user_row_by_normalized_email: dict[str, FishSniperUserRow] = {}
        self._preferences_row_by_user_id: dict[UUID, FishSniperUserPreferencesRow] = {}

    def fetch_seconds_since_last_otp_send_for_email(
        self,
        *,
        normalized_email_address: str,
        reference_time_utc: datetime,
    ) -> float | None:
        matching_created_at_list: list[datetime] = []
        for otp_row in self._otp_challenge_row_list:
            if otp_row["normalized_email_address"] == normalized_email_address:
                created_at = otp_row["otp_created_at_utc"]
                assert isinstance(created_at, datetime)
                matching_created_at_list.append(created_at)
        if not matching_created_at_list:
            return None
        latest_created_at_utc = max(matching_created_at_list)
        return (reference_time_utc - latest_created_at_utc).total_seconds()

    def insert_pending_otp_challenge_for_email(
        self,
        *,
        normalized_email_address: str,
        otp_code_six_digits: str,
        otp_expires_at_utc: datetime,
        otp_created_at_utc: datetime,
    ) -> None:
        self._otp_challenge_row_list.append(
            {
                "normalized_email_address": normalized_email_address,
                "otp_code_six_digits": otp_code_six_digits,
                "otp_expires_at_utc": otp_expires_at_utc,
                "otp_created_at_utc": otp_created_at_utc,
            }
        )

    def delete_matching_unexpired_otp_or_noop(
        self,
        *,
        normalized_email_address: str,
        otp_code_six_digits: str,
        reference_time_utc: datetime,
    ) -> bool:
        for index, otp_row in enumerate(self._otp_challenge_row_list):
            expires_at = otp_row["otp_expires_at_utc"]
            if (
                otp_row["normalized_email_address"] == normalized_email_address
                and otp_row["otp_code_six_digits"] == otp_code_six_digits
                and isinstance(expires_at, datetime)
                and expires_at > reference_time_utc
            ):
                del self._otp_challenge_row_list[index]
                return True
        return False

    def fetch_user_row_by_normalized_email(
        self,
        *,
        normalized_email_address: str,
    ) -> FishSniperUserRow | None:
        return self._user_row_by_normalized_email.get(normalized_email_address)

    def insert_user_row_for_normalized_email(
        self,
        *,
        normalized_email_address: str,
    ) -> FishSniperUserRow:
        new_user_id = uuid4()
        row = FishSniperUserRow(
            fish_sniper_user_id=new_user_id,
            normalized_email_address=normalized_email_address,
        )
        self._user_row_by_normalized_email[normalized_email_address] = row
        return row

    def fetch_user_preferences_row_for_user_id(
        self,
        *,
        fish_sniper_user_id: UUID,
    ) -> FishSniperUserPreferencesRow | None:
        return self._preferences_row_by_user_id.get(fish_sniper_user_id)

    def upsert_user_preferences_region_for_user_id(
        self,
        *,
        fish_sniper_user_id: UUID,
        profile_region_display_name: str,
        profile_onboarding_completed_flag: bool,
        preferences_updated_at_utc: datetime,
    ) -> None:
        _ = preferences_updated_at_utc
        self._preferences_row_by_user_id[fish_sniper_user_id] = FishSniperUserPreferencesRow(
            profile_region_display_name=profile_region_display_name,
            profile_onboarding_completed_flag=profile_onboarding_completed_flag,
        )


class RecordingTransactionalEmailSenderAdapter:
    """Captures OTP email sends for assertions."""

    def __init__(self) -> None:
        self.recipient_and_otp_tuple_list: list[tuple[str, str]] = []

    def send_fish_sniper_email_otp_message(
        self,
        *,
        recipient_email_address: str,
        otp_code_six_digits: str,
    ) -> None:
        self.recipient_and_otp_tuple_list.append((recipient_email_address, otp_code_six_digits))


class ExplodingTransactionalEmailSenderAdapter:
    """Always fails email delivery."""

    def send_fish_sniper_email_otp_message(
        self,
        *,
        recipient_email_address: str,
        otp_code_six_digits: str,
    ) -> None:
        _ = (recipient_email_address, otp_code_six_digits)
        raise RuntimeError("simulated email delivery failure")


@pytest.fixture
def frozen_clock() -> tuple[Callable[[], datetime], Callable[[float], None]]:
    """Controllable UTC clock for OTP cooldown tests."""

    current = datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC)

    def now_utc() -> datetime:
        return current

    def advance_seconds(seconds: float) -> None:
        nonlocal current
        current = current + timedelta(seconds=seconds)

    return now_utc, advance_seconds


@pytest.fixture
def in_memory_persistence_adapter() -> InMemoryFishSniperPersistenceAdapter:
    return InMemoryFishSniperPersistenceAdapter()


@pytest.fixture
def recording_email_sender_adapter() -> RecordingTransactionalEmailSenderAdapter:
    return RecordingTransactionalEmailSenderAdapter()


@pytest.fixture
def exploding_email_sender_adapter() -> ExplodingTransactionalEmailSenderAdapter:
    return ExplodingTransactionalEmailSenderAdapter()


@pytest.fixture(autouse=True)
def reset_fish_sniper_backend_settings_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stabilize JWT settings and avoid leaking lru_cache between tests."""

    monkeypatch.setenv("JWT_SECRET", "unit-test-jwt-secret")
    monkeypatch.setenv("SKIP_AUTH", "false")
    get_fish_sniper_backend_settings.cache_clear()
    yield
    get_fish_sniper_backend_settings.cache_clear()
