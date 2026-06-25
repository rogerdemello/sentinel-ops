"""Remediation audit log (who/what/when, with executor result)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import tenant_repo
from app.db.repository import Repository

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def list_audit(
    limit: int = Query(100, ge=1, le=2000),
    repo: Repository = Depends(tenant_repo),
) -> dict:
    entries = repo.list_audit(limit=limit)
    return {"audit": [e.model_dump(mode="json") for e in entries]}
