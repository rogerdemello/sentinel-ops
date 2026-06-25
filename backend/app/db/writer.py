"""Background Postgres write-through.

Mirrors curated records (services, dependencies, predictions, incidents, events)
to Postgres/Supabase on a daemon thread, so remote DB latency never blocks the
asyncio engine. Writes are best-effort: connection/SQL errors are logged and the
in-memory store remains the source of truth.

High-volume raw telemetry metrics are skipped unless ``PERSIST_TELEMETRY=true``.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

# table -> (primary key columns, all writable columns, json/jsonb columns)
_SCHEMA: dict[str, tuple[list[str], list[str], set[str]]] = {
    "services": (
        ["id"],
        ["id", "name", "kind", "tier", "region", "users", "revenue_per_min"],
        set(),
    ),
    "dependencies": (
        ["source_id", "target_id"],
        ["source_id", "target_id", "kind", "criticality"],
        set(),
    ),
    "predictions": (
        ["id"],
        ["id", "service_id", "incident_type", "probability", "eta_seconds",
         "metric", "summary", "features", "created_at"],
        {"features"},
    ),
    "incidents": (
        ["id"],
        ["id", "service_id", "incident_type", "status", "severity", "title",
         "scenario_key", "probability", "eta_seconds", "lead_metric",
         "lead_threshold", "root_cause", "diagnosis", "findings", "impact",
         "plan", "timeline", "auto_remediated", "postmortem", "created_at", "updated_at"],
        {"findings", "impact", "plan", "timeline"},
    ),
    "telemetry_events": (
        ["id"],
        ["id", "service_id", "type", "severity", "message", "ts", "attributes"],
        {"attributes"},
    ),
    "telemetry_metrics": (
        ["id"],
        ["id", "service_id", "name", "value", "ts"],
        set(),
    ),
    "audit_log": (
        ["id"],
        ["id", "at", "actor", "role", "incident_id", "action_kind",
         "target_service_id", "executor", "result_status", "detail"],
        set(),
    ),
}


_COOLDOWN_SECONDS = 30.0  # when the DB is unreachable, pause writes this long


class _Writer:
    def __init__(self) -> None:
        self._q: queue.Queue[tuple[str, str, dict] | None] = queue.Queue(maxsize=10000)
        self._thread: threading.Thread | None = None
        self._conn = None
        self._started = False
        self._lock = threading.Lock()
        self.failures = 0  # rows dropped because the DB was unreachable
        self.last_error: str | None = None
        self._degraded = False  # circuit-breaker state (DB currently considered down)
        self._cooldown_until = 0.0  # monotonic time until which writes are paused

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
            self._thread = threading.Thread(target=self._run, name="pg-writer", daemon=True)
            self._thread.start()
            logger.info("Postgres write-through worker started")

    def flush(self, timeout: float = 5.0) -> None:
        """Drain remaining queued writes and stop the worker — called on graceful
        shutdown so in-flight mirror writes aren't lost when the process exits."""
        if not self._started or self._thread is None:
            return
        self._q.put(None)  # sentinel: process everything already queued, then stop
        self._thread.join(timeout)
        self._started = False

    def enqueue(self, op: str, table: str, row: dict[str, Any]) -> None:
        if table not in _SCHEMA:
            return
        if not self._started:
            self.start()
        try:
            self._q.put_nowait((op, table, row))
        except queue.Full:  # pragma: no cover - backpressure safety
            self.failures += 1
            logger.warning("write queue full; dropping %s on %s", op, table)

    # -- worker --
    def _connect(self):
        import psycopg

        self._conn = psycopg.connect(get_settings().database_url, autocommit=True)

    def _run(self) -> None:
        while True:
            item = self._q.get()
            if item is None:
                break
            op, table, row = item
            # Circuit breaker: while the DB is down, drop writes for a cooldown window
            # instead of hammering an unresolvable host and flooding the logs. The
            # in-memory store remains the source of truth, so dropped mirrors are safe.
            if self._degraded and time.monotonic() < self._cooldown_until:
                self.failures += 1
                continue
            try:
                self._execute(op, table, row)
                if self._degraded:
                    self._degraded = False
                    logger.info("Postgres write-through recovered")
            except Exception as exc:  # noqa: BLE001 - best effort
                self._conn = None  # force reconnect next time
                self.last_error = str(exc)
                self.failures += 1
                self._cooldown_until = time.monotonic() + _COOLDOWN_SECONDS
                if not self._degraded:
                    self._degraded = True
                    logger.warning(
                        "Postgres write-through failing (%s); pausing mirror writes for "
                        "%.0fs (in-memory store unaffected). Further errors suppressed "
                        "until recovery.",
                        exc, _COOLDOWN_SECONDS,
                    )

    def _execute(self, op: str, table: str, row: dict[str, Any]) -> None:
        from psycopg.types.json import Json

        if self._conn is None or self._conn.closed:
            self._connect()

        pk, columns, json_cols = _SCHEMA[table]
        cols = [c for c in columns if c in row]
        values = [Json(row[c]) if c in json_cols else row[c] for c in cols]
        placeholders = ", ".join(["%s"] * len(cols))
        col_list = ", ".join(cols)

        if op == "upsert":
            updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c not in pk)
            conflict = ", ".join(pk)
            action = f"DO UPDATE SET {updates}" if updates else "DO NOTHING"
            sql = (
                f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
                f"ON CONFLICT ({conflict}) {action}"
            )
        else:  # insert (idempotent)
            sql = (
                f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
                f"ON CONFLICT DO NOTHING"
            )
        with self._conn.cursor() as cur:
            cur.execute(sql, values)


_writer = _Writer()


def get_writer() -> _Writer:
    return _writer
