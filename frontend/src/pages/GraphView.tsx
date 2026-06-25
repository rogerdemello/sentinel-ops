import { useMemo } from "react";
import ReactFlow, { Background, Controls, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { api } from "../lib/api";
import { usePoll } from "../lib/usePoll";
import { Card, Badge } from "../components/ui";

const STATUS_COLOR: Record<string, string> = {
  healthy: "#6f8f6a",
  warning: "#c59a3f",
  critical: "#b5524a",
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
          background: "#fffdf8",
          color: "#3c382f",
          border: `2px solid ${
            isRoot ? "#b5524a" : inBlast ? "#c08457" : STATUS_COLOR[status]
          }`,
          borderRadius: 12,
          fontSize: 12,
          fontWeight: 500,
          width: 150,
          padding: "2px 0",
          boxShadow: isRoot
            ? "0 0 0 4px rgba(181,82,74,0.16), 0 8px 20px -8px rgba(72,58,30,0.2)"
            : "0 4px 14px -8px rgba(72,58,30,0.25)",
        },
      };
    });
    const edges: Edge[] = graph.dependencies.map((d) => ({
      id: `${d.source_id}->${d.target_id}`,
      source: d.source_id,
      target: d.target_id,
      animated: blastIds.has(d.source_id) && (blastIds.has(d.target_id) || rootIds.has(d.target_id)),
      style: {
        stroke:
          blastIds.has(d.source_id) && (blastIds.has(d.target_id) || rootIds.has(d.target_id))
            ? "#c08457"
            : "#cabfa6",
        strokeWidth: 1.5,
      },
    }));
    return { nodes, edges };
  }, [graph, statusById, blastIds, rootIds]);

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-[1.75rem] text-slate-100">Dependency Graph</h1>
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
            <Background color="#ddd3bf" gap={22} />
            <Controls />
          </ReactFlow>
        </div>
      </Card>
    </div>
  );
}
