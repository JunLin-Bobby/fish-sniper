"""Embedding subsystem (P4 Part 1).

Splits two responsibilities:

* ``fish_sniper_log_embedding_text`` — pure, deterministic text composer.
* ``gemini_embedding_client`` (Task 2) — calls Google Gemini's ``embed_content`` API.
* ``port`` (Task 2) — Protocol + error types decoupling routes from any vendor SDK.

Embedding writes and queries both go through Gemini's ``gemini-embedding-001`` model
(same ``GEMINI_API_KEY`` as the chat/strategy LLM stack — single Google provider for
the whole project after the 2026-05-10 pivot). ``output_dimensionality`` is requested
via Matryoshka so the returned vector matches ``fishing_logs.embedding`` (vector(1536)).
"""
