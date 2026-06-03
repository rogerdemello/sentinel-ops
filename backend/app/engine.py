"""Analysis engine — the autonomous pipeline run each simulation tick.

Flow per cycle:
  1. Forecast: scan watched (service, metric) trends -> predictions.
  2. Incident lifecycle: when a prediction crosses the creation threshold and no
     incident is open for that service, open one and run the full pipeline:
     multi-agent RCA -> blast radius -> business impact -> remediation plan.
  3. Update open incidents (probability, predicted -> active on breach).

RCA/impact/remediation run once at incident creation (not every tick).
"""

from __future__ import annotations

import logging

from app.agents.context import DiagnosisContext
from app.agents.orchestrator import diagnose
from app.agents.remediation_agent import plan_remediation
from app.db.repository import get_repository
from app.graph.blast_radius import compute_blast_radius
from app.graph.service import get_graph
from app.impact.estimator import estimate_impact
from app.models import (
    Incident,
    IncidentStatus,
    IncidentType,
    Prediction,
    Severity,
)
from app.notify.notifier import get_notifier
from app.forecasting.forecaster import get_forecaster
from app.policy import get_policy
from app.remediation.workflow import WorkflowError, approve_and_execute
from app.telemetry.scenario_manager import get_scenario_manager
from app.telemetry.scenarios import Scenario
from app.telemetry.schema import MetricName

logger = logging.getLogger(__name__)

# (metric, critical threshold, incident type if this is the lead signal)
_WATCHED: list[tuple[MetricName, float, IncidentType]] = [
    (MetricName.db_pool_used_pct, 95.0, IncidentType.infra_failure),
    (MetricName.memory, 92.0, IncidentType.degradation),
    (MetricName.cpu, 90.0, IncidentType.infra_failure),
    (MetricName.disk, 90.0, IncidentType.infra_failure),
    (MetricName.error_rate, 25.0, IncidentType.degradation),
    (MetricName.latency_ms, 1500.0, IncidentType.outage),
    (MetricName.auth_failures_per_min, 800.0, IncidentType.security),
]

_CREATE_THRESHOLD = 0.6  # probability at/above which we open an incident


def run_cycle(now: float) -> None:
    repo = get_repository()
    graph = get_graph()
    sm = get_scenario_manager()

    open_incidents = [
        inc for inc in repo.list_incidents() if inc.status != IncidentStatus.resolved
    ]
    open_by_service = {inc.service_id: inc for inc in open_incidents}

    # Services already explained by an open incident (its root + blast radius).
    # A new prediction on one of these is a downstream symptom, not a new incident.
    covered: set[str] = set()
    for inc in open_incidents:
        covered.add(inc.service_id)
        covered.update(b.service_id for b in compute_blast_radius(inc.service_id, graph))

    new_candidates: list[tuple[object, Prediction]] = []

    for service in repo.list_services():
        best: tuple[float, Prediction] | None = None
        for metric, threshold, itype in _WATCHED:
            series = repo.series(service.id, metric, limit=60)
            if len(series) < 8:
                continue
            fc = get_forecaster().forecast([(p.ts, p.value) for p in series], threshold)
            if fc is None or fc.probability < 0.3:
                continue
            pred = Prediction(
                service_id=service.id,
                incident_type=itype,
                probability=round(fc.probability, 3),
                eta_seconds=fc.eta_seconds,
                metric=metric.value,
                summary=(
                    f"{service.name}: {metric.value} trending to {threshold:g} "
                    f"(now {fc.current:.1f}); "
                    + ("breached" if fc.eta_seconds == 0
                       else f"ETA ~{fc.eta_seconds // 60} min")
                ),
                features={"slope_per_sec": fc.slope_per_sec, "r2": fc.r2,
                          "current": fc.current, "threshold": threshold},
                created_at=now,
            )
            if best is None or pred.probability > best[0]:
                best = (pred.probability, pred)

        # Refresh predictions for this service.
        repo.clear_predictions_for(service.id)
        if best is None:
            continue
        prob, pred = best
        repo.upsert_prediction(pred)

        existing = open_by_service.get(service.id)
        if existing is not None:
            _update_incident(existing, pred, now)
        elif prob >= _CREATE_THRESHOLD:
            new_candidates.append((service, pred))

    # Open incidents deepest-tier first so a root cause suppresses the downstream
    # symptom incidents that fall within its blast radius (event correlation).
    new_candidates.sort(key=lambda c: c[0].tier, reverse=True)
    for service, pred in new_candidates:
        if service.id in covered:
            continue
        _open_incident(service.id, pred, now)
        covered.add(service.id)
        covered.update(b.service_id for b in compute_blast_radius(service.id, graph))


