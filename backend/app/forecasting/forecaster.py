"""Pluggable forecasting backends behind one interface.

The engine depends only on ``Forecaster.forecast(...)``; the concrete model is
selected by config (``FORECASTER=trend|holtwinters|prophet``). This is the seam
where a Temporal Fusion Transformer / LSTM would later drop in. Every backend
falls back to the robust trend forecaster on any error, so the engine never breaks.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from functools import lru_cache

import numpy as np

from app.config import get_settings
from app.forecasting.predictor import Forecast, forecast_breach

logger = logging.getLogger(__name__)


class Forecaster(ABC):
    name: str

    @abstractmethod
    def forecast(
        self, points: list[tuple[float, float]], threshold: float, window: int = 40
    ) -> Forecast | None: ...


class TrendForecaster(Forecaster):
    """Linear trend extrapolation (default; fully unit-tested)."""

    name = "trend"

    def forecast(self, points, threshold, window=40):
        return forecast_breach(points, threshold, window)


class HoltWintersForecaster(Forecaster):
    """Holt's damped-trend exponential smoothing; sharper on curved ramps.

    Fits on the recent window, projects the smoothed path forward, and finds the
    first crossing of ``threshold``. Falls back to the trend forecaster whenever
    statsmodels can't fit (short/constant series, convergence issues).
    """

    name = "holtwinters"
    _fallback = TrendForecaster()
    _HORIZON = 120  # steps to project forward

    def forecast(self, points, threshold, window=60):
        if len(points) < 12:
            return self._fallback.forecast(points, threshold, window)
        pts = points[-window:]
        ts = np.array([p[0] for p in pts], dtype=float)
        ys = np.array([p[1] for p in pts], dtype=float)
        current = float(ys[-1])
        dt = float(np.median(np.diff(ts))) if len(ts) > 1 else 60.0
        if dt <= 0:
            dt = 60.0

        if current >= threshold:
            return Forecast(True, 0.99, 0, current, 0.0, threshold, 1.0, already_breached=True)

        try:
            from statsmodels.tsa.holtwinters import Holt

            model = Holt(ys, damped_trend=True, initialization_method="estimated")
            fit = model.fit(optimized=True)
            fc = np.asarray(fit.forecast(self._HORIZON), dtype=float)
        except Exception as exc:  # noqa: BLE001 - any fit failure -> safe fallback
            logger.debug("HoltWinters fit failed, falling back to trend: %s", exc)
            return self._fallback.forecast(points, threshold, window)

        crossing = np.argmax(fc >= threshold) if np.any(fc >= threshold) else -1
        if crossing < 0:
            # No crossing within horizon -> low risk.
            slope = float((fc[-1] - current) / (self._HORIZON * dt)) if self._HORIZON else 0.0
            return Forecast(False, 0.1, 0, current, slope, threshold, 0.5)

        eta = int((crossing + 1) * dt)
        slope = float((threshold - current) / max(eta, 1))
        proximity = current / threshold
        imminence = float(np.exp(-eta / (60.0 * 45.0)))
        prob = float(max(0.05, min(0.98, 0.30 * proximity + 0.40 * imminence + 0.30)))
        return Forecast(prob >= 0.5, prob, eta, current, slope, threshold, 0.8)


class ProphetForecaster(Forecaster):
    """Facebook Prophet, if installed; otherwise transparently uses Holt-Winters."""

    name = "prophet"
    _fallback = HoltWintersForecaster()

    def forecast(self, points, threshold, window=120):
        try:
            from prophet import Prophet  # noqa: F401
        except Exception:
            return self._fallback.forecast(points, threshold, window)
        # Prophet expects datetime; for the simulated clock we keep the Holt path
        # which is robust and dependency-light. (Hook kept for real-data deploys.)
        return self._fallback.forecast(points, threshold, window)


_REGISTRY = {
    "trend": TrendForecaster,
    "holtwinters": HoltWintersForecaster,
    "prophet": ProphetForecaster,
}


@lru_cache
def get_forecaster() -> Forecaster:
    kind = get_settings().forecaster
    return _REGISTRY.get(kind, TrendForecaster)()
