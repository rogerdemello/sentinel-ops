"""Correlate anomalous services using graph adjacency.

Anomalies that co-occur on services that are graph-connected are likely part of
one incident. This groups them so the engine can attribute a single root cause.
"""

from __future__ import annotations

from app.graph.interface import GraphStore


def correlate(anomalous: list[str], graph: GraphStore) -> list[set[str]]:
    """Group anomalous service ids into connected clusters.

    Two anomalous services are linked if one directly depends on the other.
    """
    remaining = set(anomalous)
    clusters: list[set[str]] = []
    while remaining:
        seed = remaining.pop()
        cluster = {seed}
        frontier = [seed]
        while frontier:
            node = frontier.pop()
            adjacent = set(graph.neighbors_downstream(node)) | set(
                graph.neighbors_upstream(node)
            )
            for nb in adjacent & remaining:
                remaining.discard(nb)
                cluster.add(nb)
                frontier.append(nb)
        clusters.append(cluster)
    return clusters


def root_of_cluster(cluster: set[str], graph: GraphStore) -> str:
    """Pick the most-downstream node (deepest dependency) as the likely root.

    Failures originate downstream and propagate to callers, so the cluster member
    with the fewest downstream dependencies inside the cluster is the root.
    """
    def downstream_in_cluster(s: str) -> int:
        return len(set(graph.neighbors_downstream(s)) & cluster)

    return min(cluster, key=downstream_in_cluster)
