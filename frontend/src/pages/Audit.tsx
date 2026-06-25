import { api } from "../lib/api";
import { usePoll } from "../lib/usePoll";
import { Card, Badge } from "../components/ui";

export default function Audit() {
  const { data: audit } = usePoll(() => api.audit(200), 2500);

  return (
    <div>
      <h1 className="mb-1 text-[1.75rem] font-medium text-slate-100">Remediation Audit Log</h1>
      <p className="mb-6 text-sm text-slate-400">
        Every executed action — who/what/when, executor, and result. The backbone of
        accountable autonomous operations.
      </p>

      <Card>
        {(audit ?? []).length === 0 && (
          <div className="text-sm text-slate-500">
            No remediations executed yet. Approve a plan or enable self-healing.
          </div>
        )}
        <div className="divide-y divide-ink-600">
          {(audit ?? []).map((a) => (
            <div key={a.id} className="flex items-center gap-3 py-2 text-sm">
              <Badge
                kind={a.result_status === "ok" || a.result_status === "simulated" ? "healthy" : "critical"}
                text={a.result_status}
              />
              <span className="font-mono text-xs text-slate-400">{a.executor}</span>
              <span className="font-medium text-slate-200">{a.action_kind}</span>
              <span className="text-slate-400">→ {a.target_service_id}</span>
              <span className="ml-auto flex items-center gap-2 text-xs text-slate-500">
                <Badge kind={a.actor === "autonomous" ? "predicted" : "low"} text={`${a.actor} (${a.role})`} />
              </span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
