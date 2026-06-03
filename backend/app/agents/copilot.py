"""Natural-language operations copilot.

Answers free-form questions ("why is checkout slow?", "what's most at risk?")
grounded in the live platform state — metrics, predictions, incidents, topology.
Uses the LLM when configured; otherwise returns a structured summary so it always
responds.
"""

from __future__ import annotations

import logging

from app.agents.llm.base import LLMError, LLMMessage
from app.agents.llm.router import get_router
from app.db.repository import get_repository
from app.models import IncidentStatus

logger = logging.getLogger(__name__)


def _state_context() -> str:
    repo = get_repository()
    incidents = [i for i in repo.list_incidents() if i.status != IncidentStatus.resolved]
    preds = repo.list_predictions()[:5]
    lines = ["Active incidents:"]
    if incidents:
        for i in incidents:
            lines.append(
                f"  - {i.title} (sev={i.severity}, {int(i.probability * 100)}%) "
                f"root_cause={i.root_cause}"
                + (f", impact={i.impact.headline}" if i.impact else "")
            )
    else:
        lines.append("  (none)")
    lines.append("Top predictions:")
    lines += [f"  - {p.summary}" for p in preds] or ["  (none)"]
    lines.append("Recent events:")
    lines += [f"  - [{e.severity}] {e.service_id}: {e.message}"
              for e in repo.list_events(limit=8)]
    return "\n".join(lines)


def _heuristic(question: str, ctx: str) -> str:
    return (
        "LLM not configured — here is the current operational state:\n\n" + ctx
    )


def answer(question: str) -> str:
    ctx = _state_context()
    if get_router().available():
        try:
            system = (
                "You are SentinelOps' operations copilot. Answer the user's question using "
                "ONLY the live platform state provided. Be concise, specific, and actionable. "
                "If the state doesn't contain the answer, say so."
            )
            user = f"Live state:\n{ctx}\n\nQuestion: {question}"
            out = get_router().complete(
                [LLMMessage("system", system), LLMMessage("user", user)],
                agent="copilot", max_tokens=500,
            ).strip()
            if out:
                return out
        except LLMError as exc:
            logger.warning("Copilot LLM failed, using heuristic: %s", exc)
    return _heuristic(question, ctx)
