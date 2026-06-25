import { api } from "../lib/api";
import { usePoll } from "../lib/usePoll";
import { Card, Badge, etaText } from "../components/ui";

function ProbBar({ p }: { p: number }) {
  const color = p >= 0.8 ? "bg-red-400" : p >= 0.6 ? "bg-orange-400" : "bg-yellow-400";
  return (
    <div className="h-2 w-full rounded bg-ink-600">
      <div className={`h-2 rounded ${color}`} style={{ width: `${p * 100}%` }} />
    </div>
  );
}

export default function Predictions() {
  const { data: predictions } = usePoll(api.predictions, 1500);

  return (
    <div>
      <h1 className="mb-1 text-[1.75rem] font-medium text-slate-100">Incident Predictions</h1>
      <p className="mb-6 text-sm text-slate-400">
        Forecasting + anomaly detection projecting which services will breach, and when.
      </p>

      {(predictions ?? []).length === 0 && (
        <Card>
          <div className="text-sm text-slate-500">
            No incidents predicted — all monitored metrics are within safe trends.
          </div>
        </Card>
      )}

      <div className="space-y-3">
        {(predictions ?? []).map((p) => (
          <Card key={p.id}>
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-lg font-semibold text-slate-100">
                    {(p.probability * 100).toFixed(0)}%
                  </span>
                  <Badge kind={p.incident_type === "security" ? "critical" : "high"} text={p.incident_type} />
                  <span className="text-sm text-slate-400">ETA {etaText(p.eta_seconds)}</span>
                </div>
                <div className="mt-1 text-sm text-slate-300">{p.summary}</div>
              </div>
              <div className="w-40 text-right text-xs text-slate-500">
                <div>metric: {p.metric}</div>
                <div>now: {p.features.current?.toFixed(1) ?? "—"} / {p.features.threshold ?? "—"}</div>
              </div>
            </div>
            <div className="mt-3">
              <ProbBar p={p.probability} />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
