"""Translate a technical failure into business impact.

Affected users uses the *breadth* (max over impacted user-facing nodes) to avoid
double-counting overlapping populations. Revenue-at-risk sums the per-minute
revenue attributable to the failing node + impacted callers, projected over an
estimated disruption window.
"""

from __future__ import annotations

from app.graph.blast_radius import compute_blast_radius
from app.graph.interface import GraphStore
from app.models import ImpactAssessment, Service, Severity


def _severity_from(users: int, revenue_at_risk: float) -> Severity:
    if revenue_at_risk >= 1_000_000 or users >= 750_000:
        return Severity.critical
    if revenue_at_risk >= 250_000 or users >= 300_000:
        return Severity.high
    if revenue_at_risk >= 50_000 or users >= 50_000:
        return Severity.medium
    return Severity.low


def estimate_impact(
    failing_service: Service,
    services_by_id: dict[str, Service],
    graph: GraphStore,
    window_minutes: float = 60.0,
) -> ImpactAssessment:
    impacted = compute_blast_radius(failing_service.id, graph)
    impacted_ids = [b.service_id for b in impacted]
    all_ids = [failing_service.id, *impacted_ids]

    affected_users = max(
        (services_by_id[s].users for s in all_ids if s in services_by_id),
        default=failing_service.users,
    )

    # Weight each node's revenue by how critically it's tied to the failure.
    crit_by_id = {b.service_id: b.criticality for b in impacted}
    revenue_per_min = failing_service.revenue_per_min
    for sid in impacted_ids:
        svc = services_by_id.get(sid)
        if svc:
            revenue_per_min += svc.revenue_per_min * crit_by_id.get(sid, 1.0)
    revenue_at_risk = round(revenue_per_min * window_minutes, 2)

    severity = _severity_from(affected_users, revenue_at_risk)
    headline = (
        f"{failing_service.name} failure risks {affected_users:,} users and "
        f"~${revenue_at_risk:,.0f} over {int(window_minutes)} min"
    )
    return ImpactAssessment(
        affected_service_ids=all_ids,
        affected_users=affected_users,
        revenue_at_risk=revenue_at_risk,
        severity=severity,
        headline=headline,
    )
