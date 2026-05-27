"""Gemini text-generation adapter (google-genai async)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from llm.models import LlmGenerationResult, ModelConfig
from llm.port import GenerationMisconfiguredError, GenerationUnavailableError

logger = logging.getLogger(__name__)

_TRANSIENT_GEMINI_HTTP_CODES: frozenset[int] = frozenset({408, 429, 500, 502, 503, 504})
_PERMANENT_GEMINI_HTTP_CODES: frozenset[int] = frozenset({400, 401, 403, 404})


def _default_genai_client_factory(**kwargs: Any) -> genai.Client:
    return genai.Client(**kwargs)


def _text_from_generate_content_response(response: object) -> str:
    return (getattr(response, "text", None) or "").strip()


class GeminiTextAdapter:
    """Async Gemini ``generate_content`` adapter bound to one ``ModelConfig``."""

    def __init__(
        self,
        *,
        model_config: ModelConfig,
        api_key: str,
        genai_client_factory: Callable[..., Any] = _default_genai_client_factory,
    ) -> None:
        self._model_config = model_config
        self._sdk_client = genai_client_factory(api_key=api_key)

    async def generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> LlmGenerationResult:
        model_id = self._model_config.provider_model
        try:
            response = await asyncio.wait_for(
                self._sdk_client.aio.models.generate_content(
                    model=model_id,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=self._model_config.temperature,
                    ),
                ),
                timeout=self._model_config.timeout_seconds,
            )
        except TimeoutError as exc:
            logger.warning(
                "gemini_text_generation_timeout model=%s timeout=%ss",
                model_id,
                self._model_config.timeout_seconds,
            )
            raise GenerationUnavailableError(
                f"Gemini request timed out after {self._model_config.timeout_seconds}s",
            ) from exc
        except genai_errors.APIError as exc:
            self._raise_mapped_gemini_error(exc=exc, model_id=model_id)

        raw_text = _text_from_generate_content_response(response)
        if not raw_text:
            logger.warning("gemini_text_generation_empty model=%s", model_id)
            raise GenerationUnavailableError("Gemini returned empty text")

        return LlmGenerationResult(
            raw_text=raw_text,
            provider="gemini",
            model_id=self._model_config.model_id,
            provider_model=model_id,
            temperature=self._model_config.temperature,
        )

    def _raise_mapped_gemini_error(self, *, exc: genai_errors.APIError, model_id: str) -> None:
        code = getattr(exc, "code", None)
        if code in _PERMANENT_GEMINI_HTTP_CODES:
            logger.error(
                "gemini_text_generation_misconfigured model=%s code=%s",
                model_id,
                code,
            )
            raise GenerationMisconfiguredError(
                f"Gemini permanent error code={code}: {type(exc).__name__}",
            ) from exc
        if code in _TRANSIENT_GEMINI_HTTP_CODES:
            logger.warning(
                "gemini_text_generation_unavailable model=%s code=%s",
                model_id,
                code,
            )
            raise GenerationUnavailableError(
                f"Gemini transient error code={code}: {type(exc).__name__}",
            ) from exc
        logger.warning(
            "gemini_text_generation_unavailable model=%s code=%s",
            model_id,
            code,
        )
        raise GenerationUnavailableError(
            f"Gemini API request failed: {type(exc).__name__}",
        ) from exc
