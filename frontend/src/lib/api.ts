import axios from "axios";
import type {
  AuditEntry,
  GraphData,
  Incident,
  MetricsSummary,
  OverviewRow,
  Policy,
  Prediction,
  ScenarioInfo,
  Service,
  Dependency,
  TelemetryEvent,
} from "./types";

const client = axios.create({ baseURL: "" });

export interface Health {
  status: string;
  app: string;
  environment: string;
  sim_time: number;
  services: number;
  capabilities: {
    supabase: boolean;
    azure_openai: boolean;
    gemini: boolean;
    llm: boolean;
  };
}

export const api = {
  health: () => client.get<Health>("/health").then((r) => r.data),

  overview: () =>
    client.get<{ services: OverviewRow[] }>("/api/telemetry/overview").then((r) => r.data.services),

  events: (limit = 40) =>
    client
      .get<{ events: TelemetryEvent[] }>(`/api/telemetry/events?limit=${limit}`)
      .then((r) => r.data.events),

  series: (serviceId: string, metric: string, limit = 120) =>
    client
      .get<{ points: { ts: number; value: number }[] }>(
        `/api/telemetry/series?service_id=${serviceId}&metric=${metric}&limit=${limit}`,
      )
      .then((r) => r.data.points),

  graph: () =>
    client
      .get<{ graph: GraphData; services: Service[]; dependencies: Dependency[] }>("/api/graph")
      .then((r) => r.data),

  predictions: () =>
    client.get<{ predictions: Prediction[] }>("/api/predictions").then((r) => r.data.predictions),

  incidents: () =>
    client.get<{ incidents: Incident[] }>("/api/incidents").then((r) => r.data.incidents),

  incident: (id: string) =>
    client
      .get<{ incident: Incident; blast_radius: { service_id: string; criticality: number }[] }>(
        `/api/incidents/${id}`,
      )
      .then((r) => r.data),

  scenarios: () =>
    client.get<{ scenarios: ScenarioInfo[] }>("/api/scenarios").then((r) => r.data.scenarios),

  triggerScenario: (key: string) =>
    client.post(`/api/scenarios/${key}/trigger`).then((r) => r.data),

  clearScenario: (key: string) => client.post(`/api/scenarios/${key}/clear`).then((r) => r.data),

  approve: (incidentId: string) =>
    client.post(`/api/remediation/${incidentId}/approve`).then((r) => r.data),

  reject: (incidentId: string) =>
    client.post(`/api/remediation/${incidentId}/reject`).then((r) => r.data),

  simStatus: () =>
    client
      .get<{ running: boolean; ticks: number; sim_time: number }>("/api/sim/status")
      .then((r) => r.data),

  metricsSummary: () =>
    client.get<MetricsSummary>("/api/metrics/summary").then((r) => r.data),

  policy: () => client.get<Policy>("/api/policy").then((r) => r.data),

  setPolicy: (body: Partial<Policy>) =>
    client.put<Policy>("/api/policy", body).then((r) => r.data),

  postmortem: (incidentId: string) =>
    client
      .post<{ postmortem: string }>(`/api/postmortem/${incidentId}`)
      .then((r) => r.data.postmortem),

  audit: (limit = 100) =>
    client.get<{ audit: AuditEntry[] }>(`/api/audit?limit=${limit}`).then((r) => r.data.audit),
};
