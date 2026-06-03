"""Auto-generated incident postmortems.

Turns an incident's RCA + timeline + impact into a concise, blameless postmortem.
Uses the LLM when configured; otherwise composes a structured Markdown report
from the recorded facts so it always works.
"""

from __future__ import annotations

import logging

from app.agents.llm.base import LLMError, LLMMessage
from app.agents.llm.router import get_router
from app.models import Incident

logger = logging.getLogger(__name__)


def _facts(incident: Incident) -> str:
    lines = [
        f"Title: {incident.title}",
        f"Type/Severity: {incident.incident_type} / {incident.severity}",
        f"Status: {incident.status}",
        f"Root cause: {incident.root_cause}",
        f"Diagnosis: {incident.diagnosis}",
    ]
    if incident.impact:
        lines.append(
            f"Impact: {incident.impact.affected_users:,} users, "
            f"${incident.impact.revenue_at_risk:,.0f} at risk"
        )
    if incident.plan:
        lines.append(
            "Remediation: "
            + ", ".join(a.kind for a in incident.plan.actions)
            + f" (approved_by={incident.plan.approved_by})"
        )
    lines.append("Timeline:")
    for t in incident.timeline:
        lines.append(f"  - [{t.kind}] {t.message}")
    return "\n".join(lines)


def _heuristic(incident: Incident) -> str:
    facts = _facts(incident)
    healed = "autonomously" if incident.auto_remediated else "after operator approval"
    return (
        f"# Postmortem — {incident.title}\n\n"
        f"## Summary\nSentinelOps predicted this {incident.incident_type} on "
        f"{incident.service_id} and remediated it {healed}.\n\n"
        f"## Root Cause\n{incident.root_cause or 'n/a'}\n\n"
        f"## Impact\n"
        + (incident.impact.headline if incident.impact else "n/a")
        + "\n\n## What Happened\n```\n" + facts + "\n```\n\n"
        f"## Follow-ups\n- Add a guardrail/alert for the lead signal "
        f"({incident.lead_metric}).\n- Review capacity/limits on {incident.service_id}.\n"
    )


def generate_postmortem(incident: Incident) -> str:
    if get_router().available():
        try:
            system = (
                "You are an SRE writing a concise, blameless postmortem in Markdown with "
                "sections: Summary, Root Cause, Impact, Timeline, Follow-up actions. "
                "Be specific and use only the facts provided."
            )
            text = get_router().complete(
                [LLMMessage("system", system), LLMMessage("user", _facts(incident))],
                agent="postmortem", max_tokens=800,
            ).strip()
            if text:
                return text
        except LLMError as exc:
            logger.warning("Postmortem LLM failed, using heuristic: %s", exc)
    return _heuristic(incident)
