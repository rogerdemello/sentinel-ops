"""Tenant isolation + boot rehydration tests."""

from __future__ import annotations

from types import SimpleNamespace

from app.api.deps import tenant_repo
from app.bootstrap import seed_topology
from app.db.rehydrate import incident_from_row, rehydrate
from app.db.repository import get_repository
from app.models import IncidentStatus


def _open_incident(sim, repo, max_ticks=80):
    for _ in range(max_ticks):
        sim.tick()
        open_incs = [i for i in repo.list_incidents() if i.status != IncidentStatus.resolved]
        if open_incs:
            return open_incs[0]
    return None


def test_no_arg_and_default_resolve_to_same_store():
    assert get_repository() is get_repository("default")
    assert get_repository() is get_repository(None)


def test_tenants_are_isolated():
    seed_topology()
    from app.telemetry.simulator import get_simulator

    sim = get_simulator()
    default_repo = get_repository()
    sim.trigger("db_pool_exhaustion")
    inc = _open_incident(sim, default_repo)
    assert inc is not None

    other = get_repository("acme")
    assert other is not default_repo
    # The other tenant must NOT see the default tenant's incident.
    assert other.get_incident(inc.id) is None
    assert other.list_incidents() == []


def test_tenant_repo_dependency_seeds_topology_but_isolates_data():
    seed_topology()
    from app.telemetry.simulator import get_simulator

    sim = get_simulator()
    default_repo = get_repository()
    sim.trigger("memory_leak")
    inc = _open_incident(sim, default_repo)
    assert inc is not None

    req = SimpleNamespace(state=SimpleNamespace(tenant_id="acme"))
    repo = tenant_repo(req)  # type: ignore[arg-type]
    # Fresh tenant gets the shared service catalog so its dashboard renders...
    assert len(repo.list_services()) == len(default_repo.list_services())
    # ...but none of the default tenant's incidents.
    assert repo.list_incidents() == []


def test_rehydrate_is_noop_when_db_disabled():
    # conftest neutralizes DATABASE_URL, so persistence is disabled.
    assert rehydrate() == 0


def test_incident_row_roundtrip_deserializes():
    seed_topology()
    from app.telemetry.simulator import get_simulator

    sim = get_simulator()
    repo = get_repository()
    sim.trigger("db_pool_exhaustion")
    inc = _open_incident(sim, repo)
    assert inc is not None

    # Simulate the DB round-trip: model_dump(json) is what the writer persists, and
    # a jsonb read returns the same shape back.
    row = inc.model_dump(mode="json")
    restored = incident_from_row(row)
    assert restored.id == inc.id
    assert restored.service_id == inc.service_id
    assert restored.root_cause == inc.root_cause
    assert len(restored.findings) == len(inc.findings)
    assert restored.plan is not None and inc.plan is not None
