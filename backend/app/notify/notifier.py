"""Multi-channel alerting (Slack, PagerDuty, generic webhook).

Dispatches on a daemon thread so notifications never block the engine. Each
channel fires only when its credential is configured; with none set the notifier
is a no-op. Best-effort: send failures are logged, never raised.
"""

from __future__ import annotations

import logging
import queue
import threading
from functools import lru_cache

from app.config import get_settings
from app.models import Incident

logger = logging.getLogger(__name__)


class Notifier:
    def __init__(self) -> None:
        self._q: queue.Queue[dict | None] = queue.Queue(maxsize=1000)
        self._thread: threading.Thread | None = None
        self._started = False
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        s = get_settings()
        return bool(s.slack_webhook_url or s.pagerduty_routing_key or s.alert_webhook_url)

    def _ensure(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
            self._thread = threading.Thread(target=self._run, name="notifier", daemon=True)
            self._thread.start()

    def incident_opened(self, incident: Incident) -> None:
        self._emit(
            severity="critical" if incident.severity in ("critical", "high") else "warning",
            title=f"🔮 Predicted: {incident.title}",
            text=(
                f"{int(incident.probability * 100)}% probability · "
                f"{incident.incident_type} on {incident.service_id}\n"
                f"Root cause: {incident.root_cause or 'analyzing…'}"
                + (f"\nImpact: {incident.impact.headline}" if incident.impact else "")
            ),
            incident=incident,
        )

    def incident_resolved(self, incident: Incident) -> None:
        how = "autonomously self-healed" if incident.auto_remediated else "resolved by operator"
        self._emit(
            severity="info",
            title=f"✅ Resolved: {incident.title}",
            text=f"Incident {how}.",
            incident=incident,
        )

    def _emit(self, *, severity: str, title: str, text: str, incident: Incident) -> None:
        if not self.enabled:
            return
        self._ensure()
        try:
            self._q.put_nowait(
                {"severity": severity, "title": title, "text": text,
                 "incident_id": incident.id}
            )
        except queue.Full:  # pragma: no cover
            pass

    # -- worker --
    def _run(self) -> None:
        import httpx

        while True:
            msg = self._q.get()
            if msg is None:
                break
            s = get_settings()
            try:
                with httpx.Client(timeout=8.0) as client:
                    if s.slack_webhook_url:
                        client.post(s.slack_webhook_url,
                                    json={"text": f"*{msg['title']}*\n{msg['text']}"})
                    if s.alert_webhook_url:
                        client.post(s.alert_webhook_url, json=msg)
                    if s.pagerduty_routing_key:
                        client.post(
                            "https://events.pagerduty.com/v2/enqueue",
                            json={
                                "routing_key": s.pagerduty_routing_key,
                                "event_action": "resolve" if msg["severity"] == "info" else "trigger",
                                "dedup_key": msg["incident_id"],
                                "payload": {
                                    "summary": msg["title"],
                                    "source": "sentinelops",
                                    "severity": "critical" if msg["severity"] == "critical" else "warning",
                                    "custom_details": {"text": msg["text"]},
                                },
                            },
                        )
            except Exception as exc:  # noqa: BLE001
                logger.debug("notify dispatch failed: %s", exc)


@lru_cache
def get_notifier() -> Notifier:
    return Notifier()
