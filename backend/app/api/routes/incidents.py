"""Incident endpoints (includes RCA, impact, blast radius, plan)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.db.repository import get_repository
from app.graph.blast_radius import compute_blast_radius
from app.graph.service import get_graph

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("")
def list_incidents() -> dict:
    incs = get_repository().list_incidents()
    return {"incidents": [i.model_dump(mode="json") for i in incs]}


@router.get("/{incident_id}")
def get_incident(incident_id: str) -> dict:
    inc = get_repository().get_incident(incident_id)
    if inc is None:
        raise HTTPException(status_code=404, detail="incident not found")
    blast = compute_blast_radius(inc.service_id, get_graph())
    return {
        "incident": inc.model_dump(mode="json"),
        "blast_radius": [
            {"service_id": b.service_id, "criticality": b.criticality} for b in blast
        ],
    }
