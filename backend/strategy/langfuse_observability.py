"""Optional Langfuse client wiring (disabled when keys are missing)."""

from __future__ import annotations

from typing import Any

from langfuse import Langfuse

from settings import AppSettings


def build_langfuse_client_or_none(
    *,
    fish_sniper_backend_settings: AppSettings,
) -> Langfuse | None:
    """Return a configured Langfuse client, or None when tracing should be off."""

    public_key = fish_sniper_backend_settings.langfuse_public_key
    secret_key = fish_sniper_backend_settings.langfuse_secret_key
    if not public_key or not secret_key:
        return None
    base_url = fish_sniper_backend_settings.langfuse_base_url
    kwargs: dict[str, Any] = {
        "public_key": public_key,
        "secret_key": secret_key,
    }
    if base_url:
        kwargs["host"] = base_url.rstrip("/")
    return Langfuse(**kwargs)


def flush_langfuse_client_best_effort(*, langfuse_client: Langfuse | None) -> None:
    """Flush queued Langfuse events before process exit."""

    if langfuse_client is None:
        return
    try:
        langfuse_client.flush()
    except Exception:
        return
