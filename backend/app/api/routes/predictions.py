"""Prediction endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import tenant_repo
from app.db.repository import Repository

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.get("")
def list_predictions(repo: Repository = Depends(tenant_repo)) -> dict:
    preds = repo.list_predictions()
    return {"predictions": [p.model_dump(mode="json") for p in preds]}
