"""Unified telemetry schema.

All sources (metrics, logs, security events, k8s events, deploy events) are
normalized into these models before processing or persistence.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.models import new_id


# Canonical metric names emitted per service. The prediction engine watches
# these; scenarios ramp specific ones to trigger incidents.
class MetricName(str, Enum):
    cpu = "cpu_pct"
    memory = "memory_pct"
    disk = "disk_pct"
    latency_ms = "latency_p95_ms"
    error_rate = "error_rate_pct"
    requests_per_sec = "requests_per_sec"
    db_pool_used_pct = "db_pool_used_pct"
    auth_failures_per_min = "auth_failures_per_min"


class MetricPoint(BaseModel):
    id: str = Field(default_factory=new_id)
    service_id: str
    name: MetricName
    value: float
    ts: float  # simulated epoch seconds


class EventType(str, Enum):
    log = "log"
    security = "security"
    kubernetes = "kubernetes"
    deploy = "deploy"
    trace = "trace"


class EventSeverity(str, Enum):
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"


class TelemetryEvent(BaseModel):
    id: str = Field(default_factory=new_id)
    service_id: str
    type: EventType
    severity: EventSeverity = EventSeverity.info
    message: str
    ts: float
    attributes: dict[str, str] = Field(default_factory=dict)
