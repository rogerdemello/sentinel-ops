import { useState } from "react";
import { api } from "../lib/api";
import { usePoll } from "../lib/usePoll";
import { Card, Badge } from "./ui";

export default function ScenarioBar() {
  const { data: scenarios } = usePoll(api.scenarios, 2500);
  const [busy, setBusy] = useState<string | null>(null);

  const trigger = async (key: string, active: boolean) => {
    setBusy(key);
    try {
      if (active) await api.clearScenario(key);
      else await api.triggerScenario(key);
    } finally {
      setBusy(null);
    }
  };

  return (
    <Card title="Inject Incident Scenario" className="mb-6">
      <div className="flex flex-wrap gap-2">
        {(scenarios ?? []).map((s) => (
          <button
            key={s.key}
            disabled={busy === s.key}
            onClick={() => trigger(s.key, s.active)}
            className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition ${
              s.active
                ? "border-red-500/40 bg-red-500/10 text-red-200"
                : "border-ink-600 bg-ink-700 text-slate-200 hover:border-accent/50"
            }`}
          >
            <span>{s.active ? "■ Stop" : "▶ Trigger"}</span>
            <span className="font-medium">{s.name}</span>
            <Badge kind={s.severity} />
          </button>
        ))}
      </div>
      <p className="mt-3 text-xs text-slate-500">
        Triggering ramps synthetic telemetry so the engine predicts the incident before it breaches.
        Stopping (or approving remediation) returns metrics to baseline.
      </p>
    </Card>
  );
}
