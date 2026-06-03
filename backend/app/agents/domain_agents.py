"""Domain RCA agents: Infrastructure, Application, Security.

Each agent inspects its slice of telemetry and returns an ``AgentFinding``. When
an LLM provider is configured it produces the narrative; otherwise a deterministic
heuristic (threshold rules + scenario hint) yields a solid finding so the demo
works fully offline.
"""

from __future__ import annotations

import logging

from app.agents.context import DiagnosisContext
from app.agents.llm.base import LLMError
from app.agents.llm.router import get_router
from app.models import AgentFinding
from app.telemetry.schema import MetricName

logger = logging.getLogger(__name__)

_AGENT_SPECS = {
    "infrastructure": {
        "metrics": [MetricName.cpu.value, MetricName.memory.value,
                    MetricName.disk.value, MetricName.db_pool_used_pct.value,
                    MetricName.latency_ms.value],
        "role": "an infrastructure SRE analyzing CPU, memory, disk, DB pools and saturation",
    },
    "application": {
        "metrics": [MetricName.error_rate.value, MetricName.latency_ms.value,
                    MetricName.requests_per_sec.value],
        "role": "an application engineer analyzing error rates, latency, deploys and dependencies",
    },
    "security": {
        "metrics": [MetricName.auth_failures_per_min.value, MetricName.cpu.value],
        "role": "a security analyst analyzing auth failures, access patterns and threat indicators",
    },
}


# Which domain "owns" each metric — used to attribute a predicted incident to an
# agent even before absolute thresholds are crossed (predictions fire on trend).
_METRIC_DOMAIN = {
    MetricName.cpu.value: "infrastructure",
    MetricName.memory.value: "infrastructure",
    MetricName.disk.value: "infrastructure",
    MetricName.db_pool_used_pct.value: "infrastructure",
    MetricName.latency_ms.value: "application",
    MetricName.error_rate.value: "application",
    MetricName.requests_per_sec.value: "application",
    MetricName.auth_failures_per_min.value: "security",
}


def _heuristic_finding(agent: str, ctx: DiagnosisContext) -> AgentFinding:
    fm = _AGENT_SPECS[agent]["metrics"]
    fs = ctx.failing_service
    fmetrics = ctx.metrics.get(fs.id, {})
    evidence: list[str] = []
    for m in fm:
        if m in fmetrics:
            evidence.append(f"{fs.id}.{m} = {fmetrics[m]:.1f}")

    # Relevance: this agent owns the lead (trending) metric, OR its domain's
    # absolute thresholds are already breached.
    owns_lead = _METRIC_DOMAIN.get(ctx.lead_metric or "") == agent
    sec_active = fmetrics.get(MetricName.auth_failures_per_min.value, 0) > 100
    infra_active = (
        fmetrics.get(MetricName.cpu.value, 0) > 80
        or fmetrics.get(MetricName.memory.value, 0) > 85
        or fmetrics.get(MetricName.db_pool_used_pct.value, 0) > 80
    )
    app_active = fmetrics.get(MetricName.error_rate.value, 0) > 5

    threshold_active = {
        "infrastructure": infra_active,
        "application": app_active,
        "security": sec_active,
    }[agent]
    relevant = owns_lead or threshold_active

    if relevant and ctx.scenario_hint:
        summary = ctx.scenario_hint
        confidence = 0.82
        root = ctx.scenario_hint
    elif relevant:
        summary = (
            f"{fs.name}: anomalous {agent} signals detected ("
            + ", ".join(evidence[:3]) + ")."
        )
        confidence = 0.6
        root = f"{agent} saturation on {fs.name}"
    else:
        summary = f"No strong {agent} anomaly attributable to {fs.name}."
        confidence = 0.15
        root = None
    return AgentFinding(
        agent=agent, summary=summary, evidence=evidence,
        confidence=confidence, suspected_root_cause=root,
    )


def _llm_finding(agent: str, ctx: DiagnosisContext) -> AgentFinding:
    spec = _AGENT_SPECS[agent]
    system = (
        f"You are {spec['role']} on the SentinelOps autonomous operations platform. "
        "Given live telemetry, produce a concise root-cause hypothesis for your domain. "
        "Respond as JSON: {summary, evidence:[..], confidence:0..1, suspected_root_cause}."
    )
    user = (
        f"Predicted incident: {ctx.incident_type.value} originating at "
        f"'{ctx.failing_service.name}' ({ctx.failing_service.id}).\n"
        f"Impacted services: {', '.join(ctx.impacted_service_ids) or 'none yet'}.\n\n"
        f"Relevant metrics:\n{ctx.metrics_table(spec['metrics'])}\n\n"
        f"Recent events:\n" + "\n".join(f"  - {e}" for e in ctx.recent_events[:8])
    )
    data = get_router().complete_json(system, user, agent=agent, max_tokens=500)
    return AgentFinding(
        agent=agent,
        summary=str(data.get("summary", "")),
        evidence=[str(x) for x in data.get("evidence", [])][:6],
        confidence=float(data.get("confidence", 0.5)),
        suspected_root_cause=data.get("suspected_root_cause"),
    )


def run_agent(agent: str, ctx: DiagnosisContext) -> AgentFinding:
    if get_router().available():
        try:
            return _llm_finding(agent, ctx)
        except LLMError as exc:
            logger.warning("Agent %s LLM failed, using heuristic: %s", agent, exc)
    return _heuristic_finding(agent, ctx)


def run_all_agents(ctx: DiagnosisContext) -> list[AgentFinding]:
    return [run_agent(a, ctx) for a in ("infrastructure", "application", "security")]
