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
    <div className={`rounded-xl border border-ink-600 bg-ink-800 ${className}`}>
      {title && (
        <div className="flex items-center justify-between border-b border-ink-600 px-4 py-2.5">
          <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
          {right}
        </div>
      )}
      <div className="p-4">{children}</div>
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
  const color =
    status === "critical" || status === "active"
      ? "bg-red-400"
      : status === "warning" || status === "predicted" || status === "mitigating"
        ? "bg-yellow-400"
        : "bg-emerald-400";
  return <span className={`inline-block h-2.5 w-2.5 rounded-full ${color}`} />;
}

export function Stat({ label, value, sub }: { label: string; value: ReactNode; sub?: ReactNode }) {
  return (
    <div className="rounded-xl border border-ink-600 bg-ink-800 p-4">
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-100">{value}</div>
      {sub && <div className="mt-1 text-xs text-slate-400">{sub}</div>}
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
