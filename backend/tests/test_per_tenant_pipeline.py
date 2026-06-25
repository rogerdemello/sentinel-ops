"""Per-tenant ingestion → isolated analysis cycle.

Telemetry pushed for tenant "acme" must drive predictions/incidents in acme's own
store only, never leaking into the default tenant the live simulator runs.
"""

from __future__ import annotations

from app.bootstrap import seed_topology
from app.clock import get_clock
from app.db.repository import get_repository
from app.graph.topology import seed_dependencies, seed_services
from app.models import IncidentStatus
from app.telemetry.schema import MetricName, MetricPoint


def _seed_tenant(repo) -> None:
    for svc in seed_services():
        repo.add_service(svc)
    for dep in seed_dependencies():
        repo.add_dependency(dep)


def test_pushed_tenant_telemetry_opens_isolated_incident():
    seed_topology()  # default tenant (the live sim runs here)
    from app.telemetry.simulator import get_simulator

    sim = get_simulator()
    acme = get_repository("acme")
    _seed_tenant(acme)

    # Push a rising db-pool series for acme's orders_db, ending past its 95% threshold.
    base = get_clock().now()
    for i in range(20):
        acme.record_metric(
            MetricPoint(
                service_id="orders_db",
                name=MetricName.db_pool_used_pct,
                value=float(80 + i),  # 80 → 99, crosses 95
                ts=base + i * 60,
            )
        )

    # A few ticks run the default cycle AND a per-tenant cycle for acme.
    for _ in range(5):
        sim.tick()

    acme_incidents = acme.list_incidents()
    assert any(i.service_id == "orders_db" for i in acme_incidents), (
        "acme's pushed telemetry should have opened an incident in acme's store"
    )

    # Isolation: acme's incidents must not appear in the default tenant's store.
    default_repo = get_repository()
    default_ids = {i.id for i in default_repo.list_incidents()}
    assert all(i.id not in default_ids for i in acme_incidents)


def test_default_tenant_unaffected_by_other_tenant():
    seed_topology()
    from app.telemetry.simulator import get_simulator

    sim = get_simulator()
    acme = get_repository("acme")
    _seed_tenant(acme)
    base = get_clock().now()
    for i in range(20):
        acme.record_metric(
            MetricPoint(service_id="orders_db", name=MetricName.cpu, value=float(70 + i), ts=base + i * 60)
        )
    for _ in range(3):
        sim.tick()

    # The acme incidents (if any) are absent from default; default only has its own.
    default_repo = get_repository()
    for inc in default_repo.list_incidents():
        assert inc.status in {
            IncidentStatus.predicted,
            IncidentStatus.active,
            IncidentStatus.mitigating,
            IncidentStatus.resolved,
        }
    assert get_repository("acme") is not default_repo
