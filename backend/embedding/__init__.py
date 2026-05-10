"""Embedding subsystem (P4 Part 1).

Splits two responsibilities:

* `fish_sniper_log_embedding_text` — pure, deterministic text composer.
* `openai_embedding_client` (Task 2) — calls the OpenAI Embeddings API.
* `port` (Task 2) — Protocol + error types decoupling routes from the OpenAI SDK.

Embedding writes and queries both use OpenAI; the LLM stack (Gemini) is independent.
"""
