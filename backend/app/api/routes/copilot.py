"""Natural-language copilot endpoint."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.copilot import answer

router = APIRouter(prefix="/api/copilot", tags=["copilot"])


class Question(BaseModel):
    question: str


@router.post("")
def ask(body: Question) -> dict:
    return {"answer": answer(body.question)}
