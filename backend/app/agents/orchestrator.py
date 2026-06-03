"""Orchestrator: runs domain agents and synthesizes a unified diagnosis."""

from __future__ import annotations

import logging

from app.agents.context import DiagnosisContext
from app.agents.domain_agents import run_all_agents
from app.agents.llm.base import LLMError
from app.agents.llm.router import get_router
from app.models import AgentFinding

logger = logging.getLogger(__name__)


def _synthesize_heuristic(ctx: DiagnosisContext, findings: list[AgentFinding]) -> tuple[str, str]:
    top = max(findings, key=lambda f: f.confidence)
    root = top.suspected_root_cause or ctx.scenario_hint or (
        f"Degradation originating at {ctx.failing_service.name}"
    )
    contributing = [f.agent for f in findings if f.confidence >= 0.5]
    diagnosis = (
        f"Root cause: {root}\n\n"
        f"The {ctx.incident_type.value} is centered on {ctx.failing_service.name}. "
        f"Strongest signal from the {top.agent} domain (confidence {top.confidence:.0%}). "
        + (f"Contributing domains: {', '.join(contributing)}. " if contributing else "")
        + (f"Predicted blast radius: {', '.join(ctx.impacted_service_ids)}."
           if ctx.impacted_service_ids else "")
    )
    return root, diagnosis


def _synthesize_llm(ctx: DiagnosisContext, findings: list[AgentFinding]) -> tuple[str, str]:
    system = (
        "You are the lead incident commander on SentinelOps. Synthesize the domain "
        "agents' findings into a single authoritative diagnosis. Respond as JSON: "
        "{root_cause: str, diagnosis: str}."
    )
    findings_txt = "\n".join(
        f"- [{f.agent}] (conf {f.confidence:.0%}) {f.summary}" for f in findings
    )
    user = (
        f"Incident: {ctx.incident_type.value} at {ctx.failing_service.name}.\n"
        f"Impacted: {', '.join(ctx.impacted_service_ids) or 'n/a'}.\n\n"
        f"Agent findings:\n{findings_txt}"
    )
    data = get_router().complete_json(system, user, agent="orchestrator", max_tokens=600)
    return str(data.get("root_cause", "")), str(data.get("diagnosis", ""))


def diagnose(ctx: DiagnosisContext) -> tuple[list[AgentFinding], str, str]:
    """Return (findings, root_cause, diagnosis)."""
    findings = run_all_agents(ctx)
    if get_router().available():
        try:
            root, diagnosis = _synthesize_llm(ctx, findings)
            if root and diagnosis:
                return findings, root, diagnosis
        except LLMError as exc:
            logger.warning("Orchestrator LLM synthesis failed, using heuristic: %s", exc)
    root, diagnosis = _synthesize_heuristic(ctx, findings)
    return findings, root, diagnosis
