"""Executive / operational KPI summary."""

from __future__ import annotations

from fastapi import APIRouter

from app.db.repository import get_repository
from app.models import IncidentStatus

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/summary")
def summary() -> dict:
    repo = get_repository()
    incidents = repo.list_incidents()
    resolved = [i for i in incidents if i.status == IncidentStatus.resolved]
    active = [i for i in incidents if i.status != IncidentStatus.resolved]

    # An outage is "prevented" if it was resolved before its lead metric ever
    # breached (no 'breached' timeline entry) — i.e. fixed while still predicted.
    prevented = [
        i for i in resolved if not any(t.kind == "breached" for t in i.timeline)
    ]
    auto_healed = [i for i in resolved if i.auto_remediated]

    mttr_values = [
        i.updated_at - i.created_at for i in resolved if i.updated_at >= i.created_at
    ]
    mttr = sum(mttr_values) / len(mttr_values) if mttr_values else 0.0

    revenue_protected = sum(
        i.impact.revenue_at_risk for i in resolved if i.impact is not None
    )

    return {
        "active_incidents": len(active),
        "resolved_incidents": len(resolved),
        "outages_prevented": len(prevented),
        "auto_healed": len(auto_healed),
        "mttr_seconds": round(mttr, 1),
        "revenue_protected": round(revenue_protected, 2),
        "predictions": len(repo.list_predictions()),
    }
