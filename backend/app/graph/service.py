"""Process-wide graph store accessor + (re)load helper."""

from __future__ import annotations

import logging
from functools import lru_cache

from app.config import get_settings
from app.db.repository import get_repository
from app.graph.interface import GraphStore
from app.graph.networkx_store import NetworkXGraphStore

logger = logging.getLogger(__name__)


@lru_cache
def get_graph() -> GraphStore:
    if get_settings().neo4j_enabled:
        try:
            from app.graph.neo4j_store import Neo4jGraphStore

            store = Neo4jGraphStore()
            logger.info("Using Neo4j graph backend")
            return store
        except Exception as exc:  # noqa: BLE001 - fall back if driver/server absent
            logger.warning("Neo4j unavailable (%s); using in-memory NetworkX graph", exc)
    return NetworkXGraphStore()


def reload_graph_from_repo() -> None:
    repo = get_repository()
    get_graph().load(repo.list_services(), repo.list_dependencies())
