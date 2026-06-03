"""In-memory dependency graph backed by networkx.DiGraph.

Edge direction follows the call graph: ``source -> target`` means *source calls
target*. A failure of ``target`` therefore propagates to its predecessors
(callers), which is why blast radius walks inbound edges.
"""

from __future__ import annotations

import networkx as nx

from app.graph.interface import GraphStore
from app.models import Dependency, Service


class NetworkXGraphStore(GraphStore):
    def __init__(self) -> None:
        self.g = nx.DiGraph()

    def load(self, services: list[Service], deps: list[Dependency]) -> None:
        self.g.clear()
        for s in services:
            self.g.add_node(
                s.id,
                name=s.name,
                kind=s.kind.value,
                tier=s.tier,
                users=s.users,
                revenue_per_min=s.revenue_per_min,
            )
        for d in deps:
            self.g.add_edge(d.source_id, d.target_id, criticality=d.criticality, kind=d.kind)

    def neighbors_downstream(self, service_id: str) -> list[str]:
        return list(self.g.successors(service_id)) if service_id in self.g else []

    def neighbors_upstream(self, service_id: str) -> list[str]:
        return list(self.g.predecessors(service_id)) if service_id in self.g else []

    def upstream_closure(self, service_id: str) -> list[str]:
        if service_id not in self.g:
            return []
        # Ancestors via inbound edges = everyone who (transitively) calls this node.
        return list(nx.ancestors(self.g, service_id))

    def edge_criticality(self, source_id: str, target_id: str) -> float:
        if self.g.has_edge(source_id, target_id):
            return float(self.g[source_id][target_id].get("criticality", 1.0))
        return 0.0

    def to_cytoscape(self) -> dict:
        nodes = [
            {"data": {"id": n, **self.g.nodes[n]}} for n in self.g.nodes
        ]
        edges = [
            {
                "data": {
                    "id": f"{u}->{v}",
                    "source": u,
                    "target": v,
                    "criticality": self.g[u][v].get("criticality", 1.0),
                }
            }
            for u, v in self.g.edges
        ]
        return {"nodes": nodes, "edges": edges}
