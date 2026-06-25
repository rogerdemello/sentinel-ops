"""Durability: rehydrate the in-memory store from persisted rows on boot.

Uses a fake psycopg connection that replays previously-dumped rows, exercising the
full rehydrate() path (SELECT → deserialize → load) without a live database.
"""

from __future__ import annotations

from app.bootstrap import seed_topology
from app.config import get_settings
from app.db import rehydrate as rehydrate_mod
from app.db.repository import get_repository
from app.models import IncidentStatus


def _make_incident_and_prediction():
    """Open a real incident via the engine, return its persisted (json) rows."""
    seed_topology()
    from app.telemetry.simulator import get_simulator

    sim = get_simulator()
    repo = get_repository()
    sim.trigger("db_pool_exhaustion")
    inc = None
    for _ in range(80):
        sim.tick()
        op = [i for i in repo.list_incidents() if i.status != IncidentStatus.resolved]
        if op:
            inc = op[0]
            break
    assert inc is not None
    preds = repo.list_predictions()
    inc_row = inc.model_dump(mode="json")
    pred_rows = [p.model_dump(mode="json") for p in preds]
    return inc_row, pred_rows


class _FakeCursor:
    def __init__(self, inc_rows, pred_rows):
        self._inc, self._pred, self._rows = inc_rows, pred_rows, []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql):
        self._rows = self._inc if "incidents" in sql else self._pred

    def fetchall(self):
        return self._rows


class _FakeConn:
    def __init__(self, inc_rows, pred_rows):
        self._inc, self._pred = inc_rows, pred_rows

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def cursor(self):
        return _FakeCursor(self._inc, self._pred)


def test_rehydrate_loads_persisted_incident(monkeypatch):
    inc_row, pred_rows = _make_incident_and_prediction()

    # Simulate a fresh process: wipe the in-memory store, then rehydrate from "DB".
    get_repository.cache_clear()
    fresh = get_repository()
    assert fresh.list_incidents() == []

    monkeypatch.setenv("DATABASE_URL", "postgresql://fake/db")
    get_settings.cache_clear()

    import psycopg

    monkeypatch.setattr(
        psycopg, "connect", lambda *a, **k: _FakeConn([inc_row], pred_rows)
    )

    try:
        loaded = rehydrate_mod.rehydrate(fresh)
        assert loaded == 1
        assert fresh.get_incident(inc_row["id"]) is not None
        assert len(fresh.list_predictions()) == len(pred_rows)
        # The rehydrated incident is fully reconstructed (nested RCA/plan survive).
        restored = fresh.get_incident(inc_row["id"])
        assert restored.root_cause == inc_row["root_cause"]
        assert restored.plan is not None
    finally:
        get_settings.cache_clear()
