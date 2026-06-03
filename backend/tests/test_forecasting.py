from app.forecasting.anomaly import robust_zscore
from app.forecasting.predictor import forecast_breach


def test_rising_trend_forecasts_breach_with_eta():
    # Linear ramp from 40 -> 88 over 40 points spaced 60s apart; threshold 95.
    points = [(i * 60.0, 40.0 + i * 1.2) for i in range(40)]
    fc = forecast_breach(points, threshold=95.0)
    assert fc is not None
    assert fc.breaching is True
    assert fc.eta_seconds > 0  # predicted ahead of the breach
    assert fc.probability >= 0.5


def test_flat_series_does_not_breach():
    points = [(i * 60.0, 42.0) for i in range(40)]
    fc = forecast_breach(points, threshold=95.0)
    assert fc is not None
    assert fc.breaching is False
    assert fc.probability < 0.5


def test_already_breached_is_certain():
    points = [(i * 60.0, 96.0 + i * 0.1) for i in range(20)]
    fc = forecast_breach(points, threshold=95.0)
    assert fc is not None
    assert fc.eta_seconds == 0
    assert fc.probability > 0.9


def test_robust_zscore_flags_spike():
    values = [10.0] * 20 + [80.0]
    assert robust_zscore(values) > 5.0
    assert abs(robust_zscore([10.0] * 21)) < 1.0
