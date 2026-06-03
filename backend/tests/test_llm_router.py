import pytest

from app.agents.llm.base import LLMError, LLMMessage, LLMProvider
from app.agents.llm.router import LLMRouter, _parse_json


class _FakeProvider(LLMProvider):
    def __init__(self, name, ok=True, avail=True):
        self.name = name
        self._ok = ok
        self._avail = avail
        self.calls = 0

    def available(self):
        return self._avail

    def complete(self, messages, *, temperature=0.2, max_tokens=900, json_mode=False):
        self.calls += 1
        if not self._ok:
            raise LLMError(f"{self.name} boom")
        return f"reply-from-{self.name}"


def test_no_provider_available_reports_unavailable():
    r = LLMRouter()
    r._providers = {"azure": _FakeProvider("azure", avail=False),
                    "gemini": _FakeProvider("gemini", avail=False)}
    assert r.available() is False
    with pytest.raises(LLMError):
        r.complete([LLMMessage("user", "hi")])


def test_failover_from_primary_to_secondary(monkeypatch):
    from app.config import get_settings
    get_settings.cache_clear()

    r = LLMRouter()
    azure = _FakeProvider("azure", ok=False)  # primary fails
    gemini = _FakeProvider("gemini", ok=True)  # failover succeeds
    r._providers = {"azure": azure, "gemini": gemini}

    out = r.complete([LLMMessage("user", "hi")])
    assert out == "reply-from-gemini"
    assert azure.calls >= 1  # primary attempted (with retries) before failover
    assert gemini.calls == 1


def test_parse_json_handles_fenced_and_noisy_output():
    assert _parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert _parse_json('noise before {"b": 2} noise after') == {"b": 2}
