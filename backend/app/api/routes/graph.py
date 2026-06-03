"""Dependency graph + topology endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.db.repository import get_repository
from app.graph.service import get_graph

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("")
def get_topology() -> dict:
    """Graph for the frontend (cytoscape-style nodes/edges) + raw lists."""
    repo = get_repository()
    return {
        "graph": get_graph().to_cytoscape(),
        "services": [s.model_dump(mode="json") for s in repo.list_services()],
        "dependencies": [
            d.model_dump(mode="json") for d in repo.list_dependencies()
        ],
    }
