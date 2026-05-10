"""Embedding subsystem port (Protocol + error taxonomy).

Decoupling routes from the concrete OpenAI SDK lets tests inject a fake
without touching the network, and lets us swap providers in the future
by replacing a single class.

Errors are split into two categories:

* `FishSniperEmbeddingUnavailableError` (transient) — route layer should
  degrade by persisting the row with `embedding_status='pending'` and
  return a 201 SUCCESS so the user is unaffected. A future background
  worker (Part 2) will re-attempt.

* `FishSniperEmbeddingMisconfiguredError` (permanent / config) — bad key,
  bad model id, or wrong vector dimension. The route layer must NOT
  catch this; letting it bubble produces a 503 plus a loud log so the
  deployment problem is discovered quickly.
"""

from __future__ import annotations

from typing import Protocol


class FishSniperEmbeddingUnavailableError(RuntimeError):
    """Transient embedding failure — caller should degrade to `pending`."""


class FishSniperEmbeddingMisconfiguredError(RuntimeError):
    """Permanent / configuration embedding failure — caller must NOT degrade."""


class FishSniperEmbeddingClient(Protocol):
    """Synchronous embedding API consumed by `/logs` POST and PATCH handlers."""

    def embed(self, *, text: str) -> list[float]:
        """Return a vector of length `openai_embedding_dimensions` for `text`."""
