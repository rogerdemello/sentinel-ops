import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { usePoll } from "../lib/usePoll";
import { Card, Stat, Badge, StatusDot, fmtMoney, fmtNum, etaText } from "../components/ui";
import ScenarioBar from "../components/ScenarioBar";
import MetricChart from "../components/MetricChart";

export default function Overview() {
  const { data: overview } = usePoll(api.overview, 2000);
  const { data: incidents } = usePoll(api.incidents, 2000);
  const { data: predictions } = usePoll(api.predictions, 2000);
  const { data: events } = usePoll(() => api.events(12), 2500);
  const { data: kpi } = usePoll(api.metricsSummary, 2500);
  const { data: evalReport } = usePoll(api.evalReport, 10000);

  const active = (incidents ?? []).filter((i) => i.status !== "resolved");
  const topPred = (predictions ?? [])[0];
  const healthy = (overview ?? []).filter((s) => s.status === "healthy").length;
  const total = (overview ?? []).length;
  const revenueAtRisk = active.reduce((sum, i) => sum + (i.impact?.revenue_at_risk ?? 0), 0);

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold text-slate-100">Live Operations</h1>
      <p className="mb-6 text-sm text-slate-400">
        Predict → Diagnose → Impact → Remediate, autonomously.
      </p>

      <ScenarioBar />

      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Active Incidents" value={active.length} sub={`${total - healthy}/${total} services degraded`} />
        <Stat
          label="Top Prediction"
          value={topPred ? `${(topPred.probability * 100).toFixed(0)}%` : "—"}
          sub={topPred ? `${topPred.incident_type} · ${etaText(topPred.eta_seconds)}` : "no risk detected"}
        />
        <Stat label="Revenue at Risk" value={fmtMoney(revenueAtRisk)} sub="across active incidents" />
        <Stat label="Services Healthy" value={`${healthy}/${total}`} />
      </div>

      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Outages Prevented" value={kpi?.outages_prevented ?? 0} sub="resolved before breach" />
        <Stat label="Auto-Healed" value={kpi?.auto_healed ?? 0} sub="autonomous remediations" />
        <Stat
          label="Mean Time to Resolve"
          value={kpi ? `${(kpi.mttr_seconds / 60).toFixed(0)}m` : "—"}
          sub="simulated"
        />
        <Stat label="Revenue Protected" value={fmtMoney(kpi?.revenue_protected ?? 0)} sub="resolved incidents" />
      </div>

      {evalReport?.available && (
        <Card title="Model Performance (offline evaluation)" className="mb-6">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Stat label="Recall" value={`${(evalReport.recall * 100).toFixed(0)}%`} sub={`${evalReport.detected}/${evalReport.scenarios} detected`} />
            <Stat label="Precision" value={`${(evalReport.precision * 100).toFixed(0)}%`} sub={`${evalReport.false_positives_baseline} false positives`} />
            <Stat label="Early Warning" value={`${(evalReport.early_warning_rate * 100).toFixed(0)}%`} sub="before breach" />
            <Stat label="Mean Lead Time" value={evalReport.mean_lead_time_min != null ? `${evalReport.mean_lead_time_min} min` : "—"} />
          </div>
        </Card>
      )}

      <Card title="Live Signals" className="mb-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <MetricChart serviceId="gateway" metric="latency_p95_ms" label="API Gateway latency (p95)" threshold={1500} />
          <MetricChart serviceId="orders_db" metric="db_pool_used_pct" label="Orders DB pool used %" threshold={95} color="#a78bfa" />
          <MetricChart serviceId="auth" metric="auth_failures_per_min" label="Auth failures / min" threshold={800} color="#f59e0b" />
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card title="Service Health" className="lg:col-span-2">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {(overview ?? [])
              .filter((s) => s.service.id !== "user")
              .map((s) => (
                <div
                  key={s.service.id}
                  className="flex items-center justify-between rounded-lg border border-ink-600 bg-ink-700 px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <StatusDot status={s.status} />
                    <span className="text-sm text-slate-200">{s.service.name}</span>
                  </div>
                  <span className="text-xs text-slate-400">
                    {s.metrics["cpu_pct"] != null ? `cpu ${s.metrics["cpu_pct"].toFixed(0)}%` : ""}
                  </span>
                </div>
              ))}
          </div>
        </Card>

        <Card title="Active Incidents">
          {active.length === 0 && <div className="text-sm text-slate-500">No active incidents.</div>}
          <div className="space-y-2">
            {active.map((i) => (
              <Link
                key={i.id}
                to={`/incidents?id=${i.id}`}
                className="block rounded-lg border border-ink-600 bg-ink-700 p-3 hover:border-accent/50"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-100">{i.title}</span>
                  <Badge kind={i.status} />
                </div>
                <div className="mt-1 flex items-center gap-2 text-xs text-slate-400">
                  <Badge kind={i.severity} />
                  <span>{(i.probability * 100).toFixed(0)}% · {etaText(i.eta_seconds)}</span>
                  {i.impact && <span>· {fmtNum(i.impact.affected_users)} users</span>}
                </div>
              </Link>
            ))}
          </div>
        </Card>
      </div>

      <Card title="Recent Telemetry Events" className="mt-6">
        <div className="space-y-1 font-mono text-xs">
          {(events ?? []).map((e) => (
            <div key={e.id} className="flex gap-3">
              <Badge kind={e.severity === "critical" || e.severity === "error" ? "critical" : e.severity === "warning" ? "warning" : "low"} text={e.severity} />
              <span className="text-slate-500">{e.service_id}</span>
              <span className="text-slate-300">{e.message}</span>
            </div>
          ))}
          {(events ?? []).length === 0 && <div className="text-slate-500">No events yet.</div>}
        </div>
      </Card>
    </div>
  );
}
