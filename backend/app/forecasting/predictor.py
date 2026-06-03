"""Trend-extrapolation forecasting.

Fits a linear trend to a recent metric window and projects when the metric will
cross a critical threshold, yielding an ETA and a calibrated probability. This is
deliberately lightweight (no training pipeline); deep models (TFT/LSTM/Prophet)
can replace :func:`forecast_breach` behind the same signature later.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Default analysis window (number of most-recent points).
_WINDOW = 40


@dataclass
class Forecast:
    breaching: bool
    probability: float  # 0..1
    eta_seconds: int  # seconds until threshold crossed (0 if already over)
    current: float
    slope_per_sec: float
    threshold: float
    r2: float


def _linfit(ts: np.ndarray, ys: np.ndarray) -> tuple[float, float, float]:
    """Return (slope, intercept, r2) for y ~ slope*t + intercept."""
    t0 = ts - ts[0]
    slope, intercept = np.polyfit(t0, ys, 1)
    pred = slope * t0 + intercept
    ss_res = float(np.sum((ys - pred) ** 2))
    ss_tot = float(np.sum((ys - ys.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-9 else 0.0
    return float(slope), float(intercept), max(0.0, r2)


def forecast_breach(
    points: list[tuple[float, float]],  # (ts_seconds, value)
    threshold: float,
    window: int = _WINDOW,
) -> Forecast | None:
    """Forecast whether/when ``value`` crosses ``threshold`` from below.

    Returns None if there's not enough data to say anything.
    """
    if len(points) < 8:
        return None
    pts = points[-window:]
    ts = np.array([p[0] for p in pts], dtype=float)
    ys = np.array([p[1] for p in pts], dtype=float)
    current = float(ys[-1])
    slope, _intercept, r2 = _linfit(ts, ys)

    # Already breached.
    if current >= threshold:
        return Forecast(True, 0.99, 0, current, slope, threshold, r2)

    # Not rising meaningfully -> no imminent breach.
    if slope <= 1e-6:
        return Forecast(False, 0.02, 0, current, slope, threshold, r2)

    eta = (threshold - current) / slope  # seconds
    if eta <= 0:
        return Forecast(True, 0.95, 0, current, slope, threshold, r2)

    # Probability blends: trend fit quality (r2), how close we already are to the
    # threshold, and imminence (closer ETA -> higher probability). Capped at 0.98.
    proximity = current / threshold  # 0..1
    # Imminence: ~1 within a few minutes, decaying over ~90 min.
    imminence = float(np.exp(-eta / (60.0 * 45.0)))
    prob = 0.35 * r2 + 0.30 * proximity + 0.35 * imminence
    prob = float(max(0.05, min(0.98, prob)))

    return Forecast(
        breaching=prob >= 0.5,
        probability=prob,
        eta_seconds=int(eta),
        current=current,
        slope_per_sec=slope,
        threshold=threshold,
        r2=r2,
    )
