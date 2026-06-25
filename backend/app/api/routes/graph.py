"""Dependency graph + topology endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import tenant_repo
from app.db.repository import Repository
from app.graph.service import get_graph

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("")
def get_topology(repo: Repository = Depends(tenant_repo)) -> dict:
    """Graph for the frontend (cytoscape-style nodes/edges) + raw lists."""
    return {
        "graph": get_graph().to_cytoscape(),
        "services": [s.model_dump(mode="json") for s in repo.list_services()],
        "dependencies": [
            d.model_dump(mode="json") for d in repo.list_dependencies()
        ],
    }
