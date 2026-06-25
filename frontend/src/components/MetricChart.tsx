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
  color = "#6f8f6a",
}: Props) {
  const [data, setData] = useState<{ i: number; value: number }[]>([]);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    const run = async () => {
      try {
        const pts = await api.series(serviceId, metric, 80);
        if (alive) {
          setData(pts.map((p, i) => ({ i, value: p.value })));
          setFailed(false);
        }
      } catch {
        if (alive) setFailed(true);
      }
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
      {data.length === 0 ? (
        <div
          className="flex items-center justify-center rounded-lg border border-dashed border-ink-600 text-xs text-slate-500"
          style={{ height }}
        >
          {failed ? "Metric unavailable" : "Waiting for data…"}
        </div>
      ) : (
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id={`g-${serviceId}-${metric}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.4} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="i" hide />
          <YAxis tick={{ fill: "#9b927b", fontSize: 10 }} width={34} domain={[0, "auto"]} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={{
              background: "#fffdf8",
              border: "1px solid #e4dccb",
              borderRadius: 12,
              boxShadow: "0 8px 24px -12px rgba(72,58,30,0.25)",
            }}
            labelStyle={{ display: "none" }}
            itemStyle={{ color: "#3c382f" }}
            formatter={(v: number) => [v.toFixed(1), metric]}
          />
          {threshold != null && (
            <ReferenceLine y={threshold} stroke="#c08457" strokeDasharray="4 4" strokeWidth={1.5} />
          )}
          <Area
            type="monotone"
            dataKey="value"
            stroke={breaching ? "#b5524a" : color}
            fill={`url(#g-${serviceId}-${metric})`}
            strokeWidth={2}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
      )}
    </div>
  );
}
