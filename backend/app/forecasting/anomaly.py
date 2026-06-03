"""Anomaly detection.

Two complementary signals:
- ``robust_zscore``: how far the latest value sits from the recent window
  (median/MAD), resistant to outliers. Cheap, per-metric.
- ``isolation_forest_score``: multivariate outlier score over a feature window,
  used to corroborate the per-metric signal.
"""

from __future__ import annotations

import math

import numpy as np


def robust_zscore(values: list[float]) -> float:
    """Robust z-score of the latest value vs the window. 0 if insufficient data."""
    if len(values) < 6:
        return 0.0
    arr = np.asarray(values, dtype=float)
    window, latest = arr[:-1], arr[-1]
    median = float(np.median(window))
    mad = float(np.median(np.abs(window - median)))
    if mad < 1e-9:
        std = float(window.std())
        if std < 1e-9:
            # Zero-variance baseline: any deviation is a strong anomaly.
            diff = latest - median
            return 0.0 if abs(diff) < 1e-9 else math.copysign(10.0, diff)
        return float((latest - window.mean()) / std)
    # 1.4826 scales MAD to be a consistent estimator of std for normal data.
    return float((latest - median) / (1.4826 * mad))


def isolation_forest_score(feature_window: list[list[float]]) -> float:
    """Outlier score (0..1, higher = more anomalous) for the most recent row.

    Returns 0 if there isn't enough data to fit. Lazy-imports sklearn.
    """
    if len(feature_window) < 12:
        return 0.0
    try:
        from sklearn.ensemble import IsolationForest
    except Exception:  # pragma: no cover
        return 0.0
    X = np.asarray(feature_window, dtype=float)
    if X.ndim != 2 or X.shape[0] < 12:
        return 0.0
    model = IsolationForest(n_estimators=80, contamination="auto", random_state=42)
    model.fit(X)
    # decision_function: higher = more normal. Map latest row to 0..1 anomaly.
    raw = model.decision_function(X[-1:].reshape(1, -1))[0]
    return float(max(0.0, min(1.0, 0.5 - raw)))
