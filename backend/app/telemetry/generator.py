"""Baseline synthetic metric generation + scenario application.

Produces a realistic, lightly-noisy baseline per (service, metric) each tick.
Active scenarios elevate specific metrics along their ramp; the generator takes
the worse of baseline vs. scenario value (all tracked metrics are "higher = worse").
"""

from __future__ import annotations

import math
import random

from app.models import Service, ServiceKind
from app.telemetry.scenarios import Scenario
from app.telemetry.schema import MetricName

# Deterministic-ish PRNG seeded once for reproducible demos.
_rng = random.Random(42)

# Baseline (center) value per metric; jitter added per tick.
_BASELINE: dict[MetricName, float] = {
    MetricName.cpu: 38.0,
    MetricName.memory: 52.0,
    MetricName.disk: 55.0,
    MetricName.latency_ms: 120.0,
    MetricName.error_rate: 0.3,
    MetricName.requests_per_sec: 1800.0,
    MetricName.db_pool_used_pct: 42.0,
    MetricName.auth_failures_per_min: 6.0,
}

_JITTER: dict[MetricName, float] = {
    MetricName.cpu: 6.0,
    MetricName.memory: 4.0,
    MetricName.disk: 1.5,
    MetricName.latency_ms: 18.0,
    MetricName.error_rate: 0.25,
    MetricName.requests_per_sec: 220.0,
    MetricName.db_pool_used_pct: 8.0,
    MetricName.auth_failures_per_min: 4.0,
}


def metrics_for(service: Service) -> list[MetricName]:
    """Which metrics a given service emits."""
    if service.kind == ServiceKind.edge and service.id == "user":
        return []  # logical user node — no infra metrics
    base = [
        MetricName.cpu,
        MetricName.memory,
        MetricName.latency_ms,
        MetricName.error_rate,
        MetricName.requests_per_sec,
    ]
    if service.kind in (ServiceKind.datastore, ServiceKind.cache):
        base.append(MetricName.disk)
    if service.kind == ServiceKind.datastore:
        base.append(MetricName.db_pool_used_pct)
    if service.id == "auth":
        base.append(MetricName.auth_failures_per_min)
    return base


def _baseline_value(metric: MetricName, tier: int, sim_seconds: float) -> float:
    base = _BASELINE[metric]
    jitter = _JITTER[metric]
    # Gentle diurnal-ish wave on request volume + latency for realism.
    wave = math.sin(sim_seconds / 1800.0) * 0.05
    val = base * (1.0 + wave) + _rng.uniform(-jitter, jitter)
    return max(0.0, val)


def ramp_value(scenario: Scenario, service_id: str, metric: MetricName,
               elapsed_min: float, baseline: float) -> float | None:
    """Absolute scenario value for a (service, metric), or None if not targeted."""
    for r in scenario.ramps:
        if r.service_id == service_id and r.metric == metric:
            progress = (elapsed_min - r.delay_min) / max(r.ramp_min, 0.01)
            progress = max(0.0, min(1.0, progress))
            return baseline + (r.peak - baseline) * progress
    return None


def generate_value(
    service: Service,
    metric: MetricName,
    sim_seconds: float,
    active: list[tuple[Scenario, float]],  # (scenario, elapsed_min)
) -> float:
    baseline = _baseline_value(metric, service.tier, sim_seconds)
    worst = baseline
    for scenario, elapsed_min in active:
        sv = ramp_value(scenario, service.id, metric, elapsed_min, baseline)
        if sv is not None:
            worst = max(worst, sv)
    return round(worst, 2)
