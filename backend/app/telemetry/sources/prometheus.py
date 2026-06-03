"""Prometheus telemetry source.

Scrapes a Prometheus server's instant-query API and maps results to the unified
metric model. The query→(service, metric) mapping is configurable via the
``PROMETHEUS_QUERIES`` env var (JSON list of {query, service_id, metric}).
Activated when ``TELEMETRY_SOURCE=prometheus`` and ``PROMETHEUS_URL`` is set.

This is real ingestion code; in this demo environment (no Prometheus) it simply
returns nothing per tick rather than erroring.
"""

from __future__ import annotations

import json
import logging

import httpx

from app.config import get_settings
from app.telemetry.schema import MetricName, MetricPoint, TelemetryEvent
from app.telemetry.sources.base import TelemetrySource

logger = logging.getLogger(__name__)

# Sensible defaults mapping common node/cAdvisor series onto our model. Override
# entirely via PROMETHEUS_QUERIES for a real deployment.
_DEFAULT_QUERIES = [
    {"query": "100 - (avg by(instance)(rate(node_cpu_seconds_total{mode='idle'}[1m]))*100)",
     "service_id": "gateway", "metric": MetricName.cpu.value},
]


class PrometheusSource(TelemetrySource):
    name = "prometheus"

    def __init__(self) -> None:
        s = get_settings()
        self._url = (s.prometheus_url or "").rstrip("/")
        try:
            self._queries = json.loads(s.prometheus_queries) if s.prometheus_queries else _DEFAULT_QUERIES
        except json.JSONDecodeError:
            logger.warning("PROMETHEUS_QUERIES is not valid JSON; using defaults")
            self._queries = _DEFAULT_QUERIES

    def collect(self, now: float) -> tuple[list[MetricPoint], list[TelemetryEvent]]:
        if not self._url:
            return [], []
        metrics: list[MetricPoint] = []
        try:
            with httpx.Client(timeout=5.0) as client:
                for q in self._queries:
                    resp = client.get(f"{self._url}/api/v1/query", params={"query": q["query"]})
                    resp.raise_for_status()
                    results = resp.json().get("data", {}).get("result", [])
                    if not results:
                        continue
                    value = float(results[0]["value"][1])
                    metrics.append(
                        MetricPoint(
                            service_id=q["service_id"],
                            name=MetricName(q["metric"]),
                            value=value,
                            ts=now,
                        )
                    )
        except Exception as exc:  # noqa: BLE001 - scrape failures shouldn't crash the loop
            logger.debug("Prometheus scrape failed: %s", exc)
        return metrics, []
