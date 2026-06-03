"""Tracks which scenarios are currently active and their elapsed time.

Shared by the simulator (to apply ramps + emit events) and the engine (to label
incidents and know which scenario a remediation should clear).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from app.telemetry.scenarios import Scenario, get_scenario


@dataclass
class ActiveScenario:
    scenario: Scenario
    triggered_at: float  # sim epoch seconds
    emitted_event_ids: set[int] = field(default_factory=set)


class ScenarioManager:
    def __init__(self) -> None:
        self._active: dict[str, ActiveScenario] = {}

    def trigger(self, key: str, now: float) -> Scenario | None:
        scenario = get_scenario(key)
        if scenario is None:
            return None
        self._active[key] = ActiveScenario(scenario=scenario, triggered_at=now)
        return scenario

    def clear(self, key: str) -> None:
        self._active.pop(key, None)

    def clear_all(self) -> None:
        self._active.clear()

    def is_active(self, key: str) -> bool:
        return key in self._active

    def active(self, now: float) -> list[tuple[Scenario, float]]:
        """List of (scenario, elapsed_minutes)."""
        return [
            (a.scenario, (now - a.triggered_at) / 60.0)
            for a in self._active.values()
        ]

    def active_records(self) -> list[ActiveScenario]:
        return list(self._active.values())

    def scenario_for_service(self, service_id: str) -> ActiveScenario | None:
        for a in self._active.values():
            if a.scenario.target_service_id == service_id:
                return a
        return None


@lru_cache
def get_scenario_manager() -> ScenarioManager:
    return ScenarioManager()
