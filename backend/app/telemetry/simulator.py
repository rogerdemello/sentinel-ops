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
from app.telemetry.generator import generate_value, metrics_for
from app.telemetry.scenario_manager import get_scenario_manager
from app.telemetry.schema import MetricPoint, TelemetryEvent
from app.telemetry.scenarios import Scenario

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
        clock = get_clock()
        repo = get_repository()
        sm = get_scenario_manager()

        now = clock.advance(settings.sim_minutes_per_tick * 60.0)
        active = sm.active(now)

        for service in repo.list_services():
            for metric in metrics_for(service):
                value = generate_value(service, metric, now, active)
                repo.record_metric(
                    MetricPoint(service_id=service.id, name=metric, value=value, ts=now)
                )

        self._emit_scenario_events(now)
        run_cycle(now)
        self.ticks += 1

    def _emit_scenario_events(self, now: float) -> None:
        repo = get_repository()
        for rec in get_scenario_manager().active_records():
            elapsed_min = (now - rec.triggered_at) / 60.0
            scenario: Scenario = rec.scenario
            for idx, ev in enumerate(scenario.events):
                if idx in rec.emitted_event_ids:
                    continue
                if elapsed_min >= ev.at_min:
                    repo.record_event(
                        TelemetryEvent(
                            service_id=ev.service_id,
                            type=ev.type,
                            severity=ev.severity,
                            message=ev.message,
                            ts=now,
                        )
                    )
                    rec.emitted_event_ids.add(idx)

    def trigger(self, key: str):
        now = get_clock().now()
        return get_scenario_manager().trigger(key, now)


_simulator: Simulator | None = None


def get_simulator() -> Simulator:
    global _simulator
    if _simulator is None:
        _simulator = Simulator()
    return _simulator
