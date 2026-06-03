import { useMemo } from "react";
import ReactFlow, { Background, Controls, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { api } from "../lib/api";
import { usePoll } from "../lib/usePoll";
import { Card, Badge } from "../components/ui";

const STATUS_COLOR: Record<string, string> = {
  healthy: "#10b981",
  warning: "#eab308",
  critical: "#ef4444",
};

export default function GraphView() {
  const { data: graph } = usePoll(api.graph, 5000);
  const { data: overview } = usePoll(api.overview, 2000);
  const { data: incidents } = usePoll(api.incidents, 2000);

  const statusById = useMemo(() => {
    const m: Record<string, string> = {};
    (overview ?? []).forEach((o) => (m[o.service.id] = o.status));
    return m;
  }, [overview]);

  const active = (incidents ?? []).filter((i) => i.status !== "resolved");
  const blastIds = new Set<string>(
    active.flatMap((i) => i.impact?.affected_service_ids ?? []),
  );
  const rootIds = new Set(active.map((i) => i.service_id));

  const { nodes, edges } = useMemo(() => {
    if (!graph) return { nodes: [] as Node[], edges: [] as Edge[] };
    const tierCount: Record<number, number> = {};
    const nodes: Node[] = graph.services.map((s) => {
      const idx = tierCount[s.tier] ?? 0;
      tierCount[s.tier] = idx + 1;
      const status = statusById[s.id] ?? "healthy";
      const isRoot = rootIds.has(s.id);
      const inBlast = blastIds.has(s.id);
      return {
        id: s.id,
        position: { x: s.tier * 230, y: idx * 95 + (s.tier % 2) * 45 },
        data: { label: s.name },
        style: {
          background: "#161d2e",
          color: "#e6ebf5",
          border: `2px solid ${
            isRoot ? "#ef4444" : inBlast ? "#f59e0b" : STATUS_COLOR[status]
          }`,
          borderRadius: 10,
          fontSize: 12,
          width: 150,
          boxShadow: isRoot ? "0 0 0 3px rgba(239,68,68,0.3)" : undefined,
        },
      };
    });
    const edges: Edge[] = graph.dependencies.map((d) => ({
      id: `${d.source_id}->${d.target_id}`,
      source: d.source_id,
      target: d.target_id,
      animated: blastIds.has(d.source_id) && (blastIds.has(d.target_id) || rootIds.has(d.target_id)),
      style: { stroke: "#334155" },
    }));
    return { nodes, edges };
  }, [graph, statusById, blastIds, rootIds]);

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Dependency Graph</h1>
          <p className="text-sm text-slate-400">Live topology with health overlay and blast-radius highlight.</p>
        </div>
        <div className="flex gap-2 text-xs">
          <Badge kind="critical" text="Failure root" />
          <Badge kind="high" text="Blast radius" />
          <Badge kind="healthy" text="Healthy" />
        </div>
      </div>
      <Card className="reactflow-wrapper" >
        <div style={{ height: 560 }}>
          <ReactFlow nodes={nodes} edges={edges} fitView proOptions={{ hideAttribution: true }}>
            <Background color="#1e2740" gap={20} />
            <Controls />
          </ReactFlow>
        </div>
      </Card>
    </div>
  );
}
