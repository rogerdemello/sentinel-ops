import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../lib/api";

interface Props {
  serviceId: string;
  metric: string;
  label?: string;
  threshold?: number;
  height?: number;
  color?: string;
}

export default function MetricChart({
  serviceId,
  metric,
  label,
  threshold,
  height = 120,
  color = "#5b8cff",
}: Props) {
  const [data, setData] = useState<{ i: number; value: number }[]>([]);

  useEffect(() => {
    let alive = true;
    const run = async () => {
      const pts = await api.series(serviceId, metric, 80);
      if (alive) setData(pts.map((p, i) => ({ i, value: p.value })));
    };
    run();
    const id = setInterval(run, 2000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [serviceId, metric]);

  const breaching = threshold != null && data.length > 0 && data[data.length - 1].value >= threshold;

  return (
    <div>
      {label && (
        <div className="mb-1 flex items-center justify-between text-xs text-slate-400">
          <span>{label}</span>
          <span className={breaching ? "text-red-300" : "text-slate-300"}>
            {data.length ? data[data.length - 1].value.toFixed(1) : "—"}
            {threshold != null && <span className="text-slate-500"> / {threshold}</span>}
          </span>
        </div>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id={`g-${serviceId}-${metric}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.4} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="i" hide />
          <YAxis tick={{ fill: "#64748b", fontSize: 10 }} width={34} domain={[0, "auto"]} />
          <Tooltip
            contentStyle={{ background: "#0f1523", border: "1px solid #1e2740", borderRadius: 8 }}
            labelStyle={{ display: "none" }}
            itemStyle={{ color: "#e6ebf5" }}
            formatter={(v: number) => [v.toFixed(1), metric]}
          />
          {threshold != null && (
            <ReferenceLine y={threshold} stroke="#ef4444" strokeDasharray="4 4" />
          )}
          <Area
            type="monotone"
            dataKey="value"
            stroke={breaching ? "#ef4444" : color}
            fill={`url(#g-${serviceId}-${metric})`}
            strokeWidth={2}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
