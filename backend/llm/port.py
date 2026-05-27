"""Text-generation port (Protocol + error taxonomy).

Concrete vendor adapters (Gemini, OpenAI, …) implement ``LlmTextGenerationClient``.
Callers depend on this Protocol—not on SDK types—so tests can inject fakes and
providers can be swapped without touching LangGraph or routes.

Catalog / yaml errors (``UnknownModelError``, ``RegistryConfigurationError``) live
in ``llm.models``; this module covers **adapter invocation** only.

Error categories (mirror ``embedding.port``):

* ``GenerationUnavailableError`` — transient (rate limit, timeout, 5xx).
  LangGraph should map to HTTP 503 for strategy generation.

* ``GenerationMisconfiguredError`` — permanent misconfiguration (missing API
  key, invalid model id). Should not be masked as a user-retryable success path.
"""

from __future__ import annotations

from typing import Protocol

from llm.models import LlmGenerationResult


class GenerationUnavailableError(RuntimeError):
    """Transient text-generation failure (rate limit, timeout, upstream 5xx)."""


class GenerationMisconfiguredError(RuntimeError):
    """Permanent text-generation misconfiguration (bad key, model, or deployment)."""


class LlmTextGenerationClient(Protocol):
    """Async adapter contract for one provider-backed text generation call.

    Each adapter instance is typically bound to a single ``ModelConfig`` (set at
    construction). The router selects which adapter to use per ``model_id``.
    """

    async def generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> LlmGenerationResult:
        """Generate one completion's raw text from a system prompt and a user prompt (L1 layer).

        Implementations must map provider SDK failures to ``GenerationUnavailableError``
        or ``GenerationMisconfiguredError``. They must not parse fishing-strategy
        JSON; that happens upstream in ``json_payload_extraction`` and Pydantic validation.
        """
