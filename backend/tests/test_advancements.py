"""Tests for the advanced capabilities: executors, audit, postmortem, forecasting,
telemetry sources, and a regression guard for timeline messages."""

from app.agents.postmortem import generate_postmortem
from app.bootstrap import seed_topology
from app.clock import get_clock
from app.db.repository import get_repository
from app.forecasting.forecaster import HoltWintersForecaster, TrendForecaster, get_forecaster
from app.models import IncidentStatus, RemediationAction, Severity
from app.remediation import workflow
from app.remediation.executor import SimulatedExecutor, get_executor
from app.telemetry.simulator import get_simulator
from app.telemetry.sources.synthetic import SyntheticSource


def _open_incident(scenario="db_pool_exhaustion"):
    seed_topology()
    sim = get_simulator()
    repo = get_repository()
    sim.trigger(scenario)
    for _ in range(80):
        sim.tick()
        opens = [i for i in repo.list_incidents() if i.status != IncidentStatus.resolved]
        if opens:
            return opens[0]
    return None


def test_simulated_executor_is_safe():
    action = RemediationAction(kind="restart", target_service_id="checkout",
                               description="x", risk=Severity.low)
    res = SimulatedExecutor().execute(action)
    assert res.status == "simulated"
    assert get_executor().name == "simulated"  # default


def test_timeline_messages_are_populated():
    """Regression: timeline entries must carry their message text."""
    incident = _open_incident()
    assert incident is not None
    assert incident.timeline
    assert all(t.message for t in incident.timeline)
    assert any(t.kind == "detected" for t in incident.timeline)


def test_audit_log_written_on_execution():
    incident = _open_incident("bad_deploy")
    assert incident is not None
    workflow.approve_and_execute(incident.id, get_clock().now())
    audit = get_repository().list_audit()
    assert audit
    assert audit[0].result_status == "simulated"
    assert audit[0].actor == "human"


def test_postmortem_generation_heuristic():
    incident = _open_incident()
    assert incident is not None
    workflow.approve_and_execute(incident.id, get_clock().now())
    pm = generate_postmortem(incident)
    assert "Postmortem" in pm or "postmortem" in pm.lower()
    assert incident.title.split()[0] in pm


def test_forecaster_factory_default_is_trend():
    assert isinstance(get_forecaster(), TrendForecaster)


def test_holtwinters_forecasts_rising_ramp():
    points = [(i * 60.0, 40.0 + i * 1.3) for i in range(40)]
    fc = HoltWintersForecaster().forecast(points, threshold=95.0)
    assert fc is not None
    assert fc.eta_seconds >= 0


def test_synthetic_source_emits_metrics():
    seed_topology()
    metrics, events = SyntheticSource().collect(get_clock().now())
    assert len(metrics) > 0


def test_evaluation_harness_detects_all_scenarios_early():
    from app.eval.harness import evaluate

    report = evaluate(max_ticks=60)
    # Every injected scenario should be detected, with no baseline false positives.
    assert report["recall"] == 1.0
    assert report["false_positives_baseline"] == 0
    assert report["precision"] == 1.0
    # And the whole point: predicted before the metric breached.
    assert report["early_warning_rate"] >= 0.8
    assert report["mean_lead_time_min"] is not None
