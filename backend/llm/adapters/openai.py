"""OpenAI Chat Completions text-generation adapter."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)

from llm.models import LlmGenerationResult, ModelConfig
from llm.port import GenerationMisconfiguredError, GenerationUnavailableError

logger = logging.getLogger(__name__)

_PERMANENT_OPENAI_HTTP_CODES: frozenset[int] = frozenset({400, 401, 403, 404})


def _default_openai_client_factory(*, api_key: str, timeout: float) -> AsyncOpenAI:
    return AsyncOpenAI(api_key=api_key, timeout=timeout)


class OpenAITextAdapter:
    """Async OpenAI chat completions adapter bound to one ``ModelConfig``."""

    def __init__(
        self,
        *,
        model_config: ModelConfig,
        api_key: str,
        openai_client_factory: Callable[..., Any] = _default_openai_client_factory,
    ) -> None:
        self._model_config = model_config
        self._client = openai_client_factory(
            api_key=api_key,
            timeout=model_config.timeout_seconds,
        )

    async def generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> LlmGenerationResult:
        model_id = self._model_config.provider_model
        try:
            response = await self._client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self._model_config.temperature,
            )
        except AuthenticationError as exc:
            logger.error("openai_text_generation_auth_failed model=%s", model_id)
            raise GenerationMisconfiguredError(
                f"OpenAI authentication failed for model={model_id!r}",
            ) from exc
        except (RateLimitError, APITimeoutError, APIConnectionError) as exc:
            logger.warning(
                "openai_text_generation_unavailable model=%s error=%s",
                model_id,
                type(exc).__name__,
            )
            raise GenerationUnavailableError(
                f"OpenAI transient error: {type(exc).__name__}",
            ) from exc
        except APIStatusError as exc:
            self._raise_mapped_openai_status_error(exc=exc, model_id=model_id)

        choices = response.choices or []
        message_content = choices[0].message.content if choices else None
        raw_text = (message_content or "").strip()
        if not raw_text:
            logger.warning("openai_text_generation_empty model=%s", model_id)
            raise GenerationUnavailableError("OpenAI returned empty text")

        return LlmGenerationResult(
            raw_text=raw_text,
            provider="openai",
            model_id=self._model_config.model_id,
            provider_model=model_id,
            temperature=self._model_config.temperature,
        )

    def _raise_mapped_openai_status_error(
        self,
        *,
        exc: APIStatusError,
        model_id: str,
    ) -> None:
        status_code = exc.status_code
        if status_code in _PERMANENT_OPENAI_HTTP_CODES:
            logger.error(
                "openai_text_generation_misconfigured model=%s status=%s",
                model_id,
                status_code,
            )
            raise GenerationMisconfiguredError(
                f"OpenAI permanent error status={status_code}: {type(exc).__name__}",
            ) from exc
        logger.warning(
            "openai_text_generation_unavailable model=%s status=%s",
            model_id,
            status_code,
        )
        raise GenerationUnavailableError(
            f"OpenAI upstream error status={status_code}: {type(exc).__name__}",
        ) from exc
