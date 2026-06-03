"""Azure OpenAI provider (primary)."""

from __future__ import annotations

import logging

from app.agents.llm.base import LLMError, LLMMessage, LLMProvider
from app.config import get_settings

logger = logging.getLogger(__name__)


class AzureOpenAIProvider(LLMProvider):
    name = "azure"

    def __init__(self) -> None:
        self._client = None

    def available(self) -> bool:
        return get_settings().azure_enabled

    def _get_client(self):
        if self._client is None:
            from openai import AzureOpenAI

            s = get_settings()
            self._client = AzureOpenAI(
                azure_endpoint=s.azure_openai_endpoint,
                api_key=s.azure_openai_api_key,
                api_version=s.azure_openai_api_version,
            )
        return self._client

    def complete(self, messages: list[LLMMessage], *, temperature: float = 0.2,
                 max_tokens: int = 900, json_mode: bool = False) -> str:
        if not self.available():
            raise LLMError("Azure OpenAI not configured")
        try:
            client = self._get_client()
            kwargs = {
                "model": get_settings().azure_openai_deployment,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Azure OpenAI call failed: {exc}") from exc
