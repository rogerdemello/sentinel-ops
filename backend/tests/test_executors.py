"""Remediation executor tests (webhook + simulated)."""

from __future__ import annotations

from app.config import get_settings
from app.models import RemediationAction, Severity
from app.remediation.executor import SimulatedExecutor, WebhookExecutor


def test_simulated_executor_is_safe():
    action = RemediationAction(
        kind="restart", target_service_id="orders_db", description="restart pods", risk=Severity.low
    )
    res = SimulatedExecutor().execute(action)
    assert res.status == "simulated"
    assert "no real infra" in res.detail


def test_webhook_executor_posts_action(monkeypatch):
    monkeypatch.setenv("REMEDIATION_WEBHOOK_URL", "http://runbook.local/execute")
    get_settings.cache_clear()
    try:
        import httpx

        captured: dict = {}

        class _FakeResp:
            is_success = True
            status_code = 202

        def _fake_post(url, json=None, timeout=None):
            captured["url"] = url
            captured["json"] = json
            return _FakeResp()

        monkeypatch.setattr(httpx, "post", _fake_post)

        action = RemediationAction(
            kind="scale", target_service_id="gateway", description="scale out", risk=Severity.low
        )
        res = WebhookExecutor().execute(action)

        assert res.status == "ok"
        assert "202" in res.detail
        assert captured["url"] == "http://runbook.local/execute"
        assert captured["json"]["kind"] == "scale"
        assert captured["json"]["target_service_id"] == "gateway"
    finally:
        get_settings.cache_clear()


def test_webhook_executor_without_url_fails_cleanly(monkeypatch):
    monkeypatch.delenv("REMEDIATION_WEBHOOK_URL", raising=False)
    get_settings.cache_clear()
    try:
        action = RemediationAction(
            kind="restart", target_service_id="auth", description="x", risk=Severity.low
        )
        res = WebhookExecutor().execute(action)
        assert res.status == "failed"
        assert "not configured" in res.detail
    finally:
        get_settings.cache_clear()
