"""LLM provider contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class LLMError(Exception):
    """Raised when a provider call fails (triggers router failover)."""


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def available(self) -> bool:
        """Whether this provider is configured and usable."""

    @abstractmethod
    def complete(self, messages: list[LLMMessage], *, temperature: float = 0.2,
                 max_tokens: int = 900, json_mode: bool = False) -> str:
        """Return the model's text completion. Raise LLMError on failure."""
