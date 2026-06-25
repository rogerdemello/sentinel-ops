"""In-memory operational store (source of truth for the live simulation).

This is intentionally simple and synchronous. When Supabase is configured we
*mirror* writes to it (for frontend Realtime / history), but the running engine
always reads from memory so the demo works with zero external setup.

A single process-wide instance is exposed via :func:`get_repository`.
"""

from __future__ import annotations

import threading
from collections import defaultdict, deque

from app.config import get_settings
from app.db import supabase_client as sb
from app.models import (
    AuditEntry,
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
        # Guards every shared collection below. The engine tick now runs in a worker
        # thread (offloaded off the event loop) while HTTP handlers run in FastAPI's
        # threadpool — both mutate this store, so iterate/mutate must be serialized
        # (otherwise e.g. sorting predictions while one is upserted raises
        # "dictionary changed size during iteration"). Reentrant so nested calls work.
        self._lock = threading.RLock()
        self.tenant_id: str = "default"
        self.services: dict[str, Service] = {}
        self.dependencies: list[Dependency] = []
        self._series: dict[tuple[str, str], deque[MetricPoint]] = defaultdict(
            lambda: deque(maxlen=_SERIES_MAXLEN)
        )
        self.events: deque[TelemetryEvent] = deque(maxlen=_EVENTS_MAXLEN)
        self.predictions: dict[str, Prediction] = {}
        self.incidents: dict[str, Incident] = {}
        self.audit: deque[AuditEntry] = deque(maxlen=2000)
        # Sim-time a service's last incident resolved — used to suppress an immediate
        # re-open while the underlying (often real) metric is still elevated.
        self.resolved_at: dict[str, float] = {}

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
        with self._lock:
            self._series[(point.service_id, point.name.value)].append(point)
        if get_settings().persist_telemetry:
            sb.insert("telemetry_metrics", point.model_dump(mode="json"))

    def series(
        self, service_id: str, name: MetricName, limit: int | None = None
    ) -> list[MetricPoint]:
        with self._lock:
            seq = list(self._series.get((service_id, name.value), ()))
        return seq[-limit:] if limit else seq

    def latest_metric(self, service_id: str, name: MetricName) -> MetricPoint | None:
        with self._lock:
            seq = self._series.get((service_id, name.value))
            return seq[-1] if seq else None

    def latest_metrics_for(self, service_id: str) -> dict[str, float]:
        out: dict[str, float] = {}
        with self._lock:
            for (sid, name), seq in self._series.items():
                if sid == service_id and seq:
                    out[name] = seq[-1].value
        return out

    # --- events -------------------------------------------------------------
    def record_event(self, event: TelemetryEvent) -> None:
        with self._lock:
            self.events.append(event)
        sb.insert("telemetry_events", event.model_dump(mode="json"))

    def list_events(
        self, limit: int = 100, service_id: str | None = None
    ) -> list[TelemetryEvent]:
        with self._lock:
            items = list(self.events)
        if service_id:
            items = [e for e in items if e.service_id == service_id]
        return items[-limit:][::-1]  # newest first

    # --- predictions --------------------------------------------------------
    def upsert_prediction(self, pred: Prediction) -> None:
        with self._lock:
            self.predictions[pred.id] = pred
        sb.upsert("predictions", pred.model_dump(mode="json"))

    def list_predictions(self) -> list[Prediction]:
        with self._lock:
            preds = list(self.predictions.values())
        return sorted(preds, key=lambda p: p.probability, reverse=True)

    def clear_predictions_for(self, service_id: str) -> None:
        with self._lock:
            stale = [p.id for p in self.predictions.values() if p.service_id == service_id]
            for pid in stale:
                self.predictions.pop(pid, None)

    # --- rehydration (load from DB on boot; must NOT mirror back) -----------
    def load_incident(self, incident: Incident) -> None:
        with self._lock:
            self.incidents[incident.id] = incident

    def load_prediction(self, pred: Prediction) -> None:
        with self._lock:
            self.predictions[pred.id] = pred

    # --- incidents ----------------------------------------------------------
    def upsert_incident(self, incident: Incident) -> None:
        with self._lock:
            self.incidents[incident.id] = incident
        sb.upsert("incidents", incident.model_dump(mode="json"))

    def get_incident(self, incident_id: str) -> Incident | None:
        with self._lock:
            return self.incidents.get(incident_id)

    def list_incidents(self) -> list[Incident]:
        with self._lock:
            incs = list(self.incidents.values())
        return sorted(incs, key=lambda i: i.created_at, reverse=True)

    # --- audit ------------------------------------------------------------
    def record_audit(self, entry: AuditEntry) -> None:
        with self._lock:
            self.audit.append(entry)
        sb.insert("audit_log", entry.model_dump(mode="json"))

    def list_audit(self, limit: int = 100) -> list[AuditEntry]:
        with self._lock:
            items = list(self.audit)
        return items[-limit:][::-1]

    def mark_resolved(self, service_id: str, ts: float) -> None:
        with self._lock:
            self.resolved_at[service_id] = ts

    def resolved_recently(self, service_id: str, now: float, window: float) -> bool:
        with self._lock:
            ts = self.resolved_at.get(service_id)
        return ts is not None and (now - ts) < window

    def active_incident_for_scenario(self, scenario_key: str) -> Incident | None:
        with self._lock:
            for inc in self.incidents.values():
                if inc.scenario_key == scenario_key and inc.status != "resolved":
                    return inc
        return None


# --- tenant-scoped registry -------------------------------------------------
# Each tenant gets an isolated Repository. The live simulator/engine operate on
# the "default" tenant; API requests carrying `X-Tenant-Id` are served from their
# own store, so tenants never see each other's incidents. A no-arg call resolves
# to "default", so all existing call sites (engine, tests) are unchanged.
_repos: dict[str, "Repository"] = {}
_repos_lock = threading.Lock()
DEFAULT_TENANT = "default"


def get_repository(tenant_id: str | None = None) -> "Repository":
    tid = tenant_id or DEFAULT_TENANT
    with _repos_lock:
        repo = _repos.get(tid)
        if repo is None:
            repo = Repository()
            repo.tenant_id = tid
            _repos[tid] = repo
        return repo


def list_tenants() -> list[str]:
    """All tenant ids that currently have a store (the live ones)."""
    with _repos_lock:
        return list(_repos.keys())


def _clear_repositories() -> None:
    with _repos_lock:
        _repos.clear()


# Mimic the lru_cache API the rest of the codebase (conftest, eval harness) relies on.
get_repository.cache_clear = _clear_repositories  # type: ignore[attr-defined]
