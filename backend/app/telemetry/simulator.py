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
from app.db.repository import get_repository
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
        while self._running:
            try:
                self.tick()
            except Exception:  # noqa: BLE001 - never let the loop die
                logger.exception("Simulator tick failed")
            await asyncio.sleep(interval)

    def tick(self) -> None:
        settings = get_settings()
        repo = get_repository()

        now = get_clock().advance(settings.sim_minutes_per_tick * 60.0)

        metrics, events = get_source().collect(now)
        for m in metrics:
            repo.record_metric(m)
        for e in events:
            repo.record_event(e)

        run_cycle(now)
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
