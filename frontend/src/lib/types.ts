export interface Service {
  id: string;
  name: string;
  kind: string;
  tier: number;
  region: string;
  users: number;
  revenue_per_min: number;
}

export interface Dependency {
  source_id: string;
  target_id: string;
  kind: string;
  criticality: number;
}

export interface OverviewRow {
  service: Service;
  metrics: Record<string, number>;
  status: "healthy" | "warning" | "critical";
}

export interface Prediction {
  id: string;
  service_id: string;
  incident_type: string;
  probability: number;
  eta_seconds: number;
  metric: string;
  summary: string;
  features: Record<string, number>;
  created_at: number;
}

export interface AgentFinding {
  agent: string;
  summary: string;
  evidence: string[];
  confidence: number;
  suspected_root_cause?: string | null;
}

export interface ImpactAssessment {
  affected_service_ids: string[];
  affected_users: number;
  revenue_at_risk: number;
  severity: string;
  headline: string;
}

export interface RemediationAction {
  id: string;
  kind: string;
  target_service_id: string;
  description: string;
  risk: string;
}

export interface RemediationPlan {
  id: string;
  incident_id: string;
  actions: RemediationAction[];
  rationale: string;
  status: string;
  requires_approval: boolean;
  approved_by?: string | null;
}

export interface TimelineEntry {
  at: number;
  kind: string;
  message: string;
}

export interface Incident {
  id: string;
  service_id: string;
  incident_type: string;
  status: string;
  severity: string;
  title: string;
  scenario_key?: string | null;
  probability: number;
  eta_seconds: number;
  lead_metric?: string | null;
  lead_threshold?: number | null;
  root_cause?: string | null;
  diagnosis?: string | null;
  findings: AgentFinding[];
  impact?: ImpactAssessment | null;
  plan?: RemediationPlan | null;
  timeline: TimelineEntry[];
  auto_remediated: boolean;
  created_at: number;
  updated_at: number;
}

export interface MetricsSummary {
  active_incidents: number;
  resolved_incidents: number;
  outages_prevented: number;
  auto_healed: number;
  mttr_seconds: number;
  revenue_protected: number;
  predictions: number;
}

export interface Policy {
  auto_remediate: boolean;
  max_auto_risk: string;
}

export interface ScenarioInfo {
  key: string;
  name: string;
  target_service_id: string;
  incident_type: string;
  severity: string;
  active: boolean;
}

export interface TelemetryEvent {
  id: string;
  service_id: string;
  type: string;
  severity: string;
  message: string;
  ts: number;
}

export interface GraphData {
  nodes: { data: Record<string, any> }[];
  edges: { data: Record<string, any> }[];
}
