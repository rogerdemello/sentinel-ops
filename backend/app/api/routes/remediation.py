"""Remediation approval endpoints (human-in-the-loop)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.deps import tenant_repo
from app.clock import get_clock
from app.db.repository import Repository
from app.remediation import workflow

router = APIRouter(prefix="/api/remediation", tags=["remediation"])


@router.post("/{incident_id}/approve")
def approve(
    incident_id: str, request: Request, repo: Repository = Depends(tenant_repo)
) -> dict:
    # Role is assigned by the auth middleware from the authenticating key — a
    # client cannot escalate by sending its own role header.
    role = getattr(request.state, "role", "operator")
    try:
        inc = workflow.approve_and_execute(
            incident_id, get_clock().now(), actor="human", role=role, repo=repo
        )
    except workflow.WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"incident": inc.model_dump(mode="json")}


@router.post("/{incident_id}/reject")
def reject(incident_id: str, repo: Repository = Depends(tenant_repo)) -> dict:
    try:
        inc = workflow.reject(incident_id, get_clock().now(), repo=repo)
    except workflow.WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"incident": inc.model_dump(mode="json")}
