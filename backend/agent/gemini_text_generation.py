"""Gemini text generation wrapper (google-genai)."""

from __future__ import annotations

import logging

from google import genai
from google.genai import types

from settings import FishSniperBackendSettings

logger = logging.getLogger(__name__)


class FishSniperGeminiInvocationError(RuntimeError):
    """Raised when Gemini returns no usable text."""


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
    response = client.models.generate_content(
        model=model_id,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.4,
        ),
    )
    text = (response.text or "").strip()
    if not text:
        logger.warning("Gemini returned empty text for model=%s", model_id)
        raise FishSniperGeminiInvocationError("Gemini returned empty text")
    return text
