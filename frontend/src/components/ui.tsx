import type { ReactNode } from "react";

export function Card({
  title,
  children,
  className = "",
  right,
}: {
  title?: string;
  children: ReactNode;
  className?: string;
  right?: ReactNode;
}) {
  return (
    <div
      className={`animate-fade-up rounded-2xl border border-ink-600 bg-ink-800 shadow-card ${className}`}
    >
      {title && (
        <div className="flex items-center justify-between border-b border-ink-600/70 px-5 py-3">
          <h3 className="text-[13px] font-semibold uppercase tracking-wide text-slate-400">
            {title}
          </h3>
          {right}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}

const SEVERITY: Record<string, string> = {
  critical: "bg-red-500/15 text-red-300 border-red-500/30",
  high: "bg-orange-500/15 text-orange-300 border-orange-500/30",
  medium: "bg-yellow-500/15 text-yellow-300 border-yellow-500/30",
  low: "bg-sky-500/15 text-sky-300 border-sky-500/30",
};

const STATUS: Record<string, string> = {
  healthy: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  warning: "bg-yellow-500/15 text-yellow-300 border-yellow-500/30",
  critical: "bg-red-500/15 text-red-300 border-red-500/30",
  predicted: "bg-violet-500/15 text-violet-300 border-violet-500/30",
  active: "bg-red-500/15 text-red-300 border-red-500/30",
  mitigating: "bg-sky-500/15 text-sky-300 border-sky-500/30",
  resolved: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
};

export function Badge({ kind, text }: { kind: string; text?: string }) {
  const cls = SEVERITY[kind] ?? STATUS[kind] ?? "bg-ink-600 text-slate-300 border-ink-600";
  return (
    <span className={`inline-block rounded-md border px-2 py-0.5 text-xs font-medium ${cls}`}>
      {text ?? kind}
    </span>
  );
}

export function StatusDot({ status }: { status: string }) {
  const critical = status === "critical" || status === "active";
  const warn = status === "warning" || status === "predicted" || status === "mitigating";
  const color = critical ? "bg-red-400" : warn ? "bg-amber-400" : "bg-emerald-400";
  return (
    <span className="relative inline-flex h-2.5 w-2.5">
      {critical && (
        <span className="absolute inline-flex h-full w-full animate-pulse-soft rounded-full bg-red-400/50" />
      )}
      <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${color}`} />
    </span>
  );
}

export function Stat({ label, value, sub }: { label: string; value: ReactNode; sub?: ReactNode }) {
  return (
    <div className="animate-fade-up rounded-2xl border border-ink-600 bg-ink-800 p-5 shadow-card transition-shadow duration-300 hover:shadow-lift">
      <div className="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">
        {label}
      </div>
      <div className="mt-1.5 font-display text-[1.85rem] leading-none text-slate-100">{value}</div>
      {sub && <div className="mt-2 text-xs text-slate-400">{sub}</div>}
    </div>
  );
}

/** Pulsing placeholder shown while first data is loading. */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-ink-700 ${className}`} />;
}

/** A grid of stat-sized skeletons (used before the first poll resolves). */
export function StatSkeletons({ count = 4 }: { count?: number }) {
  return (
    <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} className="h-[88px]" />
      ))}
    </div>
  );
}

/** Friendly empty state with an optional call-to-action. */
export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string;
  hint?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-ink-600 bg-ink-800/50 px-6 py-10 text-center">
      <div className="text-sm font-medium text-slate-300">{title}</div>
      {hint && <div className="max-w-md text-xs text-slate-500">{hint}</div>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

/** Inline banner for connection / error feedback. */
export function Banner({
  kind = "error",
  children,
}: {
  kind?: "error" | "warning" | "info";
  children: ReactNode;
}) {
  const cls =
    kind === "error"
      ? "border-red-500/40 bg-red-500/10 text-red-200"
      : kind === "warning"
        ? "border-yellow-500/40 bg-yellow-500/10 text-yellow-200"
        : "border-sky-500/40 bg-sky-500/10 text-sky-200";
  return (
    <div role="alert" className={`mb-4 flex items-center gap-2 rounded-lg border px-3 py-2 text-sm ${cls}`}>
      <span aria-hidden className="h-2 w-2 shrink-0 rounded-full bg-current" />
      <span>{children}</span>
    </div>
  );
}

export function fmtMoney(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

export function fmtNum(n: number): string {
  return n.toLocaleString();
}

export function etaText(seconds: number): string {
  if (seconds <= 0) return "now";
  const m = Math.round(seconds / 60);
  if (m < 60) return `~${m} min`;
  return `~${(m / 60).toFixed(1)} h`;
}
