import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { usePoll } from "../lib/usePoll";
import { Card, Badge, Stat, fmtMoney, fmtNum } from "../components/ui";

export default function Impact() {
  const { data: incidents } = usePoll(api.incidents, 2000);
  const active = (incidents ?? []).filter((i) => i.status !== "resolved" && i.impact);

  const totalUsers = active.reduce((m, i) => Math.max(m, i.impact!.affected_users), 0);
  const totalRevenue = active.reduce((s, i) => s + i.impact!.revenue_at_risk, 0);

  return (
    <div>
      <h1 className="mb-1 text-[1.75rem] font-medium text-slate-100">Executive Impact</h1>
      <p className="mb-6 text-sm text-slate-400">
        Technical incidents translated into business terms.
      </p>

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Stat label="Customers at Risk" value={fmtNum(totalUsers)} />
        <Stat label="Total Revenue at Risk" value={fmtMoney(totalRevenue)} />
        <Stat label="Active Incidents" value={active.length} />
      </div>

      {active.length === 0 && (
        <Card>
          <div className="text-sm text-slate-500">
            No active business impact. All systems nominal.
          </div>
        </Card>
      )}

      <div className="space-y-4">
        {active.map((i) => (
          <Card key={i.id}>
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-semibold text-slate-100">{i.title}</h3>
                  <Badge kind={i.severity} />
                </div>
                <p className="mt-1 max-w-2xl text-sm text-slate-300">{i.impact!.headline}</p>
                <Link to={`/incidents?id=${i.id}`} className="mt-2 inline-block text-xs text-accent">
                  View diagnosis & remediation →
                </Link>
              </div>
              <div className="flex gap-6 text-right">
                <div>
                  <div className="text-3xl font-bold text-red-300">{fmtNum(i.impact!.affected_users)}</div>
                  <div className="text-xs text-slate-400">users</div>
                </div>
                <div>
                  <div className="text-3xl font-bold text-orange-300">{fmtMoney(i.impact!.revenue_at_risk)}</div>
                  <div className="text-xs text-slate-400">at risk</div>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
