"""Neo4j-backed GraphStore for large-scale, persistent dependency graphs.

Implements the same ``GraphStore`` contract as the in-memory NetworkX backend,
so the rest of the platform is unchanged. Activated when ``NEO4J_URI`` is set;
otherwise the NetworkX store is used. The driver is imported lazily so neo4j is
never a hard dependency.
"""

from __future__ import annotations

import logging

from app.config import get_settings
from app.graph.interface import GraphStore
from app.models import Dependency, Service

logger = logging.getLogger(__name__)


class Neo4jGraphStore(GraphStore):
    def __init__(self) -> None:
        from neo4j import GraphDatabase

        s = get_settings()
        self._driver = GraphDatabase.driver(
            s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password)
        )

    def close(self) -> None:
        self._driver.close()

    def load(self, services: list[Service], deps: list[Dependency]) -> None:
        with self._driver.session() as session:
            session.run("MATCH (n:Service) DETACH DELETE n")
            for s in services:
                session.run(
                    """
                    MERGE (n:Service {id: $id})
                    SET n.name=$name, n.kind=$kind, n.tier=$tier,
                        n.users=$users, n.revenue_per_min=$rev
                    """,
                    id=s.id, name=s.name, kind=s.kind.value, tier=s.tier,
                    users=s.users, rev=s.revenue_per_min,
                )
            for d in deps:
                session.run(
                    """
                    MATCH (a:Service {id:$src}), (b:Service {id:$tgt})
                    MERGE (a)-[r:CALLS]->(b)
                    SET r.criticality=$crit, r.kind=$kind
                    """,
                    src=d.source_id, tgt=d.target_id, crit=d.criticality, kind=d.kind,
                )

    def neighbors_downstream(self, service_id: str) -> list[str]:
        with self._driver.session() as session:
            res = session.run(
                "MATCH (a:Service {id:$id})-[:CALLS]->(b) RETURN b.id AS id",
                id=service_id,
            )
            return [r["id"] for r in res]

    def neighbors_upstream(self, service_id: str) -> list[str]:
        with self._driver.session() as session:
            res = session.run(
                "MATCH (a)-[:CALLS]->(b:Service {id:$id}) RETURN a.id AS id",
                id=service_id,
            )
            return [r["id"] for r in res]

    def upstream_closure(self, service_id: str) -> list[str]:
        with self._driver.session() as session:
            res = session.run(
                "MATCH (a)-[:CALLS*1..]->(b:Service {id:$id}) RETURN DISTINCT a.id AS id",
                id=service_id,
            )
            return [r["id"] for r in res]

    def edge_criticality(self, source_id: str, target_id: str) -> float:
        with self._driver.session() as session:
            res = session.run(
                """
                MATCH (a:Service {id:$src})-[r:CALLS]->(b:Service {id:$tgt})
                RETURN r.criticality AS c
                """,
                src=source_id, tgt=target_id,
            )
            rec = res.single()
            return float(rec["c"]) if rec and rec["c"] is not None else 0.0

    def to_cytoscape(self) -> dict:
        with self._driver.session() as session:
            nodes = [
                {"data": {"id": r["id"], "name": r["name"], "kind": r["kind"],
                          "tier": r["tier"], "users": r["users"],
                          "revenue_per_min": r["rev"]}}
                for r in session.run(
                    "MATCH (n:Service) RETURN n.id AS id, n.name AS name, n.kind AS kind,"
                    " n.tier AS tier, n.users AS users, n.revenue_per_min AS rev"
                )
            ]
            edges = [
                {"data": {"id": f"{r['s']}->{r['t']}", "source": r["s"],
                          "target": r["t"], "criticality": r["c"]}}
                for r in session.run(
                    "MATCH (a)-[r:CALLS]->(b) RETURN a.id AS s, b.id AS t,"
                    " r.criticality AS c"
                )
            ]
        return {"nodes": nodes, "edges": edges}
