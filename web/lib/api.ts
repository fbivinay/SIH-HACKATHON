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
  // Derived from the work description (data/sectors.py). `category` is
  // 'Normal/Others' for 98.1% of works, so `sector` is the one that carries
  // information. Nullable: rows scored before sector existed have none.
  sector: string | null;
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
  peer_median_cost: number | null;
  peer_count: number | null;
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
  // From agency_vendor_profile (data/vendors.py). Null for an agency with no
  // expenditure rows — the join is a LEFT one, so those agencies still appear.
  vendor_count: number | null;
  transaction_count: number | null;
  total_spend: number | null;
  top_vendor: string | null;
  top_vendor_share_pct: number | null;
  concentration_risk: number;
};

export type FilterOptions = {
  states: Array<{ state: string; count: number }>;
  risk_levels: string[];
};

// Empty object when no successful run has ever completed (see
// GET /api/data-freshness in api/main.py) - every field is then absent.
export type DataFreshness = {
  finished_at?: string;
  rows_loaded?: number;
  rows_scored?: number;
  rows_rejected?: number;
  source?: string;
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
  dataFreshness: () => get<DataFreshness>("/api/data-freshness"),
  filters: () => get<FilterOptions>("/api/filters"),
};
