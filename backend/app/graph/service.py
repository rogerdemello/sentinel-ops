"""Process-wide graph store accessor + (re)load helper."""

from __future__ import annotations

from functools import lru_cache

from app.db.repository import get_repository
from app.graph.interface import GraphStore
from app.graph.networkx_store import NetworkXGraphStore


@lru_cache
def get_graph() -> GraphStore:
    return NetworkXGraphStore()


def reload_graph_from_repo() -> None:
    repo = get_repository()
    get_graph().load(repo.list_services(), repo.list_dependencies())
