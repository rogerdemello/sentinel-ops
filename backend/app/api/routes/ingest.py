"""External telemetry push ingestion.

Lets any agent/collector POST metrics + events into the platform, independent of
the configured pull source. This is how real OTLP/Fluent/custom exporters feed
SentinelOps in production.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.clock import get_clock
from app.db.repository import get_repository
from app.telemetry.schema import (
    EventSeverity,
    EventType,
    MetricName,
    MetricPoint,
    TelemetryEvent,
)

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


class MetricIn(BaseModel):
    service_id: str
    name: MetricName
    value: float
    ts: float | None = None


class EventIn(BaseModel):
    service_id: str
    type: EventType = EventType.log
    severity: EventSeverity = EventSeverity.info
    message: str
    ts: float | None = None


@router.post("/metrics")
def ingest_metrics(points: list[MetricIn]) -> dict:
    repo = get_repository()
    now = get_clock().now()
    for p in points:
        repo.record_metric(
            MetricPoint(service_id=p.service_id, name=p.name, value=p.value, ts=p.ts or now)
        )
    return {"ingested": len(points)}


@router.post("/events")
def ingest_events(events: list[EventIn]) -> dict:
    repo = get_repository()
    now = get_clock().now()
    for e in events:
        repo.record_event(
            TelemetryEvent(
                service_id=e.service_id, type=e.type, severity=e.severity,
                message=e.message, ts=e.ts or now,
            )
        )
    return {"ingested": len(events)}
