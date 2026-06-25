"""Boot-time rehydration from Postgres.

The in-memory store is the live source of truth, but when ``DATABASE_URL`` is set
the engine mirrors incidents/predictions to Postgres. On startup we read them back
so a restart doesn't lose open incidents — durability without changing the hot path.

Best-effort: any connection/parse failure is logged and skipped (the app still
boots cleanly on a fresh/unreachable database).
"""

from __future__ import annotations

import logging

from app.config import get_settings
from app.db.repository import Repository, get_repository
from app.models import Incident, Prediction

logger = logging.getLogger(__name__)


def incident_from_row(row: dict) -> Incident:
    """Reconstruct an Incident from a DB row (JSON columns already parsed)."""
    return Incident.model_validate(row)


def prediction_from_row(row: dict) -> Prediction:
    return Prediction.model_validate(row)


def rehydrate(repo: Repository | None = None) -> int:
    """Load persisted incidents + predictions into ``repo`` (default tenant).

    Returns the number of incidents loaded (0 if persistence is disabled or the
    database is unreachable).
    """
    settings = get_settings()
    if not settings.db_persist_enabled:
        return 0
    repo = repo or get_repository()
    loaded = 0
    try:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(
            settings.database_url, connect_timeout=5, row_factory=dict_row
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM incidents")
                for row in cur.fetchall():
                    try:
                        repo.load_incident(incident_from_row(row))
                        loaded += 1
                    except Exception as exc:  # noqa: BLE001 - skip a bad row, keep going
                        logger.warning("Skipped unrehydratable incident row: %s", exc)
                cur.execute("SELECT * FROM predictions")
                for row in cur.fetchall():
                    try:
                        repo.load_prediction(prediction_from_row(row))
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Skipped unrehydratable prediction row: %s", exc)
    except Exception as exc:  # noqa: BLE001 - DB unreachable / schema absent
        logger.warning("Rehydrate from Postgres skipped (%s); starting fresh.", exc)
        return 0
    if loaded:
        logger.info("Rehydrated %d incident(s) from Postgres on startup.", loaded)
    return loaded
