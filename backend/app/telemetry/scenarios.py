"""Injectable incident scenarios.

Each scenario ramps specific (service, metric) pairs over simulated time so the
prediction engine can detect the rising trend and forecast a breach *before* the
metric reaches critical levels. Scenarios also carry the metadata the RCA agents
and remediation engine need (narrative hints, recommended actions).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models import IncidentType, Severity
from app.telemetry.schema import EventSeverity, EventType, MetricName


@dataclass(frozen=True)
class MetricRamp:
    service_id: str
    metric: MetricName
    peak: float  # target value at full ramp
    delay_min: float = 0.0  # sim-minutes before the ramp starts
    ramp_min: float = 25.0  # sim-minutes to go from baseline -> peak


@dataclass(frozen=True)
class ScenarioEvent:
    service_id: str
    type: EventType
    severity: EventSeverity
    message: str
    at_min: float = 0.0  # emit once, this many sim-minutes after trigger


@dataclass(frozen=True)
class Scenario:
    key: str
    name: str
    target_service_id: str  # the failing node (root)
    incident_type: IncidentType
    severity: Severity
    primary_metric: MetricName  # the metric whose breach defines the incident
    breach_threshold: float  # value at which the incident becomes "active"
    ramps: list[MetricRamp]
    events: list[ScenarioEvent] = field(default_factory=list)
    # Hints surfaced to the RCA agents / heuristic fallback.
    root_cause_hint: str = ""
    recommended_actions: list[str] = field(default_factory=list)


SCENARIOS: dict[str, Scenario] = {
    "db_pool_exhaustion": Scenario(
        key="db_pool_exhaustion",
        name="Orders DB connection-pool exhaustion",
        target_service_id="orders_db",
        incident_type=IncidentType.infra_failure,
        severity=Severity.critical,
        primary_metric=MetricName.db_pool_used_pct,
        breach_threshold=95.0,
        ramps=[
            MetricRamp("orders_db", MetricName.db_pool_used_pct, peak=100.0, ramp_min=22.0),
            MetricRamp("orders_db", MetricName.latency_ms, peak=1800.0, delay_min=4, ramp_min=20),
            MetricRamp("checkout", MetricName.latency_ms, peak=2200.0, delay_min=6, ramp_min=18),
            MetricRamp("checkout", MetricName.error_rate, peak=35.0, delay_min=8, ramp_min=16),
        ],
        events=[
            ScenarioEvent("orders_db", EventType.log, EventSeverity.warning,
                          "connection pool near capacity (waiters growing)", at_min=5),
            ScenarioEvent("checkout", EventType.log, EventSeverity.error,
                          "TimeoutError acquiring DB connection from pool", at_min=10),
        ],
        root_cause_hint=(
            "Orders DB connection pool is saturating; checkout requests block waiting "
            "for connections, driving latency and error-rate up across checkout."
        ),
        recommended_actions=["scale", "restart", "failover"],
    ),
    "memory_leak": Scenario(
        key="memory_leak",
        name="Catalog service memory leak / OOM risk",
        target_service_id="catalog",
        incident_type=IncidentType.degradation,
        severity=Severity.high,
        primary_metric=MetricName.memory,
        breach_threshold=94.0,
        ramps=[
            MetricRamp("catalog", MetricName.memory, peak=99.0, ramp_min=26.0),
            MetricRamp("catalog", MetricName.latency_ms, peak=900.0, delay_min=10, ramp_min=18),
            MetricRamp("catalog", MetricName.error_rate, peak=12.0, delay_min=16, ramp_min=12),
        ],
        events=[
            ScenarioEvent("catalog", EventType.kubernetes, EventSeverity.warning,
                          "pod memory working set climbing; GC pauses lengthening", at_min=8),
        ],
        root_cause_hint=(
            "Catalog service memory grows monotonically (suspected leak), heading "
            "toward the container limit and an OOMKill."
        ),
        recommended_actions=["restart", "scale"],
    ),
    "bad_deploy": Scenario(
        key="bad_deploy",
        name="Checkout bad deployment (error spike)",
        target_service_id="checkout",
        incident_type=IncidentType.degradation,
        severity=Severity.high,
        primary_metric=MetricName.error_rate,
        breach_threshold=25.0,
        ramps=[
            MetricRamp("checkout", MetricName.error_rate, peak=48.0, delay_min=2, ramp_min=10.0),
            MetricRamp("checkout", MetricName.latency_ms, peak=1400.0, delay_min=2, ramp_min=10),
        ],
        events=[
            ScenarioEvent("checkout", EventType.deploy, EventSeverity.info,
                          "deployment checkout@v2.7.0 rolled out", at_min=0),
            ScenarioEvent("checkout", EventType.log, EventSeverity.error,
                          "NullReferenceException in PaymentMapper (new code path)", at_min=3),
        ],
        root_cause_hint=(
            "A recent checkout deployment (v2.7.0) introduced a regression causing a "
            "spike in 5xx errors immediately after rollout."
        ),
        recommended_actions=["rollback"],
    ),
    "auth_attack": Scenario(
        key="auth_attack",
        name="Auth service credential-stuffing attack",
        target_service_id="auth",
        incident_type=IncidentType.security,
        severity=Severity.critical,
        primary_metric=MetricName.auth_failures_per_min,
        breach_threshold=800.0,
        ramps=[
            MetricRamp("auth", MetricName.auth_failures_per_min, peak=2400.0, ramp_min=12.0),
            MetricRamp("auth", MetricName.cpu, peak=92.0, delay_min=4, ramp_min=12),
            MetricRamp("auth", MetricName.latency_ms, peak=700.0, delay_min=6, ramp_min=10),
        ],
        events=[
            ScenarioEvent("auth", EventType.security, EventSeverity.warning,
                          "elevated failed-login rate from a narrow ASN range", at_min=3),
            ScenarioEvent("auth", EventType.security, EventSeverity.critical,
                          "credential-stuffing pattern detected (distributed source IPs)", at_min=7),
        ],
        root_cause_hint=(
            "A credential-stuffing / brute-force attack is driving auth failures and "
            "CPU on the Auth service from a distributed set of source IPs."
        ),
        recommended_actions=["block_traffic", "scale", "isolate"],
    ),
    "cascading_failure": Scenario(
        key="cascading_failure",
        name="API Gateway saturation -> cascading degradation",
        target_service_id="gateway",
        incident_type=IncidentType.outage,
        severity=Severity.critical,
        primary_metric=MetricName.latency_ms,
        breach_threshold=1500.0,
        ramps=[
            MetricRamp("gateway", MetricName.cpu, peak=97.0, ramp_min=16.0),
            MetricRamp("gateway", MetricName.latency_ms, peak=2600.0, delay_min=3, ramp_min=14),
            MetricRamp("checkout", MetricName.latency_ms, peak=2400.0, delay_min=6, ramp_min=12),
            MetricRamp("catalog", MetricName.latency_ms, peak=1900.0, delay_min=6, ramp_min=12),
            MetricRamp("gateway", MetricName.error_rate, peak=40.0, delay_min=8, ramp_min=10),
        ],
        events=[
            ScenarioEvent("gateway", EventType.kubernetes, EventSeverity.warning,
                          "HPA at max replicas; CPU throttling observed", at_min=6),
        ],
        root_cause_hint=(
            "API Gateway CPU saturates and can no longer scale (HPA maxed), so latency "
            "and errors cascade to every downstream service it fronts."
        ),
        recommended_actions=["scale", "block_traffic", "failover"],
    ),
}


def get_scenario(key: str) -> Scenario | None:
    return SCENARIOS.get(key)


def list_scenarios() -> list[Scenario]:
    return list(SCENARIOS.values())
