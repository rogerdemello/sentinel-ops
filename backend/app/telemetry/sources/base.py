"""TelemetrySource contract.

A source produces the metrics + events for one tick. The simulator records them
and runs the engine — it doesn't care whether they came from the synthetic
generator, a Prometheus scrape, or pushed OTLP data.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.telemetry.schema import MetricPoint, TelemetryEvent


class TelemetrySource(ABC):
    name: str

    @abstractmethod
    def collect(self, now: float) -> tuple[list[MetricPoint], list[TelemetryEvent]]:
        """Return (metrics, events) observed for this tick."""
