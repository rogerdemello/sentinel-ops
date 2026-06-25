"""Telemetry query endpoints + dashboard overview."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import tenant_repo
from app.db.repository import Repository
from app.telemetry.schema import MetricName

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])

# Soft health thresholds (warning / critical) per metric for the overview tiles.
_HEALTH = {
    MetricName.cpu.value: (75, 90),
    MetricName.memory.value: (80, 92),
    MetricName.disk.value: (80, 90),
    MetricName.latency_ms.value: (600, 1500),
    MetricName.error_rate.value: (5, 25),
    MetricName.db_pool_used_pct.value: (80, 95),
    MetricName.auth_failures_per_min.value: (200, 800),
}


def _status_for(metrics: dict[str, float]) -> str:
    status = "healthy"
    for name, value in metrics.items():
        thr = _HEALTH.get(name)
        if not thr:
            continue
        warn, crit = thr
        if value >= crit:
            return "critical"
        if value >= warn:
            status = "warning"
    return status


@router.get("/series")
def series(
    service_id: str,
    metric: MetricName,
    limit: int = Query(120, ge=1, le=720),
    repo: Repository = Depends(tenant_repo),
) -> dict:
    points = repo.series(service_id, metric, limit=limit)
    return {
        "service_id": service_id,
        "metric": metric.value,
        "points": [{"ts": p.ts, "value": p.value} for p in points],
    }


@router.get("/events")
def events(
    limit: int = Query(60, ge=1, le=500),
    service_id: str | None = None,
    repo: Repository = Depends(tenant_repo),
) -> dict:
    items = repo.list_events(limit=limit, service_id=service_id)
    return {"events": [e.model_dump(mode="json") for e in items]}


@router.get("/overview")
def overview(repo: Repository = Depends(tenant_repo)) -> dict:
    rows = []
    for svc in repo.list_services():
        latest = repo.latest_metrics_for(svc.id)
        rows.append(
            {
                "service": svc.model_dump(mode="json"),
                "metrics": latest,
                "status": _status_for(latest),
            }
        )
    return {"services": rows}
