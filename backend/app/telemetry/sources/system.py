"""Real host telemetry source (psutil) — the default.

Replaces the scripted synthetic generator with **real measurements from the host
machine**: CPU, memory, disk, network throughput/errors, and process counts are
sampled via ``psutil`` every tick.

The seeded service topology is preserved on purpose — so the dependency graph,
blast-radius, and business-impact narrative stay intact — but each service's
metrics are *derived from the live host snapshot* with a small, deterministic
per-service offset so the services remain distinguishable. Active demo scenarios
are still layered on top (the worse of real-baseline vs. scenario ramp), so you
can either genuinely load the machine to drive a prediction, or inject a scenario
on demand for a repeatable walkthrough.

What is real vs. derived:
  * cpu_pct, memory_pct, disk_pct ........ measured directly from the host.
  * requests_per_sec, error_rate_pct ..... derived from real network packet /
    error-and-drop rates (deltas between ticks).
  * latency_p95_ms ....................... derived from real CPU pressure.
  * db_pool_used_pct ..................... derived from the real open-connection
    count (falls back to a memory-pressure proxy if the OS denies the listing).
  * auth_failures_per_min ................ a small derived proxy (no real auth
    feed exists on a bare host); honestly the weakest signal here.
"""

from __future__ import annotations

import logging
import os
import time
import zlib

from app.db.repository import get_repository
from app.telemetry.generator import metrics_for, ramp_value
from app.telemetry.scenario_manager import get_scenario_manager
from app.telemetry.schema import MetricName, MetricPoint, TelemetryEvent
from app.telemetry.sources.base import TelemetrySource

logger = logging.getLogger(__name__)

try:
    import psutil
except Exception:  # pragma: no cover - import guard; factory handles fallback
    psutil = None  # type: ignore[assignment]

_DISK_PATH = os.path.abspath(os.sep)  # root of the current drive (C:\ / /)


def _offset(service_id: str) -> float:
    """Stable per-service offset in [-1, 1] (crc32 — survives process restarts)."""
    return (zlib.crc32(service_id.encode()) % 1000) / 500.0 - 1.0


class _HostSnapshot:
    """Real host metrics for one tick, plus per-second rates from prior tick."""

    def __init__(self, cpu: float, mem: float, disk: float,
                 reqs_per_sec: float, err_rate: float, conn_pct: float) -> None:
        self.cpu = cpu
        self.mem = mem
        self.disk = disk
        self.reqs_per_sec = reqs_per_sec
        self.err_rate = err_rate
        self.conn_pct = conn_pct


class SystemSource(TelemetrySource):
    name = "system"

    def __init__(self) -> None:
        if psutil is None:  # pragma: no cover - guarded by factory
            raise RuntimeError("psutil is not installed")
        self._prime()

    def _prime(self) -> None:
        # cpu_percent's first call always returns 0.0; prime it so tick 1 is real.
        psutil.cpu_percent(interval=None)
        net = psutil.net_io_counters()
        self._prev_net = net
        self._prev_wall = time.monotonic()

    def _snapshot(self) -> _HostSnapshot:
        cpu = float(psutil.cpu_percent(interval=None))
        mem = float(psutil.virtual_memory().percent)
        try:
            disk = float(psutil.disk_usage(_DISK_PATH).percent)
        except Exception:  # noqa: BLE001
            disk = 0.0

        now_wall = time.monotonic()
        elapsed = max(now_wall - self._prev_wall, 1e-3)
        net = psutil.net_io_counters()
        d_packets = max(
            (net.packets_sent + net.packets_recv)
            - (self._prev_net.packets_sent + self._prev_net.packets_recv), 0
        )
        d_errdrop = max(
            (net.errin + net.errout + net.dropin + net.dropout)
            - (self._prev_net.errin + self._prev_net.errout
               + self._prev_net.dropin + self._prev_net.dropout), 0
        )
        self._prev_net = net
        self._prev_wall = now_wall

        reqs_per_sec = d_packets / elapsed
        err_rate = (d_errdrop / d_packets * 100.0) if d_packets else 0.0

        # Real open-connection count as a DB-pool-pressure proxy (cap ~200).
        try:
            conn_pct = min(len(psutil.net_connections(kind="inet")) / 200.0 * 100.0, 100.0)
        except Exception:  # noqa: BLE001 - net_connections often needs privileges
            conn_pct = mem * 0.6  # fall back to a memory-pressure proxy

        return _HostSnapshot(cpu, mem, disk, reqs_per_sec, err_rate, conn_pct)

    def _value(self, metric: MetricName, service, snap: _HostSnapshot) -> float:
        """Derive a per-service value for ``metric`` from the real host snapshot."""
        off = _offset(service.id)
        if metric is MetricName.cpu:
            return _clamp(snap.cpu * (1.0 + 0.12 * off) + 1.5 * off, 0.0, 100.0)
        if metric is MetricName.memory:
            return _clamp(snap.mem * (1.0 + 0.08 * off), 0.0, 100.0)
        if metric is MetricName.disk:
            # Datastores/caches carry slightly more disk pressure.
            return _clamp(snap.disk * (1.0 + 0.05 * off), 0.0, 100.0)
        if metric is MetricName.latency_ms:
            # Real CPU pressure → tail latency. ~80ms idle, ~480ms at full load.
            return round(max(20.0, 80.0 + snap.cpu * 4.0) * (1.0 + 0.15 * off), 2)
        if metric is MetricName.error_rate:
            return round(max(0.0, snap.err_rate + 0.2 + 0.15 * off), 3)
        if metric is MetricName.requests_per_sec:
            return round(max(0.0, snap.reqs_per_sec * (1.0 + 0.2 * off)), 2)
        if metric is MetricName.db_pool_used_pct:
            return _clamp(snap.conn_pct * (1.0 + 0.1 * off), 0.0, 100.0)
        if metric is MetricName.auth_failures_per_min:
            # No real auth feed on a bare host — a small derived proxy.
            return round(max(0.0, 4.0 + snap.err_rate * 0.5 + 2.0 * off), 2)
        return 0.0

    def collect(self, now: float) -> tuple[list[MetricPoint], list[TelemetryEvent]]:
        repo = get_repository()
        sm = get_scenario_manager()
        active = sm.active(now)
        snap = self._snapshot()

        metrics: list[MetricPoint] = []
        for service in repo.list_services():
            for metric in metrics_for(service):
                baseline = self._value(metric, service, snap)
                worst = baseline
                # Layer any active demo scenario on top (higher = worse).
                for scenario, elapsed_min in active:
                    sv = ramp_value(scenario, service.id, metric, elapsed_min, baseline)
                    if sv is not None:
                        worst = max(worst, sv)
                metrics.append(
                    MetricPoint(service_id=service.id, name=metric, value=round(worst, 2), ts=now)
                )

        # Scenario events (real host emits none of its own) — identical to synthetic.
        events: list[TelemetryEvent] = []
        for rec in sm.active_records():
            elapsed_min = (now - rec.triggered_at) / 60.0
            for idx, ev in enumerate(rec.scenario.events):
                if idx in rec.emitted_event_ids:
                    continue
                if elapsed_min >= ev.at_min:
                    events.append(
                        TelemetryEvent(
                            service_id=ev.service_id, type=ev.type,
                            severity=ev.severity, message=ev.message, ts=now,
                        )
                    )
                    rec.emitted_event_ids.add(idx)
        return metrics, events


def _clamp(value: float, lo: float, hi: float) -> float:
    return round(max(lo, min(hi, value)), 2)
