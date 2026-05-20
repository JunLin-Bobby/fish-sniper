"""Gemini text generation wrapper (google-genai)."""

from __future__ import annotations

import logging

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from settings import FishSniperBackendSettings

logger = logging.getLogger(__name__)


class FishSniperGeminiInvocationError(RuntimeError):
    """Raised when Gemini returns no usable text."""


def _concatenate_text_from_generate_content_response(response: object) -> str:
    text = (getattr(response, "text", None) or "").strip()
    return text


def generate_text_from_gemini_with_system_and_user_prompts(
    *,
    fish_sniper_backend_settings: FishSniperBackendSettings,
    system_instruction: str,
    user_prompt: str,
) -> str:
    """Call Gemini `generate_content` and return concatenated text parts."""

    api_key = fish_sniper_backend_settings.gemini_api_key
    if not api_key:
        raise FishSniperGeminiInvocationError("GEMINI_API_KEY is not configured")

    client = genai.Client(api_key=api_key)
    model_id = fish_sniper_backend_settings.gemini_model
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
            ),
        )
    except genai_errors.APIError as exc:
        logger.warning("Gemini generate_content failed model=%s: %s", model_id, exc)
        raise FishSniperGeminiInvocationError(
            "Gemini API request failed (rate limit, overload, or upstream error)"
        ) from exc
    text = _concatenate_text_from_generate_content_response(response)
    if not text:
        logger.warning("Gemini returned empty text for model=%s", model_id)
        raise FishSniperGeminiInvocationError("Gemini returned empty text")
    return text


async def agenerate_text_from_gemini_with_system_and_user_prompts(
    *,
    fish_sniper_backend_settings: FishSniperBackendSettings,
    system_instruction: str,
    user_prompt: str,
) -> str:
    """Async Gemini `generate_content` via ``Client.aio.models`` (google-genai ≥ 1.38)."""

    api_key = fish_sniper_backend_settings.gemini_api_key
    if not api_key:
        raise FishSniperGeminiInvocationError("GEMINI_API_KEY is not configured")

    client = genai.Client(api_key=api_key)
    model_id = fish_sniper_backend_settings.gemini_model
    try:
        response = await client.aio.models.generate_content(
            model=model_id,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.4,
            ),
        )
    except genai_errors.APIError as exc:
        logger.warning("Gemini async generate_content failed model=%s: %s", model_id, exc)
        raise FishSniperGeminiInvocationError(
            "Gemini API request failed (rate limit, overload, or upstream error)"
        ) from exc
    text = _concatenate_text_from_generate_content_response(response)
    if not text:
        logger.warning("Gemini returned empty text for model=%s", model_id)
        raise FishSniperGeminiInvocationError("Gemini returned empty text")
    return text
