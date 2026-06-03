"""Google Gemini provider (failover)."""

from __future__ import annotations

import logging

from app.agents.llm.base import LLMError, LLMMessage, LLMProvider
from app.config import get_settings

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self) -> None:
        self._configured = False

    def available(self) -> bool:
        return get_settings().gemini_enabled

    def _ensure_configured(self):
        import google.generativeai as genai

        if not self._configured:
            genai.configure(api_key=get_settings().gemini_api_key)
            self._configured = True
        return genai

    def complete(self, messages: list[LLMMessage], *, temperature: float = 0.2,
                 max_tokens: int = 900, json_mode: bool = False) -> str:
        if not self.available():
            raise LLMError("Gemini not configured")
        try:
            genai = self._ensure_configured()
            # Gemini has no separate system role; fold system text into the prompt.
            system = "\n".join(m.content for m in messages if m.role == "system")
            convo = "\n\n".join(
                f"{m.role.upper()}: {m.content}" for m in messages if m.role != "system"
            )
            prompt = (system + "\n\n" + convo).strip()
            if json_mode:
                prompt += "\n\nRespond with a single valid JSON object and nothing else."
            gen_cfg = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
            if json_mode:
                gen_cfg["response_mime_type"] = "application/json"
            model = genai.GenerativeModel(
                get_settings().gemini_model, generation_config=gen_cfg
            )
            resp = model.generate_content(prompt)
            return resp.text or ""
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Gemini call failed: {exc}") from exc
