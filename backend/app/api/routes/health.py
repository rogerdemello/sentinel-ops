"""Health + capability reporting."""

from __future__ import annotations

from fastapi import APIRouter

from app.clock import get_clock
from app.config import get_settings
from app.db.repository import get_repository

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    repo = get_repository()
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "sim_time": get_clock().now(),
        "services": len(repo.list_services()),
        "capabilities": {
            "supabase": settings.persistence_enabled,
            "azure_openai": settings.azure_enabled,
            "gemini": settings.gemini_enabled,
            "llm": settings.any_llm_enabled,
        },
    }
