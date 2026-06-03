from app.bootstrap import seed_topology
from app.clock import get_clock
from app.db.repository import get_repository
from app.models import IncidentStatus, RemediationStatus
from app.remediation import workflow
from app.telemetry.scenario_manager import get_scenario_manager
from app.telemetry.simulator import get_simulator


def _run_until_incident(sim, repo, max_ticks=80):
    for _ in range(max_ticks):
        sim.tick()
        open_incs = [i for i in repo.list_incidents() if i.status != IncidentStatus.resolved]
        if open_incs:
            return open_incs[0]
    return None


def test_scenario_opens_incident_with_full_pipeline():
    seed_topology()
    sim = get_simulator()
    repo = get_repository()
    sim.trigger("db_pool_exhaustion")

    incident = _run_until_incident(sim, repo)
    assert incident is not None
    assert incident.scenario_key == "db_pool_exhaustion"
    assert incident.root_cause  # RCA produced a root cause
    assert len(incident.findings) == 3  # three domain agents
    assert incident.impact is not None
    assert incident.impact.revenue_at_risk > 0
    assert incident.plan is not None
    assert incident.plan.actions  # remediation proposed
    assert incident.plan.status == RemediationStatus.proposed


def test_approve_executes_and_resolves():
    seed_topology()
    sim = get_simulator()
    repo = get_repository()
    sim.trigger("bad_deploy")
    incident = _run_until_incident(sim, repo)
    assert incident is not None

    resolved = workflow.approve_and_execute(incident.id, get_clock().now())
    assert resolved.status == IncidentStatus.resolved
    assert resolved.plan.status == RemediationStatus.executed
    # Scenario cleared -> no longer active.
    assert get_scenario_manager().is_active("bad_deploy") is False


def test_autonomous_mode_auto_heals_low_risk_incident():
    from app.policy import get_policy

    seed_topology()
    policy = get_policy()
    policy.auto_remediate = True  # max_auto_risk defaults to "low"

    sim = get_simulator()
    repo = get_repository()
    # memory_leak's plan is restart/scale (low risk) -> should auto-heal.
    sim.trigger("memory_leak")

    healed = None
    for _ in range(80):
        sim.tick()
        resolved = [
            i for i in repo.list_incidents()
            if i.status == IncidentStatus.resolved and i.auto_remediated
        ]
        if resolved:
            healed = resolved[0]
            break

    assert healed is not None
    assert healed.auto_remediated is True
    assert healed.plan.approved_by == "autonomous"
    assert any(t.kind == "auto_healed" for t in healed.timeline)


def test_reject_keeps_incident_open():
    seed_topology()
    sim = get_simulator()
    repo = get_repository()
    sim.trigger("memory_leak")
    incident = _run_until_incident(sim, repo)
    assert incident is not None

    out = workflow.reject(incident.id, get_clock().now())
    assert out.plan.status == RemediationStatus.rejected
    assert out.status != IncidentStatus.resolved
