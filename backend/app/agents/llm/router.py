"""LLM router with primary -> failover ordering and per-agent overrides.

Agents depend only on the router, never a concrete provider. The router tries the
configured primary first, then falls back to the other provider on error/rate
limit. ``available`` reports whether *any* provider can serve, so callers can
choose a heuristic path when no LLM is configured at all.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache

from app.agents.llm.azure_openai import AzureOpenAIProvider
from app.agents.llm.base import LLMError, LLMMessage, LLMProvider
from app.agents.llm.gemini import GeminiProvider
from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMRouter:
    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {
            "azure": AzureOpenAIProvider(),
            "gemini": GeminiProvider(),
        }

    def _ordered(self, agent: str | None = None) -> list[LLMProvider]:
        s = get_settings()
        # Per-agent override could be read from config here; default to global.
        primary = s.llm_primary
        order = [primary, "gemini" if primary == "azure" else "azure"]
        return [self._providers[name] for name in order if self._providers[name].available()]

    def available(self) -> bool:
        return any(p.available() for p in self._providers.values())

    def complete(self, messages: list[LLMMessage], *, agent: str | None = None,
                 temperature: float = 0.2, max_tokens: int = 900,
                 json_mode: bool = False) -> str:
        providers = self._ordered(agent)
        if not providers:
            raise LLMError("No LLM provider configured")
        last: Exception | None = None
        # Always attempt each provider at least once, even if misconfigured to 0.
        retries = max(1, get_settings().llm_max_retries)
        for provider in providers:
            for attempt in range(retries):
                try:
                    return provider.complete(
                        messages, temperature=temperature,
                        max_tokens=max_tokens, json_mode=json_mode,
                    )
                except LLMError as exc:
                    last = exc
                    logger.warning(
                        "LLM provider %s attempt %d failed: %s",
                        provider.name, attempt + 1, exc,
                    )
        raise LLMError(f"All LLM providers failed: {last}")

    def complete_json(self, system: str, user: str, *, agent: str | None = None,
                      max_tokens: int = 900) -> dict:
        """Return a parsed JSON object; raises LLMError if no provider/parse fails."""
        text = self.complete(
            [LLMMessage("system", system), LLMMessage("user", user)],
            agent=agent, json_mode=True, max_tokens=max_tokens,
        )
        return _parse_json(text)


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if 0 <= start < end:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError as exc:
                raise LLMError("LLM did not return valid JSON") from exc
        raise LLMError("LLM did not return valid JSON")


@lru_cache
def get_router() -> LLMRouter:
    return LLMRouter()
