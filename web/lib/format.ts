// Shared formatting + risk-color tokens. Later screens (map, projects, analysis)
// should import from here rather than re-implementing money/risk formatting.

/** Indian-format currency abbreviation: ₹1.24 Cr / ₹45.30 L / ₹8,240. */
export function formatINR(amount: number | null | undefined): string {
  if (amount === null || amount === undefined || Number.isNaN(amount)) return "—";
  const abs = Math.abs(amount);
  if (abs >= 1e7) return `₹${(amount / 1e7).toFixed(2)} Cr`;
  if (abs >= 1e5) return `₹${(amount / 1e5).toFixed(2)} L`;
  return `₹${amount.toLocaleString("en-IN")}`;
}

/** Plain thousands-separated integer, "—" for null/undefined. */
export function formatCount(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toLocaleString("en-IN");
}

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";

/** Normalizes whatever the API sends (case, null) into a known bucket or null. */
export function normalizeRiskLevel(level: string | null | undefined): RiskLevel | null {
  const v = level?.toUpperCase();
  if (v === "LOW" || v === "MEDIUM" || v === "HIGH") return v;
  return null;
}

/** CSS class for a risk pill/badge — pair with the .risk-pill base class. */
export function riskLevelClass(level: string | null | undefined): string {
  const norm = normalizeRiskLevel(level);
  if (norm === "HIGH") return "risk-pill risk-pill--high";
  if (norm === "MEDIUM") return "risk-pill risk-pill--medium";
  if (norm === "LOW") return "risk-pill risk-pill--low";
  return "risk-pill risk-pill--pending";
}

export function riskLevelLabel(level: string | null | undefined): string {
  return normalizeRiskLevel(level) ?? "Pending";
}

// Same thresholds as data/scoring.py RISK_LEVEL_THRESHOLDS (LOW: <40, MEDIUM: <70, HIGH: >=70).
// Hex values match the --risk-* custom properties in globals.css — for contexts (Leaflet
// inline styles, canvas) that can't consume a CSS class.
export function riskScoreToLevel(score: number | null | undefined): RiskLevel | null {
  if (score === null || score === undefined || Number.isNaN(score)) return null;
  if (score >= 70) return "HIGH";
  if (score >= 40) return "MEDIUM";
  return "LOW";
}

export function riskScoreColorHex(score: number | null | undefined): string {
  if (score === null || score === undefined || Number.isNaN(score)) return "#6b7280"; // --risk-pending
  if (score >= 70) return "#ac2b23"; // --risk-high
  if (score >= 40) return "#b3720e"; // --risk-medium
  return "#1e7a4b"; // --risk-low
}

/**
 * Aggregate endpoints (map/states, agencies) COALESCE avg_risk_score to 0 rather than
 * returning null, so a real "everything scored low" state is indistinguishable from
 * "nothing scored yet" at the type level. Heuristic: if every row's avg score AND
 * high-risk/anomaly count is exactly 0 across a non-empty list, treat it as pending —
 * mirrors the overview screen's per-field pending check.
 */
export function isAggregateScoringPending(
  rows: Array<{ avg_risk_score: number }>,
  countField: "high_risk_count" | "delayed_count" | "anomaly_count"
): boolean {
  if (rows.length === 0) return false;
  return rows.every((r) => r.avg_risk_score === 0 && (r as Record<string, number>)[countField] === 0);
}

/**
 * Normalizes a state name for cross-source matching (our DB values vs. a third-party
 * GeoJSON's ST_NM property), which differ on "&" vs "and", a leading "The", and a
 * trailing "Islands" (e.g. DB "Andaman And Nicobar Islands" vs. GeoJSON "Andaman & Nicobar").
 */
export function normalizeStateName(s: string | null | undefined): string {
  if (!s) return "";
  return s
    .toLowerCase()
    .replace(/^the\s+/, "")
    .replace(/&/g, "and")
    .replace(/\s+islands$/, "")
    .replace(/[^a-z]/g, "");
}
