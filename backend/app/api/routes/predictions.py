"""Prediction endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.db.repository import get_repository

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.get("")
def list_predictions() -> dict:
    preds = get_repository().list_predictions()
    return {"predictions": [p.model_dump(mode="json") for p in preds]}
