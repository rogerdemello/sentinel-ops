"""Remediation planning agent.

Maps a diagnosis to an ordered, human-approvable remediation plan drawn from the
action catalog. Uses scenario-recommended actions as the backbone; an LLM (when
configured) writes the rationale and may reorder.
"""

from __future__ import annotations

import logging

from app.agents.llm.base import LLMError, LLMMessage
from app.agents.llm.router import get_router
from app.models import Incident, RemediationAction, RemediationPlan, Service
from app.remediation.actions import build_action, known_kinds

logger = logging.getLogger(__name__)


def _rationale_llm(incident: Incident, actions: list[RemediationAction]) -> str:
    system = (
        "You are SentinelOps' remediation planner. In 2-3 sentences, justify why the "
        "proposed actions resolve the diagnosed incident and call out the main risk. "
        "Plain text, no JSON."
    )
    action_txt = "\n".join(f"- {a.kind}: {a.description}" for a in actions)
    user = (
        f"Diagnosis: {incident.diagnosis}\nRoot cause: {incident.root_cause}\n\n"
        f"Proposed actions (in order):\n{action_txt}"
    )
    return get_router().complete(
        [LLMMessage("system", system), LLMMessage("user", user)],
        agent="remediation", max_tokens=300,
    ).strip()


def plan_remediation(
    incident: Incident,
    target_service: Service,
    recommended_kinds: list[str],
    now: float,
) -> RemediationPlan:
    kinds = [k for k in recommended_kinds if k in known_kinds()] or ["restart"]
    actions = [a for k in kinds if (a := build_action(k, target_service))]

    rationale = (
        f"These actions directly address the diagnosed root cause on "
        f"{target_service.name}. Apply in order; the first is lowest-risk."
    )
    if get_router().available() and incident.diagnosis:
        try:
            rationale = _rationale_llm(incident, actions)
        except LLMError as exc:
            logger.warning("Remediation rationale LLM failed, using default: %s", exc)

    # High-risk actions force human approval (always on in v1 regardless).
    return RemediationPlan(
        incident_id=incident.id,
        actions=actions,
        rationale=rationale,
        requires_approval=True,
        created_at=now,
    )
