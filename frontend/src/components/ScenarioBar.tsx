import { useState } from "react";
import { api } from "../lib/api";
import { usePoll } from "../lib/usePoll";
import { Card, Badge } from "./ui";

export default function ScenarioBar() {
  const { data: scenarios } = usePoll(api.scenarios, 2500);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const trigger = async (key: string, active: boolean) => {
    setBusy(key);
    setError(null);
    try {
      if (active) await api.clearScenario(key);
      else await api.triggerScenario(key);
    } catch (e: any) {
      setError(e?.message ?? "Scenario action failed — is the backend running?");
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
            aria-pressed={s.active}
            aria-label={`${s.active ? "Stop" : "Trigger"} scenario ${s.name}`}
            onClick={() => trigger(s.key, s.active)}
            className={`group flex items-center gap-2.5 rounded-xl border px-3.5 py-2 text-sm transition-all duration-200 disabled:opacity-60 ${
              s.active
                ? "border-red-400/40 bg-red-400/10 text-red-300 shadow-soft"
                : "border-ink-600 bg-ink-800 text-slate-300 hover:-translate-y-0.5 hover:border-accent/50 hover:text-slate-100 hover:shadow-card"
            }`}
          >
            <span
              aria-hidden
              className={`h-2 w-2 rounded-full transition-colors ${
                s.active ? "bg-red-400 animate-pulse-soft" : "bg-slate-500 group-hover:bg-accent"
              }`}
            />
            <span className="font-medium">{s.name}</span>
            <Badge kind={s.severity} />
          </button>
        ))}
      </div>
      {error && <p className="mt-3 text-xs text-red-300">{error}</p>}
      <p className="mt-3 text-xs text-slate-500">
        Telemetry is sampled live from this host; triggering a scenario ramps a metric on
        top of the real baseline so the engine predicts the incident before it breaches.
        Stopping (or approving remediation) returns metrics to baseline.
      </p>
    </Card>
  );
}
