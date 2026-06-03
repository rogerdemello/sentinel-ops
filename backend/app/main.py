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
    seed_topology()
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

    from app.api.routes import (
        graph,
        health,
        incidents,
        metrics,
        policy,
        predictions,
        remediation,
        scenarios,
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
    return app


app = create_app()
