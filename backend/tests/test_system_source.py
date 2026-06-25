"""Real host telemetry source (psutil) — shape + scenario-layering tests.

These don't assert exact values (they're real host readings) but verify the
adapter produces well-formed metrics for the seeded topology and still lets an
injected scenario drive a metric past its threshold.
"""

from __future__ import annotations

import os

from app.bootstrap import seed_topology
from app.clock import get_clock
from app.db.repository import get_repository
from app.telemetry.schema import MetricName
from app.telemetry.sources.system import SystemSource


def test_system_source_emits_real_metrics_for_every_service():
    seed_topology()
    repo = get_repository()
    src = SystemSource()
    now = get_clock().now()
    src.collect(now)  # prime cpu_percent / net deltas
    metrics, _events = src.collect(get_clock().advance(60))

    assert metrics, "system source produced no metrics"
    # Every non-logical service should report at least cpu + memory.
    by_service: dict[str, set[str]] = {}
    for m in metrics:
        by_service.setdefault(m.service_id, set()).add(m.name.value)
        assert m.value >= 0.0
    for svc in repo.list_services():
        if svc.id == "user":
            continue
        assert MetricName.cpu.value in by_service.get(svc.id, set())
        assert MetricName.memory.value in by_service.get(svc.id, set())


def test_system_source_cpu_memory_are_percentages():
    seed_topology()
    src = SystemSource()
    src.collect(get_clock().now())
    metrics, _ = src.collect(get_clock().advance(60))
    for m in metrics:
        if m.name in (MetricName.cpu, MetricName.memory, MetricName.disk):
            assert 0.0 <= m.value <= 100.0


def test_scenario_ramps_layer_on_top_of_real_baseline():
    """An injected scenario must still push its target metric toward its peak,
    even though the baseline now comes from real host readings."""
    os.environ["TELEMETRY_SOURCE"] = "system"
    seed_topology()
    from app.telemetry.scenario_manager import get_scenario_manager

    sm = get_scenario_manager()
    src = SystemSource()
    start = get_clock().now()
    sm.trigger("db_pool_exhaustion", start)

    # Advance well past the ramp so the scenario reaches near its peak.
    peak = 0.0
    for _ in range(60):
        now = get_clock().advance(60)
        metrics, _ = src.collect(now)
        for m in metrics:
            if m.service_id == "orders_db" and m.name is MetricName.db_pool_used_pct:
                peak = max(peak, m.value)

    # db_pool_exhaustion ramps orders_db's pool toward ~99 — far above any real baseline.
    assert peak > 95.0, f"scenario did not elevate the metric (peak={peak})"
