"""Core domain models shared across the platform.

Telemetry-specific models live in ``app.telemetry.schema``.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def new_id() -> str:
    return uuid.uuid4().hex


class ServiceKind(str, Enum):
    edge = "edge"  # user-facing entrypoint
    frontend = "frontend"
    gateway = "gateway"
    service = "service"
    datastore = "datastore"
    cache = "cache"
    queue = "queue"


class Service(BaseModel):
    id: str
    name: str
    kind: ServiceKind
    tier: int = 0  # depth from the user (0 = user/edge)
    region: str = "us-east-1"
    # business weights used by the impact estimator
    users: int = 0  # users directly served by this node
    revenue_per_min: float = 0.0  # $ throughput attributable to this node


class Dependency(BaseModel):
    source_id: str  # the upstream caller
    target_id: str  # the downstream dependency it calls
    kind: str = "sync"  # sync | async
    criticality: float = 1.0  # 0..1, how essential the target is to the source


class IncidentType(str, Enum):
    outage = "outage"
    degradation = "degradation"
    infra_failure = "infra_failure"
    security = "security"


class Prediction(BaseModel):
    id: str = Field(default_factory=new_id)
    service_id: str
    incident_type: IncidentType
    probability: float  # 0..1
    eta_seconds: int  # predicted seconds until threshold breach
    metric: str
    summary: str
    features: dict[str, Any] = Field(default_factory=dict)
    created_at: float  # simulated epoch seconds


class IncidentStatus(str, Enum):
    predicted = "predicted"
    active = "active"
    mitigating = "mitigating"
    resolved = "resolved"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AgentFinding(BaseModel):
    agent: str  # infra | application | security
    summary: str
    evidence: list[str] = Field(default_factory=list)
    confidence: float = 0.0  # 0..1
    suspected_root_cause: str | None = None


class ImpactAssessment(BaseModel):
    affected_service_ids: list[str] = Field(default_factory=list)
    affected_users: int = 0
    revenue_at_risk: float = 0.0
    severity: Severity = Severity.low
    headline: str = ""


class RemediationStatus(str, Enum):
    proposed = "proposed"
    approved = "approved"
    rejected = "rejected"
    executing = "executing"
    executed = "executed"


class RemediationAction(BaseModel):
    id: str = Field(default_factory=new_id)
    kind: str  # restart | scale | rollback | block_traffic | isolate | failover
    target_service_id: str
    description: str
    risk: Severity = Severity.low
    params: dict[str, Any] = Field(default_factory=dict)


class RemediationPlan(BaseModel):
    id: str = Field(default_factory=new_id)
    incident_id: str
    actions: list[RemediationAction] = Field(default_factory=list)
    rationale: str = ""
    status: RemediationStatus = RemediationStatus.proposed
    requires_approval: bool = True
    approved_by: str | None = None  # "human" | "autonomous"
    created_at: float
    decided_at: float | None = None

    @property
    def max_risk(self) -> Severity:
        order = [Severity.low, Severity.medium, Severity.high, Severity.critical]
        worst = Severity.low
        for a in self.actions:
            if order.index(a.risk) > order.index(worst):
                worst = a.risk
        return worst


class TimelineEntry(BaseModel):
    at: float  # simulated epoch seconds
    kind: str  # detected | rca | impact | planned | approved | auto_healed | rejected | breached | resolved
    message: str


class Incident(BaseModel):
    id: str = Field(default_factory=new_id)
    service_id: str
    incident_type: IncidentType
    status: IncidentStatus = IncidentStatus.predicted
    severity: Severity = Severity.medium
    title: str = ""
    scenario_key: str | None = None  # which synthetic scenario produced it
    probability: float = 0.0
    eta_seconds: int = 0
    lead_metric: str | None = None
    lead_threshold: float | None = None
    root_cause: str | None = None
    diagnosis: str | None = None
    findings: list[AgentFinding] = Field(default_factory=list)
    impact: ImpactAssessment | None = None
    plan: RemediationPlan | None = None
    timeline: list[TimelineEntry] = Field(default_factory=list)
    auto_remediated: bool = False
    created_at: float = 0.0
    updated_at: float = 0.0

    def log(self, at: float, kind: str, message: str) -> None:
        self.timeline.append(TimelineEntry(at=at, kind=kind, message=message))
