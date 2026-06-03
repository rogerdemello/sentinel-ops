"""Persistence write-through facade.

Routes mirror-writes to Postgres (preferred, via the background ``writer``) when
``DATABASE_URL`` is set, else to the Supabase REST client when configured, else
no-ops. Never raises — persistence is an enhancement, not a hard dependency.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_supabase():  # -> Client | None
    settings = get_settings()
    if not settings.supabase_enabled:
        return None
    try:
        from supabase import create_client

        return create_client(settings.supabase_url, settings.supabase_service_key)
    except Exception as exc:  # pragma: no cover - depends on external lib/env
        logger.warning("Supabase REST client init failed: %s", exc)
        return None


def _supabase_write(method: str, table: str, row: dict[str, Any]) -> None:
    client = get_supabase()
    if client is None:
        return
    try:
        getattr(client.table(table), method)(row).execute()
    except Exception as exc:  # pragma: no cover - external
        logger.debug("Supabase %s %s failed: %s", method, table, exc)


def upsert(table: str, row: dict[str, Any]) -> None:
    settings = get_settings()
    if settings.db_persist_enabled:
        from app.db.writer import get_writer

        get_writer().enqueue("upsert", table, row)
    elif settings.supabase_enabled:
        _supabase_write("upsert", table, row)


def insert(table: str, row: dict[str, Any]) -> None:
    settings = get_settings()
    if settings.db_persist_enabled:
        from app.db.writer import get_writer

        get_writer().enqueue("insert", table, row)
    elif settings.supabase_enabled:
        _supabase_write("insert", table, row)
