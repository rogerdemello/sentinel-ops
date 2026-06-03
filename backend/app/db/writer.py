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
         "plan", "timeline", "auto_remediated", "created_at", "updated_at"],
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
}


class _Writer:
    def __init__(self) -> None:
        self._q: queue.Queue[tuple[str, str, dict] | None] = queue.Queue(maxsize=10000)
        self._thread: threading.Thread | None = None
        self._conn = None
        self._started = False
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
            self._thread = threading.Thread(target=self._run, name="pg-writer", daemon=True)
            self._thread.start()
            logger.info("Postgres write-through worker started")

    def enqueue(self, op: str, table: str, row: dict[str, Any]) -> None:
        if table not in _SCHEMA:
            return
        if not self._started:
            self.start()
        try:
            self._q.put_nowait((op, table, row))
        except queue.Full:  # pragma: no cover - backpressure safety
            logger.debug("write queue full; dropping %s on %s", op, table)

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
            try:
                self._execute(op, table, row)
            except Exception as exc:  # noqa: BLE001 - best effort
                logger.debug("write-through %s %s failed: %s", op, table, exc)
                self._conn = None  # force reconnect next time

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
