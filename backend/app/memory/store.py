"""Retrieval-augmented incident memory.

Embeds resolved incidents (Azure ada-002) into a Supabase **pgvector** table, then
retrieves the most similar past incidents to ground new RCAs ("we've seen this
before; last time X fixed it"). Fully optional: when embeddings or the DB aren't
configured, ``recall``/``remember`` are safe no-ops.
"""

from __future__ import annotations

import logging
import threading

from app.agents.llm.embeddings import embed
from app.config import get_settings
from app.models import Incident

logger = logging.getLogger(__name__)

_EMBED_DIM = 1536  # text-embedding-ada-002
_schema_ready = False


def _connect():
    import psycopg

    return psycopg.connect(get_settings().database_url, autocommit=True, connect_timeout=15)


def ensure_schema() -> bool:
    """Create the pgvector extension + memory table. Returns True on success."""
    global _schema_ready
    if not get_settings().rag_enabled:
        return False
    if _schema_ready:
        return True
    try:
        with _connect() as conn, conn.cursor() as cur:
            cur.execute("create extension if not exists vector")
            cur.execute(
                f"""
                create table if not exists incident_memory (
                    id          text primary key,
                    incident_id text not null,
                    summary     text not null,
                    severity    text,
                    root_cause  text,
                    embedding   vector({_EMBED_DIM}),
                    created_at  double precision not null default 0
                )
                """
            )
        _schema_ready = True
        logger.info("RAG incident memory schema ready (pgvector)")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not initialize RAG memory schema: %s", exc)
        return False


def _incident_text(incident: Incident) -> str:
    parts = [
        incident.title,
        f"type={incident.incident_type}",
        f"service={incident.service_id}",
        f"root_cause={incident.root_cause or ''}",
        f"diagnosis={incident.diagnosis or ''}",
    ]
    if incident.plan:
        parts.append("remediation=" + ",".join(a.kind for a in incident.plan.actions))
    return " | ".join(parts)


def _vec_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


def remember(incident: Incident) -> None:
    """Embed + store a resolved incident (runs in a background thread)."""
    if not get_settings().rag_enabled:
        return

    def _work():
        if not ensure_schema():
            return
        vec = embed(_incident_text(incident))
        if vec is None:
            return
        try:
            with _connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    insert into incident_memory
                        (id, incident_id, summary, severity, root_cause, embedding, created_at)
                    values (%s, %s, %s, %s, %s, %s::vector, %s)
                    on conflict (id) do nothing
                    """,
                    (incident.id, incident.id, _incident_text(incident),
                     str(incident.severity), incident.root_cause,
                     _vec_literal(vec), incident.created_at),
                )
        except Exception as exc:  # noqa: BLE001
            logger.debug("remember() insert failed: %s", exc)

    threading.Thread(target=_work, name="rag-remember", daemon=True).start()


def recall(query_text: str, k: int = 3) -> list[dict]:
    """Return up to k most similar past incidents (cosine), or [] if unavailable."""
    if not get_settings().rag_enabled or not ensure_schema():
        return []
    vec = embed(query_text)
    if vec is None:
        return []
    try:
        with _connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select summary, root_cause, severity,
                       1 - (embedding <=> %s::vector) as score
                from incident_memory
                order by embedding <=> %s::vector
                limit %s
                """,
                (_vec_literal(vec), _vec_literal(vec), k),
            )
            return [
                {"summary": r[0], "root_cause": r[1], "severity": r[2],
                 "score": round(float(r[3]), 3)}
                for r in cur.fetchall()
            ]
    except Exception as exc:  # noqa: BLE001
        logger.debug("recall() query failed: %s", exc)
        return []
