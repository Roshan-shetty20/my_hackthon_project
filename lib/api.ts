
export interface RouteOption {
  route_id: string;
  name: string;
  waypoints: number[][];
  road_segments: string[];
  distance_km: number;
  eta_minutes: number;
  status: string;
  blocked?: boolean;
  reason?: string;
}

export interface DispatchMission {
  mission_id: string;
  unit_id: string;
  incident_id: string;
  route_id: string;
  status: string;
  progress_percent: number;
  current_latitude: number;
  current_longitude: number;
  destination_latitude: number;
  destination_longitude: number;
  eta_minutes: number;
  distance_remaining_km: number;
  route?: RouteOption;
}

// Crisis Command API client
// All backend communication goes through this module.
// Change NEXT_PUBLIC_API_URL to point at your deployed backend.

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Types ────────────────────────────────────────────────────────────────

export interface Incident {
  id: string;
  type: string;
  location: string;
  latitude: number;
  longitude: number;
  people_affected: number;
  people_trapped: number;
  vulnerable_people: number;
  life_threat: boolean;
  time_critical: boolean;
  spreading_hazard: boolean;
  required_units: Record<string, number>;
  status: string;
  severity: number | null;

  urgency: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | null;
  assessment?: {
    incident_type: string;
    severity: number;
    urgency: string;
    confidence: string;
    risk_factors: string[];
    missing_information: string[];
    predicted_resource_demand: Record<string, number>;
  };
  escalation_prediction?: {
    current_severity: number;
    escalation_risk: string;
    possible_severity_range: string;
    prediction_horizon: string;
    major_risk_drivers: string[];
    uncertainty: string;
  };

}

export interface Unit {
  id: string;
  type: string;
  status: string;
  capacity: number;
  latitude: number;
  longitude: number;
  current_incident: string | null;
  capabilities: string[];
}

export interface RoadCondition {
  id: string;
  name: string;
  from_lat: number;
  from_lon: number;
  to_lat: number;
  to_lon: number;
  distance_km: number;
  blocked: boolean;
  delay_minutes: number;
  reason: string | null;
}

export interface Assignment {
  incident_id: string;
  unit_id: string;
  eta_minutes: number;
}

export interface ValidationResult {
  valid: boolean;
  violations: { type: string; message: string; unit?: string; incident?: string }[];
}

export interface PlanMetrics {
  critical_covered: number;
  high_covered: number;
  medium_covered: number;
  low_covered: number;
  total_covered: number;
  total_incidents: number;
  uncovered_incidents: string[];
  average_eta: number;
  max_eta: number;
  reserve_units: number;
  resilience_score: number;
  fragility_index: number;
  human_attention_required: boolean;
  attention_reasons: string[];
}

export interface Plan {
  id: string;
  strategy_name: string;
  state_version: number;
  assignments: Assignment[];
  validation: ValidationResult | null;
  metrics: PlanMetrics | null;
  score: number | null;
  explanation: string;
  ai_explanation: Record<string, unknown> | null;
}

export interface ResilienceResult {
  plan_id: string;
  resilience_score: number;
  fragility_index: number;
  worst_case_unit: string | null;
  worst_case_impact: {
    scenario: { type: string; target_id: string; description: string };
    plan_still_valid: boolean;
    affected_incidents: string[];
    uncovered_incidents: string[];
    eta_increase_minutes: number;
    severity_impact: string;
  } | null;
  single_points_of_failure: string[];
  scenarios_tested: number;
  scenario_results: {
    scenario: { type: string; target_id: string; description: string };
    plan_still_valid: boolean;
    affected_incidents: string[];
    uncovered_incidents: string[];
    eta_increase_minutes: number;
    severity_impact: string;
  }[];
}

export interface PlanDiff {
  before_plan_id: string;
  after_plan_id: string;
  added_assignments: Assignment[];
  removed_assignments: Assignment[];
  changed_units: {
    incident: string;
    before_unit: string;
    after_unit: string;
    before_eta: number;
    after_eta: number;
  }[];
  newly_uncovered: string[];
  newly_covered: string[];
  eta_changes: Record<string, number>;
  explanation: string;
  trigger: string;
  reallocation_reasons: {
    incident_id: string;
    previous_unit: string;
    new_unit: string;
    trigger: string;
    reason_for_change: string;
    eta_impact: number;
  }[];
}

export interface ActionLogEntry {
  timestamp: string;
  version: number;
  agent: string;
  action: string;
  details: string;
}

export interface DecisionConfidence {
  level: "HIGH" | "MEDIUM" | "LOW";
  factors: { label: string; passed: boolean; detail: string }[];
  passed_count: number;
  total_count: number;
}

export interface DecisionDebt {
  unit_id: string;
  dependent_incident_ids: string[];
  is_spof: boolean;
  description: string;
  failure_impact: string;
}

export type DemoStage =
  | "RECEIVE"
  | "ALLOCATE"
  | "COMPARE"
  | "RECOMMEND"
  | "REPLAN_REVIEW"
  | "POST_DISRUPTION"
  | "ACTIVE";

