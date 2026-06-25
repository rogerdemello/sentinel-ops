import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { usePoll } from "../lib/usePoll";
import { api } from "../lib/api";
import { Badge, Banner } from "./ui";
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
  const { data: health, error: healthError } = usePoll(api.health, 4000);
  const { data: sim } = usePoll(api.simStatus, 3000);

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 flex h-screen w-64 shrink-0 flex-col overflow-y-auto border-r border-ink-600 bg-ink-800/80 p-5 backdrop-blur-sm">
        <div className="mb-8 flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent/12 text-accent shadow-soft">
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round">
              <path d="M12 3l7 3v5c0 4.4-3 7.7-7 9-4-1.3-7-4.6-7-9V6l7-3z" />
              <circle cx="12" cy="10.5" r="1.7" fill="currentColor" stroke="none" />
            </svg>
          </span>
          <div>
            <div className="font-display text-xl leading-none text-slate-100">
              Sentinel<span className="text-accent">Ops</span>
            </div>
            <div className="mt-0.5 text-[10px] uppercase tracking-[0.22em] text-slate-500">
              Autonomous Ops
            </div>
          </div>
        </div>
        <nav className="space-y-0.5">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                `block rounded-xl px-3.5 py-2 text-sm transition-colors duration-200 ${
                  isActive
                    ? "bg-accent/12 font-medium text-accent-deep"
                    : "text-slate-300 hover:bg-ink-700/70 hover:text-slate-100"
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

        <div className="mt-auto space-y-2 pt-6 text-xs text-slate-400">
          <div className="font-semibold uppercase tracking-[0.12em] text-slate-500">Engine</div>
          <div className="flex items-center gap-2">
            <span
              className={`h-2 w-2 rounded-full ${sim?.running ? "bg-emerald-400 animate-pulse-soft" : "bg-slate-500"}`}
            />
            Simulator {sim?.running ? "running" : "stopped"} · {sim?.ticks ?? 0} ticks
          </div>
          <div className="pt-2 font-semibold uppercase tracking-[0.12em] text-slate-500">
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
        <div className="mx-auto max-w-7xl p-6">
          {healthError && (
            <Banner kind="error">
              Cannot reach the SentinelOps backend ({healthError}). Is it running on
              port 8000? Showing the last known data.
            </Banner>
          )}
          {children}
        </div>
      </main>
    </div>
  );
}
