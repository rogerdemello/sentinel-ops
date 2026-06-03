"""Blast radius: what fails next if a given service degrades.

A failure propagates to the services that *call* the failing node (its upstream
callers), transitively. We weight each impacted service by the criticality of the
path connecting it to the failure.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.graph.interface import GraphStore


@dataclass
class BlastImpactedService:
    service_id: str
    criticality: float  # 0..1 strength of dependence on the failing node


def compute_blast_radius(
    failing_service_id: str, graph: GraphStore
) -> list[BlastImpactedService]:
    """Return impacted services (excluding the failing node itself).

    Criticality of an impacted caller is the criticality of its direct edge toward
    the failing subtree (approximated by the max edge criticality on any direct
    dependency it has into the impacted set).
    """
    impacted_ids = set(graph.upstream_closure(failing_service_id))
    impacted_ids.discard(failing_service_id)

    results: list[BlastImpactedService] = []
    closure_with_root = impacted_ids | {failing_service_id}
    for sid in impacted_ids:
        downstream = graph.neighbors_downstream(sid)
        crits = [
            graph.edge_criticality(sid, d)
            for d in downstream
            if d in closure_with_root
        ]
        results.append(
            BlastImpactedService(service_id=sid, criticality=max(crits, default=0.5))
        )
    # Most-critical first.
    results.sort(key=lambda r: r.criticality, reverse=True)
    return results