export interface CrisisStateResponse {
  version: number;
  stage: DemoStage;
  incidents: Incident[];
  units: Unit[];
  road_conditions: RoadCondition[];
  candidate_plans: Plan[];
  recommended_plan: Plan | null;
  approved_plan: Plan | null;
  resilience_results: Record<string, ResilienceResult>;
  plan_diffs: PlanDiff[];
  action_log: ActionLogEntry[];
  system_events: { id: string; type: string; target_id: string; description: string; timestamp: string }[];
  decision_confidence: DecisionConfidence | null;
  decision_debts: DecisionDebt[];
  latest_impact_analysis: any | null;
  active_missions: Record<string, DispatchMission>;
}

export interface ExplanationResponse {
  gemini_status: "connected" | "degraded";
  explanation_source: "gemini" | "deterministic_fallback";
  why: string;
  tradeoff: string;
  risk: string;
  what_changed: string;
  summary: string;
  why_not?: Record<string, string>;
  boundary_note: string;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
  sessions_active: number;
  integrations: {
    gemini: string;
    openrouteservice: string;
    open_meteo: string;
    dijkstra: string;
  };
}

// ─── Fetcher utility ──────────────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ─── API calls ────────────────────────────────────────────────────────────

export const api = {
  health: () => apiFetch<HealthResponse>("/health"),

  createSession: () =>
    apiFetch<{ session_id: string; version: number; stage: DemoStage; message: string }>(
      "/session",
      { method: "POST" }
    ),

  resetSession: (sid: string) =>
    apiFetch<{ session_id: string; version: number; stage: DemoStage }>(`/session/${sid}/reset`, { method: "POST" }),

  getState: (sid: string) => apiFetch<CrisisStateResponse>(`/session/${sid}/state`),

  replan: (sid: string) =>
    apiFetch<{ status: string; version: number; stage: DemoStage; plans: Plan[]; recommended_plan: Plan | null; plan_diffs: PlanDiff[]; changed: boolean }>(`/session/${sid}/replan`, { method: "POST" }),

  generatePlans: (sid: string) =>
    apiFetch<{
      version: number; stage: DemoStage;
      plans: Plan[]; recommended_plan: Plan | null;
      resilience_results: Record<string, ResilienceResult>;
    }>(`/session/${sid}/generate-plans`, { method: "POST" }),

  approvePlan: (sid: string, planId: string) =>
    apiFetch<{ status: string; plan_id: string; strategy: string; version: number }>(
      `/session/${sid}/approve`,
      { method: "POST", body: JSON.stringify({ plan_id: planId }) }
    ),

  rejectPlan: (sid: string) =>
    apiFetch<{ status: string; version: number }>(`/session/${sid}/reject`, { method: "POST" }),

  breakdown: (sid: string, unitId: string) =>
    apiFetch<{ status: string; version: number; stage: DemoStage; impact: unknown }>(
      `/session/${sid}/events/breakdown`,
      { method: "POST", body: JSON.stringify({ unit_id: unitId }) }
    ),

  roadBlock: (sid: string, roadId: string) =>
    apiFetch<{ status: string; version: number; stage: DemoStage; impact: unknown }>(
      `/session/${sid}/events/road-block`,
      { method: "POST", body: JSON.stringify({ road_id: roadId }) }
    ),

  newIncident: (sid: string, inc: {
    id: string; type: string; location: string;
    latitude: number; longitude: number;
    people_affected?: number; people_trapped?: number;
    life_threat?: boolean; time_critical?: boolean; spreading_hazard?: boolean;
    required_units?: Record<string, number>;
  }) =>
    apiFetch<{ status: string; version: number; stage: DemoStage; impact: unknown }>(
      `/session/${sid}/events/new-incident`,
      { method: "POST", body: JSON.stringify(inc) }
    ),


  tickTime: (sid: string) =>
    apiFetch<CrisisStateResponse>(`/session/${sid}/tick`, {
      method: "POST",
    }),

  batchEvents: (sid: string, events: Array<{event_type: string; payload: Record<string, unknown>}>) =>
    apiFetch<{ status: string; events_applied: number; version: number; stage: DemoStage; impact: unknown }>(
      `/session/${sid}/events`,
      { method: 'POST', body: JSON.stringify({ events }) }
    ),


  simulateStep: (sid: string) =>
    apiFetch<{
      event: { event_type: string; payload: Record<string, unknown> };
      version: number; stage: DemoStage; events_remaining: number; impact: unknown;
    }>(`/session/${sid}/simulate-step`, { method: "POST" }),

  getExplanation: (sid: string) => apiFetch<ExplanationResponse>(`/session/${sid}/explanation`),

  getTimeline: (sid: string) =>
    apiFetch<{ action_log: ActionLogEntry[]; system_events: unknown[]; version: number }>(
      `/session/${sid}/timeline`
    ),

  getPlanDiff: (sid: string) =>
    apiFetch<{ plan_diffs: PlanDiff[]; count: number }>(`/session/${sid}/plan-diff`),
};
