"""Simulated clock.

The platform reasons over *simulated* time so demos can compress hours of metric
history into seconds. ``now()`` returns simulated epoch seconds; the simulator
advances it each tick.
"""

from __future__ import annotations

from functools import lru_cache


class SimClock:
    # Start at a fixed, deterministic instant (2026-06-03T12:00:00Z) so runs are
    # reproducible (Date.now() / wall-clock are deliberately avoided).
    _EPOCH_START = 1_780_488_000.0

    def __init__(self) -> None:
        self._t = self._EPOCH_START

    def now(self) -> float:
        return self._t

    def advance(self, seconds: float) -> float:
        self._t += seconds
        return self._t


@lru_cache
def get_clock() -> SimClock:
    return SimClock()
