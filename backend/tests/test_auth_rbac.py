"""Security tests: RBAC gate, identity-bound roles, and WebSocket auth.

These lock in the P0 fix — a client must not be able to escalate privileges by
sending its own role header, and the live stream must not be world-readable when
an API key is configured.
"""

from __future__ import annotations

import inspect

import pytest

from app.config import get_settings
from app.models import IncidentStatus


def _open_incident(sim, repo, max_ticks=80):
    from app.models import IncidentStatus as _S

    for _ in range(max_ticks):
        sim.tick()
        open_incs = [i for i in repo.list_incidents() if i.status != _S.resolved]
        if open_incs:
            return open_incs[0]
    return None


def test_approve_route_does_not_trust_a_role_header():
    """Regression guard: the approve endpoint must derive role from auth, not a
    client-supplied parameter/header."""
    from app.api.routes import remediation

    params = inspect.signature(remediation.approve).parameters
    assert "x_role" not in params, "approve must not accept a client role header"
    # It should take the Request (so it can read the middleware-assigned role).
    assert "request" in params


def test_rbac_gate_denies_unlisted_role(monkeypatch):
    monkeypatch.setenv("RBAC_ENABLED", "true")
    get_settings.cache_clear()
    try:
        from app.bootstrap import seed_topology
        from app.clock import get_clock
        from app.db.repository import get_repository
        from app.remediation import workflow
        from app.telemetry.simulator import get_simulator

        seed_topology()
        sim = get_simulator()
        repo = get_repository()
        sim.trigger("db_pool_exhaustion")
        incident = _open_incident(sim, repo)
        assert incident is not None

        # A non-allowed role (e.g. an unauthenticated "viewer") must be rejected...
        with pytest.raises(workflow.WorkflowError):
            workflow.approve_and_execute(
                incident.id, get_clock().now(), actor="human", role="viewer"
            )
        # ...while a legitimate operator succeeds.
        resolved = workflow.approve_and_execute(
            incident.id, get_clock().now(), actor="human", role="operator"
        )
        assert resolved.status == IncidentStatus.resolved
    finally:
        get_settings.cache_clear()


def test_ws_stream_requires_token_when_api_key_set(monkeypatch):
    from starlette.websockets import WebSocketDisconnect

    monkeypatch.setenv("API_KEY", "s3cret")
    get_settings.cache_clear()
    try:
        from fastapi.testclient import TestClient

        from app.main import create_app

        client = TestClient(create_app())

        # No token → server rejects the handshake (policy violation close).
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/stream") as ws:
                ws.receive_json()

        # Correct token → snapshot streams.
        with client.websocket_connect("/ws/stream?token=s3cret") as ws:
            data = ws.receive_json()
            assert "sim_time" in data
    finally:
        get_settings.cache_clear()


def test_ws_stream_open_when_no_api_key(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    get_settings.cache_clear()
    try:
        from fastapi.testclient import TestClient

        from app.main import create_app

        client = TestClient(create_app())
        with client.websocket_connect("/ws/stream") as ws:
            data = ws.receive_json()
            assert "active_incidents" in data
    finally:
        get_settings.cache_clear()
