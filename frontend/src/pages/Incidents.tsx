import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { usePoll } from "../lib/usePoll";
import { Card, Badge, fmtMoney, fmtNum, etaText } from "../components/ui";
import MetricChart from "../components/MetricChart";
import type { Incident } from "../lib/types";

function AgentCard({ f }: { f: Incident["findings"][number] }) {
  return (
    <div className="rounded-lg border border-ink-600 bg-ink-700 p-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold capitalize text-slate-200">{f.agent} Agent</span>
        <span className="text-xs text-slate-400">{(f.confidence * 100).toFixed(0)}% conf</span>
      </div>
      <p className="mt-1 text-sm text-slate-300">{f.summary}</p>
      {f.evidence.length > 0 && (
        <ul className="mt-2 space-y-0.5 font-mono text-[11px] text-slate-500">
          {f.evidence.map((e, i) => (
            <li key={i}>· {e}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Detail({ incident }: { incident: Incident }) {
  const [busy, setBusy] = useState(false);
  const plan = incident.plan;
  const proposed = plan && plan.status === "proposed";

  const act = async (kind: "approve" | "reject") => {
    setBusy(true);
    try {
      await (kind === "approve" ? api.approve(incident.id) : api.reject(incident.id));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-xl font-bold text-slate-100">{incident.title}</h2>
        <Badge kind={incident.status} />
        <Badge kind={incident.severity} />
        {incident.auto_remediated && <Badge kind="healthy" text="⚡ Auto-healed" />}
      </div>
      <div className="text-sm text-slate-400">
        {(incident.probability * 100).toFixed(0)}% probability · ETA {etaText(incident.eta_seconds)} ·{" "}
        {incident.incident_type}
      </div>

      {incident.lead_metric && (
        <Card title="Lead Signal">
          <MetricChart
            serviceId={incident.service_id}
            metric={incident.lead_metric}
            label={`${incident.service_id} · ${incident.lead_metric}`}
            threshold={incident.lead_threshold ?? undefined}
            height={160}
          />
        </Card>
      )}

      {incident.impact && (
        <Card title="Business Impact">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-red-300">{fmtNum(incident.impact.affected_users)}</div>
              <div className="text-xs text-slate-400">Affected Users</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-orange-300">{fmtMoney(incident.impact.revenue_at_risk)}</div>
              <div className="text-xs text-slate-400">Revenue at Risk</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-slate-100">{incident.impact.affected_service_ids.length}</div>
              <div className="text-xs text-slate-400">Services in Blast Radius</div>
            </div>
          </div>
          <p className="mt-3 text-center text-sm text-slate-300">{incident.impact.headline}</p>
        </Card>
      )}

      <Card title="Root Cause Analysis">
        {incident.root_cause && (
          <div className="mb-3 rounded-lg border border-accent/30 bg-accent/10 p-3 text-sm text-slate-100">
            <span className="font-semibold text-accent">Root cause: </span>
            {incident.root_cause}
          </div>
        )}
        {incident.diagnosis && (
          <p className="mb-3 whitespace-pre-line text-sm text-slate-300">{incident.diagnosis}</p>
        )}
        <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
          {incident.findings.map((f, i) => (
            <AgentCard key={i} f={f} />
          ))}
        </div>
      </Card>

      {plan && (
        <Card title="Remediation Plan" right={<Badge kind={plan.status === "executed" ? "resolved" : plan.status === "rejected" ? "critical" : "predicted"} text={plan.status} />}>
          <p className="mb-3 text-sm text-slate-300">{plan.rationale}</p>
          <ol className="mb-4 space-y-2">
            {plan.actions.map((a, i) => (
              <li key={a.id} className="flex items-center gap-3 rounded-lg border border-ink-600 bg-ink-700 p-2.5">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-ink-600 text-xs text-slate-300">
                  {i + 1}
                </span>
                <span className="flex-1 text-sm text-slate-200">{a.description}</span>
                <Badge kind={a.risk} text={`${a.kind} · ${a.risk}`} />
              </li>
            ))}
          </ol>
          {proposed ? (
            <div className="flex gap-2">
              <button
                disabled={busy}
                onClick={() => act("approve")}
                className="rounded-lg bg-emerald-500/90 px-4 py-2 text-sm font-semibold text-ink-900 hover:bg-emerald-400 disabled:opacity-50"
              >
                Approve &amp; Execute
              </button>
              <button
                disabled={busy}
                onClick={() => act("reject")}
                className="rounded-lg border border-ink-600 px-4 py-2 text-sm text-slate-300 hover:bg-ink-700 disabled:opacity-50"
              >
                Reject
              </button>
              <span className="self-center text-xs text-slate-500">
                Human approval required · execution is simulated (no real infra touched)
              </span>
            </div>
          ) : (
            <div className="text-sm text-slate-400">
              {plan.status === "executed"
                ? "✓ Remediation executed (simulated). Scenario cleared; metrics recovering."
                : plan.status === "rejected"
                  ? "Plan rejected. Incident remains open."
                  : `Plan ${plan.status}.`}
            </div>
          )}
        </Card>
      )}

      {incident.timeline?.length > 0 && (
        <Card title="Incident Timeline">
          <ol className="relative space-y-3 border-l border-ink-600 pl-4">
            {incident.timeline.map((t, i) => (
              <li key={i} className="relative">
                <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-accent" />
                <div className="flex items-center gap-2">
                  <Badge
                    kind={
                      t.kind === "auto_healed" || t.kind === "resolved"
                        ? "resolved"
                        : t.kind === "breached" || t.kind === "rejected"
                          ? "critical"
                          : "predicted"
                    }
                    text={t.kind}
                  />
                  <span className="text-sm text-slate-300">{t.message}</span>
                </div>
              </li>
            ))}
          </ol>
        </Card>
      )}
    </div>
  );
}

export default function Incidents() {
  const { data: incidents } = usePoll(api.incidents, 1500);
  const [params, setParams] = useSearchParams();
  const selectedId = params.get("id");
  const selected = (incidents ?? []).find((i) => i.id === selectedId) ?? (incidents ?? [])[0];

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-slate-100">Incidents</h1>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[320px_1fr]">
        <div className="space-y-2">
          {(incidents ?? []).length === 0 && (
            <div className="text-sm text-slate-500">No incidents yet. Trigger a scenario from Overview.</div>
          )}
          {(incidents ?? []).map((i) => (
            <button
              key={i.id}
              onClick={() => setParams({ id: i.id })}
              className={`w-full rounded-lg border p-3 text-left ${
                selected?.id === i.id ? "border-accent/60 bg-accent/10" : "border-ink-600 bg-ink-800 hover:border-ink-600"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-100">{i.title}</span>
                <Badge kind={i.status} />
              </div>
              <div className="mt-1 flex gap-2">
                <Badge kind={i.severity} />
                <span className="text-xs text-slate-400">{(i.probability * 100).toFixed(0)}%</span>
              </div>
            </button>
          ))}
        </div>
        <div>
          {selected ? (
            <Detail incident={selected} />
          ) : (
            <Card>
              <div className="text-sm text-slate-500">Select an incident to see RCA, impact, and remediation.</div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