def _update_incident(incident: Incident, pred: Prediction, now: float) -> None:
    repo = get_repository()
    incident.probability = pred.probability
    incident.eta_seconds = pred.eta_seconds
    # Promote to active once the lead metric has actually breached.
    if pred.eta_seconds == 0 and incident.status == IncidentStatus.predicted:
        incident.status = IncidentStatus.active
        incident.log(now, "breached", f"{pred.metric} crossed its critical threshold.")
    incident.updated_at = now
    repo.upsert_incident(incident)


def _open_incident(service_id: str, pred: Prediction, now: float) -> None:
    repo = get_repository()
    graph = get_graph()
    sm = get_scenario_manager()
    service = repo.get_service(service_id)
    if service is None:
        return

    active = sm.scenario_for_service(service_id)
    scenario: Scenario | None = active.scenario if active else None

    impacted = [b.service_id for b in compute_blast_radius(service_id, graph)]

    incident = Incident(
        service_id=service_id,
        incident_type=pred.incident_type,
        status=IncidentStatus.predicted,
        severity=scenario.severity if scenario else Severity.high,
        title=scenario.name if scenario else f"Predicted {pred.incident_type.value} on {service.name}",
        scenario_key=scenario.key if scenario else None,
        probability=pred.probability,
        eta_seconds=pred.eta_seconds,
        lead_metric=pred.metric,
        lead_threshold=pred.features.get("threshold"),
        created_at=now,
        updated_at=now,
    )
    incident.log(now, "detected", pred.summary)

    # --- multi-agent RCA ---
    metrics_snapshot = {
        sid: repo.latest_metrics_for(sid)
        for sid in [service_id, *impacted]
    }
    recent_events = [
        f"[{e.severity.value}] {e.service_id}: {e.message}"
        for e in repo.list_events(limit=12)
        if e.service_id in {service_id, *impacted}
    ]
    ctx = DiagnosisContext(
        failing_service=service,
        incident_type=pred.incident_type,
        impacted_service_ids=impacted,
        metrics=metrics_snapshot,
        recent_events=recent_events,
        lead_metric=pred.metric,
        scenario_hint=scenario.root_cause_hint if scenario else None,
        recommended_actions=scenario.recommended_actions if scenario else [],
    )
    findings, root_cause, diagnosis = diagnose(ctx)
    incident.findings = findings
    incident.root_cause = root_cause
    incident.diagnosis = diagnosis
    incident.log(now, "rca", f"Multi-agent RCA complete. Root cause: {root_cause}")

    # --- business impact ---
    services_by_id = {s.id: s for s in repo.list_services()}
    incident.impact = estimate_impact(service, services_by_id, graph)
    incident.severity = incident.impact.severity
    incident.log(now, "impact", incident.impact.headline)

    # --- remediation plan (proposed; needs human approval) ---
    incident.plan = plan_remediation(
        incident, service,
        scenario.recommended_actions if scenario else ["restart", "scale"],
        now,
    )
    incident.log(
        now, "planned",
        f"Remediation plan proposed ({len(incident.plan.actions)} action(s), "
        f"max risk {incident.plan.max_risk.value}).",
    )

    repo.upsert_incident(incident)
    logger.info("Opened incident %s for %s (p=%.2f)", incident.id, service_id, pred.probability)
    get_notifier().incident_opened(incident)

    # --- autonomous self-healing (policy-gated) ---
    if get_policy().allows_auto(incident.plan.max_risk):
        try:
            approve_and_execute(incident.id, now, actor="autonomous", role="system")
            logger.info("Auto-healed incident %s (risk<=policy)", incident.id)
        except WorkflowError as exc:  # pragma: no cover - defensive
            logger.warning("Auto-heal failed for %s: %s", incident.id, exc)
