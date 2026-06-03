import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { usePoll } from "../lib/usePoll";
import { api } from "../lib/api";
import { Badge } from "./ui";
import AutoHealToggle from "./AutoHealToggle";

const NAV = [
  { to: "/", label: "Overview", end: true },
  { to: "/predictions", label: "Predictions" },
  { to: "/incidents", label: "Incidents" },
  { to: "/graph", label: "Dependency Graph" },
  { to: "/impact", label: "Executive Impact" },
  { to: "/audit", label: "Audit Log" },
  { to: "/copilot", label: "Ops Copilot" },
];

export default function Layout({ children }: { children: ReactNode }) {
  const { data: health } = usePoll(api.health, 4000);
  const { data: sim } = usePoll(api.simStatus, 3000);

  return (
    <div className="flex min-h-screen">
      <aside className="w-60 shrink-0 border-r border-ink-600 bg-ink-900 p-4">
        <div className="mb-6">
          <div className="text-lg font-bold text-slate-100">
            Sentinel<span className="text-accent">Ops</span>
          </div>
          <div className="text-[11px] uppercase tracking-widest text-slate-500">
            Autonomous Ops AI
          </div>
        </div>
        <nav className="space-y-1">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                `block rounded-lg px-3 py-2 text-sm ${
                  isActive
                    ? "bg-accent/15 text-accent"
                    : "text-slate-300 hover:bg-ink-700"
                }`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-6">
          <AutoHealToggle />
        </div>

        <div className="mt-6 space-y-2 text-xs text-slate-400">
          <div className="font-semibold uppercase tracking-wide text-slate-500">Engine</div>
          <div className="flex items-center gap-2">
            <span
              className={`h-2 w-2 rounded-full ${sim?.running ? "bg-emerald-400" : "bg-slate-500"}`}
            />
            Simulator {sim?.running ? "running" : "stopped"} · {sim?.ticks ?? 0} ticks
          </div>
          <div className="font-semibold uppercase tracking-wide text-slate-500 pt-2">
            AI Providers
          </div>
          <div className="flex flex-wrap gap-1">
            <Badge kind={health?.capabilities.azure_openai ? "healthy" : "low"} text="Azure OpenAI" />
            <Badge kind={health?.capabilities.gemini ? "healthy" : "low"} text="Gemini" />
          </div>
          {!health?.capabilities.llm && (
            <div className="text-[11px] text-slate-500">
              No LLM key set — using heuristic RCA.
            </div>
          )}
          <div className="flex flex-wrap gap-1 pt-1">
            <Badge kind={health?.capabilities.supabase ? "healthy" : "low"} text="Supabase" />
          </div>
        </div>
      </aside>

      <main className="flex-1 bg-ink-900">
        <div className="mx-auto max-w-7xl p-6">{children}</div>
      </main>
    </div>
  );
}
