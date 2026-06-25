"""Select the active telemetry source from config."""

from __future__ import annotations

import logging
from functools import lru_cache

from app.config import get_settings
from app.telemetry.sources.base import TelemetrySource
from app.telemetry.sources.synthetic import SyntheticSource

logger = logging.getLogger(__name__)


@lru_cache
def get_source() -> TelemetrySource:
    kind = get_settings().telemetry_source
    if kind == "prometheus":
        try:
            from app.telemetry.sources.prometheus import PrometheusSource

            logger.info("Using Prometheus telemetry source")
            return PrometheusSource()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Prometheus source unavailable (%s); using synthetic", exc)
        return SyntheticSource()
    if kind == "system":
        try:
            from app.telemetry.sources.system import SystemSource

            logger.info("Using real host telemetry source (psutil)")
            return SystemSource()
        except Exception as exc:  # noqa: BLE001
            logger.warning("System source unavailable (%s); using synthetic", exc)
        return SyntheticSource()
    return SyntheticSource()
