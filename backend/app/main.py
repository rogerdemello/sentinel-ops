"""FastAPI application entrypoint.

Wires routers, CORS, and the simulator background loop. Seeds the demo topology
on startup. Everything runs with zero external setup; Supabase / LLM providers
are optional enhancements detected at runtime.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.bootstrap import seed_topology
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentinelops")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Warm the psycopg import in the main thread BEFORE any background writer/RAG
    # thread starts, to avoid a concurrent-import deadlock on psycopg.types.json.
    if settings.db_persist_enabled:
        try:
            import psycopg  # noqa: F401
            from psycopg.types.json import Json  # noqa: F401
        except Exception:  # noqa: BLE001
            pass

    seed_topology()
    if settings.rag_enabled:
        from app.memory.store import ensure_schema

        ensure_schema()
    logger.info("SentinelOps backend ready (env=%s)", settings.environment)

    # Simulator is started lazily here once M3 wires it in.
    from app.telemetry.simulator import get_simulator

    sim = get_simulator()
    if settings.sim_autostart:
        await sim.start()
    try:
        yield
    finally:
        await sim.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def api_key_auth(request, call_next):
        """Optional API-key gate. Active only when API_KEY is configured; /health
        and docs stay open. Also stashes X-Tenant-Id for tenant-scoped features."""
        key = get_settings().api_key
        path = request.url.path
        request.state.tenant_id = request.headers.get("X-Tenant-Id", "default")
        if key and path.startswith("/api"):
            provided = request.headers.get("X-API-Key") or (
                request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            )
            if provided != key:
                from fastapi.responses import JSONResponse

                return JSONResponse(status_code=401, content={"detail": "unauthorized"})
        return await call_next(request)

    from app.api.routes import (
        audit,
        copilot,
        evaluation,
        graph,
        health,
        incidents,
        ingest,
        metrics,
        policy,
        postmortem,
        predictions,
        remediation,
        scenarios,
        stream,
        telemetry,
    )

    app.include_router(health.router)
    app.include_router(graph.router)
    app.include_router(telemetry.router)
    app.include_router(predictions.router)
    app.include_router(incidents.router)
    app.include_router(scenarios.router)
    app.include_router(remediation.router)
    app.include_router(policy.router)
    app.include_router(metrics.router)
    app.include_router(ingest.router)
    app.include_router(audit.router)
    app.include_router(postmortem.router)
    app.include_router(stream.router)
    app.include_router(copilot.router)
    app.include_router(evaluation.router)
    return app


app = create_app()
