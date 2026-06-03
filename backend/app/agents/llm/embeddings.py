"""Azure OpenAI text embeddings (for RAG incident memory).

Returns None when embeddings aren't configured or a call fails, so callers can
degrade gracefully. Lazy client init.
"""

from __future__ import annotations

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        from openai import AzureOpenAI

        s = get_settings()
        _client = AzureOpenAI(
            azure_endpoint=s.azure_openai_endpoint,
            api_key=s.azure_openai_api_key,
            api_version=s.azure_openai_api_version,
        )
    return _client


def embed(text: str) -> list[float] | None:
    s = get_settings()
    if not s.embeddings_enabled:
        return None
    try:
        resp = _get_client().embeddings.create(
            model=s.azure_openai_embedding_deployment, input=text[:8000]
        )
        return resp.data[0].embedding
    except Exception as exc:  # noqa: BLE001
        logger.warning("Embedding call failed: %s", exc)
        return None
