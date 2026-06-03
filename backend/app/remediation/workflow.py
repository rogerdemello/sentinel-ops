"""Approval workflow + simulated execution.

SAFETY: v1 execution is **simulated** only. "Executing" a plan clears the active
synthetic scenario (so generated metrics revert to baseline and the incident
resolves). It never calls any real infrastructure. This boundary is intentional
and is where a real, RBAC-gated executor would later plug in.
"""

from __future__ import annotations

import logging

from app.config import get_settings
from app.db.repository import get_repository
from app.models import (
    AuditEntry,
    Incident,
    IncidentStatus,
    RemediationStatus,
)
from app.memory.store import remember
from app.notify.notifier import get_notifier
from app.remediation.executor import get_executor
from app.telemetry.scenario_manager import get_scenario_manager

logger = logging.getLogger(__name__)

_ALLOWED_ROLES = {"operator", "admin", "system"}


class WorkflowError(Exception):
    pass


def _require_plan(incident: Incident):
    if incident.plan is None:
        raise WorkflowError(f"Incident {incident.id} has no remediation plan")
    return incident.plan


def approve_and_execute(
    incident_id: str, now: float, actor: str = "human", role: str = "operator"
) -> Incident:
    repo = get_repository()
    incident = repo.get_incident(incident_id)
    if incident is None:
        raise WorkflowError(f"Unknown incident {incident_id}")
    plan = _require_plan(incident)
    if plan.status not in (RemediationStatus.proposed,):
        raise WorkflowError(f"Plan already {plan.status.value}")

    # --- RBAC gate ---
    if get_settings().rbac_enabled and role not in _ALLOWED_ROLES:
        raise WorkflowError(f"role '{role}' is not authorized to execute remediation")

    plan.status = RemediationStatus.executing
    plan.approved_by = actor
    incident.auto_remediated = actor == "autonomous"
    incident.status = IncidentStatus.mitigating
    incident.log(
        now,
        "auto_healed" if actor == "autonomous" else "approved",
        ("Autonomously approved" if actor == "autonomous" else "Approved by operator")
        + f"; executing {len(plan.actions)} action(s): "
        + ", ".join(a.kind for a in plan.actions),
    )
    incident.updated_at = now
    repo.upsert_incident(incident)

    # --- execute each action via the configured executor + write audit log ---
    executor = get_executor()
    for action in plan.actions:
        result = executor.execute(action)
        repo.record_audit(
            AuditEntry(
                at=now, actor=actor, role=role, incident_id=incident.id,
                action_kind=action.kind, target_service_id=action.target_service_id,
                executor=executor.name, result_status=result.status,
                detail=result.detail,
            )
        )

    # Simulated world: clear the scenario so metrics recover (no-op for real infra).
    if incident.scenario_key:
        get_scenario_manager().clear(incident.scenario_key)
        logger.info("Simulated remediation cleared scenario '%s'", incident.scenario_key)

    plan.status = RemediationStatus.executed
    plan.decided_at = now
    incident.status = IncidentStatus.resolved
    incident.log(now, "resolved", "Remediation executed (simulated); metrics recovering.")
    incident.updated_at = now
    repo.clear_predictions_for(incident.service_id)
    repo.upsert_incident(incident)
    get_notifier().incident_resolved(incident)
    remember(incident)  # store in RAG memory for future similar-incident recall
    return incident


def reject(incident_id: str, now: float) -> Incident:
    repo = get_repository()
    incident = repo.get_incident(incident_id)
    if incident is None:
        raise WorkflowError(f"Unknown incident {incident_id}")
    plan = _require_plan(incident)
    plan.status = RemediationStatus.rejected
    plan.decided_at = now
    incident.log(now, "rejected", "Remediation plan rejected by operator; incident remains open.")
    incident.updated_at = now
    repo.upsert_incident(incident)
    return incident
