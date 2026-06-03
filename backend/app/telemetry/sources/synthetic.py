"""Synthetic telemetry source (default).

Generates baseline + scenario-perturbed metrics and emits scenario events. This
is the demo's self-contained world; swapping in Prometheus/OTLP needs no other
code changes.
"""

from __future__ import annotations

from app.db.repository import get_repository
from app.telemetry.generator import generate_value, metrics_for
from app.telemetry.scenario_manager import get_scenario_manager
from app.telemetry.schema import MetricPoint, TelemetryEvent
from app.telemetry.sources.base import TelemetrySource


class SyntheticSource(TelemetrySource):
    name = "synthetic"

    def collect(self, now: float) -> tuple[list[MetricPoint], list[TelemetryEvent]]:
        repo = get_repository()
        sm = get_scenario_manager()
        active = sm.active(now)

        metrics: list[MetricPoint] = []
        for service in repo.list_services():
            for metric in metrics_for(service):
                value = generate_value(service, metric, now, active)
                metrics.append(
                    MetricPoint(service_id=service.id, name=metric, value=value, ts=now)
                )

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
