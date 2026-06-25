"""Irregular-timestamp forecasting + Prometheus scrape mapping."""

from __future__ import annotations

from app.config import get_settings
from app.forecasting.predictor import forecast_breach
from app.telemetry.schema import MetricName


def test_trend_forecast_handles_irregular_timestamps():
    """Real telemetry arrives at irregular intervals. The trend forecaster fits on
    actual timestamps (not index position), so a rising series with uneven gaps
    must still project a breach with a sane ETA."""
    threshold = 95.0
    # Irregularly-spaced timestamps (gaps: 30s, 90s, 15s, 120s, ...), value rising
    # ~0.1/sec toward the threshold.
    gaps = [0, 30, 120, 135, 255, 300, 360, 540, 600, 700, 820, 900]
    t0 = 1_000_000.0
    points = [(t0 + g, 60.0 + 0.04 * g) for g in gaps]  # 60 → ~96 across the window
    fc = forecast_breach(points, threshold)
    assert fc is not None
    # Slope is per-second and independent of sampling cadence.
    assert fc.slope_per_sec > 0
    # Either already breached at the end, or a finite positive ETA to breach.
    assert fc.already_breached or fc.eta_seconds >= 0
    assert fc.probability > 0.3


def test_flat_irregular_series_is_not_a_false_breach():
    threshold = 95.0
    gaps = [0, 45, 60, 200, 230, 400, 600, 900]
    t0 = 500_000.0
    points = [(t0 + g, 40.0) for g in gaps]  # flat, far from threshold
    fc = forecast_breach(points, threshold)
    assert fc is not None
    assert fc.already_breached is False
    assert fc.probability < 0.3


def test_prometheus_source_maps_scrape_to_metric(monkeypatch):
    monkeypatch.setenv("PROMETHEUS_URL", "http://prom.local:9090")
    get_settings.cache_clear()
    try:
        import httpx

        from app.telemetry.sources.prometheus import PrometheusSource

        class _FakeResp:
            def raise_for_status(self):
                return None

            def json(self):
                return {"data": {"result": [{"value": [0, "42.5"]}]}}

        class _FakeClient:
            def __init__(self, *a, **k):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def get(self, url, params=None):
                return _FakeResp()

        monkeypatch.setattr(httpx, "Client", _FakeClient)

        src = PrometheusSource()
        metrics, events = src.collect(now=1234.0)

        assert len(metrics) == 1
        m = metrics[0]
        assert m.service_id == "gateway"
        assert m.name == MetricName.cpu
        assert m.value == 42.5
        assert m.ts == 1234.0
        assert events == []
    finally:
        get_settings.cache_clear()
