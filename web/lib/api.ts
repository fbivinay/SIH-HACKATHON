const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type Overview = {
  total_projects: number;
  total_expenditure: number;
  high_risk_count: number;
  delayed_count: number;
  anomaly_count: number;
};

export type ProjectSummary = {
  id: number;
  work_name: string;
  state: string;
  district: string;
  category: string;
  implementing_agency: string;
  sanctioned_amount: number;
  overall_risk_score: number | null;
  risk_level: string | null;
};

// Note on nullability vs. the task brief: `SELECT *` on `projects` returns every
// scoring column, and per data/schema.sql none of cost_risk/delay_risk/duplicate_risk/
// agency_risk/compliance_risk/delay_days/cost_deviation_pct carry a NOT NULL constraint
// — they are NULL until the scoring pass runs (currently in progress over 127k rows).
// description/mp_name/constituency are likewise nullable text columns in the schema.
// The brief typed these as non-nullable; corrected here so callers must handle null.
export type ProjectDetail = ProjectSummary & {
  description: string | null;
  mp_name: string | null;
  constituency: string | null;
  work_status: string | null;
  cost_risk: number | null;
  delay_risk: number | null;
  duplicate_risk: number | null;
  agency_risk: number | null;
  compliance_risk: number | null;
  flagged_reasons: string[];
  delay_days: number | null;
  cost_deviation_pct: number | null;
  similar_work_id: number | null;
};

export type StateStat = {
  state: string;
  total_projects: number;
  high_risk_count: number;
  avg_risk_score: number;
};

export type AgencyStat = {
  implementing_agency: string;
  total_projects: number;
  delayed_count: number;
  anomaly_count: number;
  avg_risk_score: number;
};

// If the API's own Vercel deployment is behind Vercel Deployment Protection,
// set API_PROTECTION_BYPASS (server-only env var, not NEXT_PUBLIC_) to that
// project's automation bypass secret so server-side fetches aren't redirected
// to the SSO login page. No-op once the API is public.
const API_BYPASS = process.env.API_PROTECTION_BYPASS;

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    headers: API_BYPASS ? { "x-vercel-protection-bypass": API_BYPASS } : undefined,
  });
  if (!res.ok) throw new Error(`API error ${res.status} on ${path}`);
  return res.json();
}

export const api = {
  overview: () => get<Overview>("/api/overview"),
  projects: (params: Record<string, string> = {}) =>
    get<ProjectSummary[]>(`/api/projects?${new URLSearchParams(params)}`),
  project: (id: number) => get<ProjectDetail>(`/api/projects/${id}`),
  mapStates: () => get<StateStat[]>("/api/map/states"),
  agencies: () => get<AgencyStat[]>("/api/agencies"),
};
