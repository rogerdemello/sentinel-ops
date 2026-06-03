"""Abstract graph store.

The platform depends only on this interface, so the in-memory NetworkX backend
can be swapped for Neo4j (or a GNN-backed store) without touching callers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.models import Dependency, Service


class GraphStore(ABC):
    @abstractmethod
    def load(self, services: list[Service], deps: list[Dependency]) -> None: ...

    @abstractmethod
    def neighbors_downstream(self, service_id: str) -> list[str]:
        """Direct dependencies this service calls (edges out)."""

    @abstractmethod
    def neighbors_upstream(self, service_id: str) -> list[str]:
        """Direct callers that depend on this service (edges in)."""

    @abstractmethod
    def upstream_closure(self, service_id: str) -> list[str]:
        """All services transitively impacted if ``service_id`` fails.

        Failure propagates to callers, so this walks edges *inbound*.
        """

    @abstractmethod
    def edge_criticality(self, source_id: str, target_id: str) -> float: ...

    @abstractmethod
    def to_cytoscape(self) -> dict:
        """Serialize nodes+edges for the frontend graph view."""
