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
  // 17 or 18. 0 marks a work from a snapshot taken before the column existed.
  ls_term: number | null;
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
  // '<Work ID>|<ls_term>|<IDA>' — the identity a review is pinned to. Null for
  // rows loaded before the column existed.
  work_key: string | null;
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
  // Agencies are reported per term: a vendor mix in one Lok Sabha says nothing
  // about the other, so the two are not pooled.
  ls_term: number | null;
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

export type MpStat = {
  mp_id: string;
  ls_term: number;
  mp_name: string;
  constituency: string | null;
  state: string | null;
  house: string | null;
  allocated_amount: number | null;
  total_expenditure: number | null;
  utilization_pct: number | null;
  unspent_amount: number | null;
  completion_rate_pct: number | null;
  pending_payments: number | null;
  total_projects: number;
  high_risk_works: number;
};

export type ReviewStatus = "pending" | "verified" | "dismissed" | "escalated";

// One row of the verification queue. Everything a reviewer needs to decide
// whether a work is worth a site visit, without opening a second page.
export type Alert = ProjectDetail & {
  // '<Work ID>|<ls_term>|<IDA>' — see data/load_real_data.py:work_key. This is
  // what a review is pinned to, because `id` is reassigned on every reload.
  work_key: string | null;
  expenditure: number;
  max_similarity_score: number | null;
  review_status: ReviewStatus;
  review_note: string | null;
  review_reviewer: string | null;
  review_updated_at: string | null;
};

// Append-only: one row per decision ever recorded, newest first. work_reviews
// holds only the latest, so this is where an overwritten note survives.
export type ReviewEvent = {
  status: Exclude<ReviewStatus, "pending">;
  note: string | null;
  reviewer: string | null;
  created_at: string;
};

export type ReviewHistory = {
  work_key: string;
  events: ReviewEvent[];
};

export type AlertPage = {
  total: number;
  limit: number;
  offset: number;
  alerts: Alert[];
};

export type AlertSummary = {
  in_scope: number;
  pending: number;
  escalated: number;
  verified: number;
  dismissed: number;
  high: number;
  medium: number;
  pending_sanctioned_amount: number;
};

// A detector describes a population — an agency, an MP — not a work, so these
// never appear in a work's risk score. See data/detectors.py.
export type Detector = {
  code: string;
  name: string;
  subject: "agency" | "mp";
  what: string;
  limit: string;
  findings: number;
  max_severity: number | null;
};

export type DetectorFinding = {
  code: string;
  subject_type: "agency" | "mp";
  subject: string;
  ls_term: number | null;
  // Fiscal year for D-01, null for the rest.
  period: string | null;
  severity: number;
  headline: string;
  evidence: Record<string, unknown>;
};

export type DetectorFindingPage = {
  total: number;
  limit: number;
  offset: number;
  findings: DetectorFinding[];
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
  agencies: (params: Record<string, string> = {}) =>
    get<AgencyStat[]>(`/api/agencies?${new URLSearchParams(params)}`),
  mps: () => get<MpStat[]>("/api/mps"),
  dataFreshness: () => get<DataFreshness>("/api/data-freshness"),
  filters: () => get<FilterOptions>("/api/filters"),
  alerts: (params: Record<string, string> = {}) =>
    get<AlertPage>(`/api/alerts?${new URLSearchParams(params)}`),
  alertSummary: (params: Record<string, string> = {}) =>
    get<AlertSummary>(`/api/alerts/summary?${new URLSearchParams(params)}`),
  detectors: () => get<Detector[]>("/api/detectors"),
  detectorFindings: (params: Record<string, string> = {}) =>
    get<DetectorFindingPage>(`/api/detectors/findings?${new URLSearchParams(params)}`),
  reviewHistory: (workKey: string) =>
    get<ReviewHistory>(`/api/alerts/history?${new URLSearchParams({ work_key: workKey })}`),
};

/** Record a reviewer's decision. Server-side only: it carries REVIEW_TOKEN,
 * which must never reach the browser (hence no NEXT_PUBLIC_ prefix). Called
 * from the server action in app/alerts/actions.ts. */
export async function postReview(body: {
  work_key: string;
  status: Exclude<ReviewStatus, "pending">;
  note?: string;
  reviewer?: string;
}): Promise<void> {
  const token = process.env.REVIEW_TOKEN;
  if (!token) {
    throw new Error(
      "REVIEW_TOKEN is not set on the web server, so reviews cannot be submitted."
    );
  }
  const res = await fetch(`${API_BASE}/api/alerts/review`, {
    method: "POST",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      "X-Review-Token": token,
      ...(API_BYPASS ? { "x-vercel-protection-bypass": API_BYPASS } : {}),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    // Surface the API's own message — "REVIEW_TOKEN is not configured on the
    // server" is a very different problem from a 404, and the UI shows it.
    let detail = `API error ${res.status}`;
    try {
      const parsed = (await res.json()) as { detail?: string };
      if (parsed.detail) detail = parsed.detail;
    } catch {
      /* non-JSON error body; keep the status line */
    }
    throw new Error(detail);
  }
}
