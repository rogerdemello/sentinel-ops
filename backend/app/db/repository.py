"""In-memory operational store (source of truth for the live simulation).

This is intentionally simple and synchronous. When Supabase is configured we
*mirror* writes to it (for frontend Realtime / history), but the running engine
always reads from memory so the demo works with zero external setup.

A single process-wide instance is exposed via :func:`get_repository`.
"""

from __future__ import annotations

from collections import defaultdict, deque
from functools import lru_cache

from app.config import get_settings
from app.db import supabase_client as sb
from app.models import (
    Dependency,
    Incident,
    Prediction,
    Service,
)
from app.telemetry.schema import MetricName, MetricPoint, TelemetryEvent

# How many points to retain per (service, metric). At 1 sim-minute/tick this is
# ~12 hours of history — plenty for forecasting windows.
_SERIES_MAXLEN = 720
_EVENTS_MAXLEN = 2000


class Repository:
    def __init__(self) -> None:
        self.services: dict[str, Service] = {}
        self.dependencies: list[Dependency] = []
        self._series: dict[tuple[str, str], deque[MetricPoint]] = defaultdict(
            lambda: deque(maxlen=_SERIES_MAXLEN)
        )
        self.events: deque[TelemetryEvent] = deque(maxlen=_EVENTS_MAXLEN)
        self.predictions: dict[str, Prediction] = {}
        self.incidents: dict[str, Incident] = {}

    # --- topology -----------------------------------------------------------
    def add_service(self, service: Service) -> Service:
        self.services[service.id] = service
        sb.upsert("services", service.model_dump(mode="json"))
        return service

    def add_dependency(self, dep: Dependency) -> Dependency:
        self.dependencies.append(dep)
        sb.upsert(
            "dependencies",
            {
                "source_id": dep.source_id,
                "target_id": dep.target_id,
                "kind": dep.kind,
                "criticality": dep.criticality,
            },
        )
        return dep

    def get_service(self, service_id: str) -> Service | None:
        return self.services.get(service_id)

    def list_services(self) -> list[Service]:
        return list(self.services.values())

    def list_dependencies(self) -> list[Dependency]:
        return list(self.dependencies)

    # --- metrics ------------------------------------------------------------
    def record_metric(self, point: MetricPoint) -> None:
        self._series[(point.service_id, point.name.value)].append(point)
        if get_settings().persist_telemetry:
            sb.insert("telemetry_metrics", point.model_dump(mode="json"))

    def series(
        self, service_id: str, name: MetricName, limit: int | None = None
    ) -> list[MetricPoint]:
        seq = list(self._series.get((service_id, name.value), ()))
        return seq[-limit:] if limit else seq

    def latest_metric(self, service_id: str, name: MetricName) -> MetricPoint | None:
        seq = self._series.get((service_id, name.value))
        return seq[-1] if seq else None

    def latest_metrics_for(self, service_id: str) -> dict[str, float]:
        out: dict[str, float] = {}
        for (sid, name), seq in self._series.items():
            if sid == service_id and seq:
                out[name] = seq[-1].value
        return out

    # --- events -------------------------------------------------------------
    def record_event(self, event: TelemetryEvent) -> None:
        self.events.append(event)
        sb.insert("telemetry_events", event.model_dump(mode="json"))

    def list_events(
        self, limit: int = 100, service_id: str | None = None
    ) -> list[TelemetryEvent]:
        items = list(self.events)
        if service_id:
            items = [e for e in items if e.service_id == service_id]
        return items[-limit:][::-1]  # newest first

    # --- predictions --------------------------------------------------------
    def upsert_prediction(self, pred: Prediction) -> None:
        self.predictions[pred.id] = pred
        sb.upsert("predictions", pred.model_dump(mode="json"))

    def list_predictions(self) -> list[Prediction]:
        return sorted(
            self.predictions.values(), key=lambda p: p.probability, reverse=True
        )

    def clear_predictions_for(self, service_id: str) -> None:
        for pid in [p.id for p in self.predictions.values() if p.service_id == service_id]:
            self.predictions.pop(pid, None)

    # --- incidents ----------------------------------------------------------
    def upsert_incident(self, incident: Incident) -> None:
        self.incidents[incident.id] = incident
        sb.upsert("incidents", incident.model_dump(mode="json"))

    def get_incident(self, incident_id: str) -> Incident | None:
        return self.incidents.get(incident_id)

    def list_incidents(self) -> list[Incident]:
        return sorted(
            self.incidents.values(), key=lambda i: i.created_at, reverse=True
        )

    def active_incident_for_scenario(self, scenario_key: str) -> Incident | None:
        for inc in self.incidents.values():
            if inc.scenario_key == scenario_key and inc.status != "resolved":
                return inc
        return None


@lru_cache
def get_repository() -> Repository:
    return Repository()
