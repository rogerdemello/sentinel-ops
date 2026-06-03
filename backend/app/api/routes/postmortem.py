"""On-demand AI postmortem generation."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.agents.postmortem import generate_postmortem
from app.db.repository import get_repository

router = APIRouter(prefix="/api/postmortem", tags=["postmortem"])


@router.post("/{incident_id}")
def create_postmortem(incident_id: str) -> dict:
    repo = get_repository()
    incident = repo.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    incident.postmortem = generate_postmortem(incident)
    repo.upsert_incident(incident)
    return {"incident_id": incident_id, "postmortem": incident.postmortem}
