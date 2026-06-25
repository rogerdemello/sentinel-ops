"""Incident endpoints (includes RCA, impact, blast radius, plan)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import tenant_repo
from app.db.repository import Repository
from app.graph.blast_radius import compute_blast_radius
from app.graph.service import get_graph

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("")
def list_incidents(repo: Repository = Depends(tenant_repo)) -> dict:
    incs = repo.list_incidents()
    return {"incidents": [i.model_dump(mode="json") for i in incs]}


@router.get("/{incident_id}")
def get_incident(incident_id: str, repo: Repository = Depends(tenant_repo)) -> dict:
    inc = repo.get_incident(incident_id)
    if inc is None:
        raise HTTPException(status_code=404, detail="incident not found")
    blast = compute_blast_radius(inc.service_id, get_graph())
    return {
        "incident": inc.model_dump(mode="json"),
        "blast_radius": [
            {"service_id": b.service_id, "criticality": b.criticality} for b in blast
        ],
    }
