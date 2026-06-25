import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Policy } from "../lib/types";

const RISKS = ["low", "medium", "high", "critical"];

export default function AutoHealToggle() {
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.policy().then(setPolicy).catch(() => setError(true));
  }, []);

  const toggle = async () => {
    if (!policy) return;
    try {
      setPolicy(await api.setPolicy({ auto_remediate: !policy.auto_remediate }));
    } catch {
      setError(true);
    }
  };
  const setRisk = async (r: string) => {
    try {
      setPolicy(await api.setPolicy({ max_auto_risk: r }));
    } catch {
      setError(true);
    }
  };

  if (!policy) {
    if (error)
      return (
        <div className="rounded-lg border border-ink-600 bg-ink-800 p-3 text-[11px] text-slate-500">
          Self-healing controls unavailable (backend unreachable).
        </div>
      );
    return null;
  }

  return (
    <div className="rounded-lg border border-ink-600 bg-ink-800 p-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          Self-Healing
        </span>
        <button
          onClick={toggle}
          role="switch"
          aria-checked={policy.auto_remediate}
          aria-label="Toggle autonomous self-healing"
          className={`relative h-5 w-9 rounded-full transition ${
            policy.auto_remediate ? "bg-emerald-500" : "bg-ink-600"
          }`}
        >
          <span
            className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition ${
              policy.auto_remediate ? "left-4" : "left-0.5"
            }`}
          />
        </button>
      </div>
      <div className="mt-1 text-[11px] text-slate-500">
        {policy.auto_remediate
          ? "Autonomous: auto-executing plans within risk limit."
          : "Manual: all remediations need approval."}
      </div>
      {policy.auto_remediate && (
        <div className="mt-2">
          <div className="mb-1 text-[11px] text-slate-500">Max auto-risk</div>
          <div className="flex gap-1">
            {RISKS.map((r) => (
              <button
                key={r}
                onClick={() => setRisk(r)}
                className={`rounded px-1.5 py-0.5 text-[10px] capitalize ${
                  policy.max_auto_risk === r
                    ? "bg-accent/20 text-accent"
                    : "bg-ink-700 text-slate-400 hover:text-slate-200"
                }`}
              >
                {r}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
