"""Self-healing policy endpoints (toggle autonomous mode at runtime)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.policy import get_policy

router = APIRouter(prefix="/api/policy", tags=["policy"])


class PolicyUpdate(BaseModel):
    auto_remediate: bool | None = None
    max_auto_risk: str | None = None  # low | medium | high | critical


@router.get("")
def read_policy() -> dict:
    return get_policy().as_dict()


@router.put("")
def update_policy(body: PolicyUpdate) -> dict:
    get_policy().update(
        auto_remediate=body.auto_remediate, max_auto_risk=body.max_auto_risk
    )
    return get_policy().as_dict()
