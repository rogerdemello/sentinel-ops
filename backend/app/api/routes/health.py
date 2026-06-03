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
            "neo4j": settings.neo4j_enabled,
            "telemetry_source": settings.telemetry_source,
            "forecaster": settings.forecaster,
            "remediation_executor": settings.remediation_executor,
            "alerting": bool(
                settings.slack_webhook_url
                or settings.pagerduty_routing_key
                or settings.alert_webhook_url
            ),
            "auth": bool(settings.api_key),
        },
    }
