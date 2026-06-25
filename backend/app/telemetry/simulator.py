"""Simulation loop.

Each tick advances simulated time, generates baseline + scenario-perturbed
telemetry for every service, emits scenario events, then runs the analysis engine.
Runs as an asyncio background task started in the app lifespan.
"""

from __future__ import annotations

import asyncio
import logging

from app.clock import get_clock
from app.config import get_settings
from app.db.repository import DEFAULT_TENANT, get_repository, list_tenants
from app.engine import run_cycle
from app.telemetry.scenario_manager import get_scenario_manager
from app.telemetry.sources.factory import get_source

logger = logging.getLogger(__name__)


class Simulator:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running = False
        self.ticks = 0

    @property
    def running(self) -> bool:
        return self._running

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Simulator started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        interval = get_settings().sim_tick_seconds
        loop = asyncio.get_running_loop()
        while self._running:
            try:
                # Offload the tick to a worker thread: the RCA/impact pipeline makes
                # blocking LLM/DB calls and must not stall the event loop (WebSocket
                # streaming, HTTP handlers) while an incident is being analyzed.
                await loop.run_in_executor(None, self.tick)
            except Exception:  # noqa: BLE001 - never let the loop die
                logger.exception("Simulator tick failed")
            await asyncio.sleep(interval)

    def tick(self) -> None:
        settings = get_settings()
        repo = get_repository()

        now = get_clock().advance(settings.sim_minutes_per_tick * 60.0)

        # Default tenant: driven by the configured pull source (real host / synthetic).
        metrics, events = get_source().collect(now)
        for m in metrics:
            repo.record_metric(m)
        for e in events:
            repo.record_event(e)
        run_cycle(now, repo)

        # Other tenants: driven purely by their own pushed telemetry (/api/ingest).
        # Each gets an isolated analysis cycle over its own store.
        for tid in list_tenants():
            if tid == DEFAULT_TENANT:
                continue
            run_cycle(now, get_repository(tid))

        self.ticks += 1

    def trigger(self, key: str):
        now = get_clock().now()
        return get_scenario_manager().trigger(key, now)


_simulator: Simulator | None = None


def get_simulator() -> Simulator:
    global _simulator
    if _simulator is None:
        _simulator = Simulator()
    return _simulator
