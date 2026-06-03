"""Remediation approval endpoints (human-in-the-loop)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.clock import get_clock
from app.remediation import workflow

router = APIRouter(prefix="/api/remediation", tags=["remediation"])


@router.post("/{incident_id}/approve")
def approve(incident_id: str) -> dict:
    try:
        inc = workflow.approve_and_execute(incident_id, get_clock().now())
    except workflow.WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"incident": inc.model_dump(mode="json")}


@router.post("/{incident_id}/reject")
def reject(incident_id: str) -> dict:
    try:
        inc = workflow.reject(incident_id, get_clock().now())
    except workflow.WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"incident": inc.model_dump(mode="json")}
