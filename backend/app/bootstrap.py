"""One-time seeding of topology into the repository + graph store."""

from __future__ import annotations

from app.db.repository import get_repository
from app.graph.service import reload_graph_from_repo
from app.graph.topology import seed_dependencies, seed_services


def seed_topology() -> None:
    repo = get_repository()
    if repo.list_services():  # already seeded
        return
    for svc in seed_services():
        repo.add_service(svc)
    for dep in seed_dependencies():
        repo.add_dependency(dep)
    reload_graph_from_repo()
