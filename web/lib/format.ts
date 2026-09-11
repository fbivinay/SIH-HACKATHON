// Shared formatting + risk-color tokens. Later screens (map, projects, analysis)
// should import from here rather than re-implementing money/risk formatting.

/** Indian-format currency abbreviation: ₹1.24 Cr / ₹45.30 L / ₹8,240. */
export function formatINR(amount: number | null | undefined): string {
  if (amount === null || amount === undefined || Number.isNaN(amount)) return "—";
  const abs = Math.abs(amount);
  // Group the mantissa too. At programme scale this reads "₹4,629.50 Cr", and
  // an ungrouped "₹4629.50 Cr" is the kind of number nobody can scan.
  const two = (n: number) =>
    n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (abs >= 1e7) return `₹${two(amount / 1e7)} Cr`;
  if (abs >= 1e5) return `₹${two(amount / 1e5)} L`;
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

// projects.work_status is 'recommended' or 'completed' (see data/load_real_data.py).
// Keep MPLADS' own terminology rather than renaming it — officials reading this
// screen use these words, and "recommended" is not a synonym for "pending".
export function workStatusLabel(status: string | null | undefined): string {
  if (!status) return "—";
  return status.charAt(0).toUpperCase() + status.slice(1);
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
/**
 * Data-freshness timestamps (GET /api/data-freshness) render in IST — the
 * dashboard's whole audience (MPs' offices, districts, oversight bodies) is
 * India-based, and every other timestamp-shaped figure on the site is
 * already Indian-formatted (en-IN locale, ₹ Cr/L). Intl's own "IST" timezone
 * name is ambiguous (India/Israel/Ireland all claim it) and some runtimes
 * render "GMT+5:30" instead, so the label is appended literally.
 */
export function formatFreshnessTimestamp(iso: string | null | undefined): string {
  if (!iso) return "unknown";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "unknown";
  const datePart = new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Kolkata",
  }).format(d);
  const timePart = new Intl.DateTimeFormat("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Kolkata",
  }).format(d);
  return `${datePart}, ${timePart} IST`;
}

export function normalizeStateName(s: string | null | undefined): string {
  if (!s) return "";
  return s
    .toLowerCase()
    .replace(/^the\s+/, "")
    .replace(/&/g, "and")
    .replace(/\s+islands$/, "")
    .replace(/[^a-z]/g, "");
}


/**
 * Sequential ramp for the state choropleth: one hue, light to dark, ending on
 * the risk-high token the rest of the interface already uses.
 *
 * Lightness is monotonic by construction (OKLab L 0.956 → 0.489, every step
 * decreasing), which is the check that applies to a sequential ramp — the
 * categorical rules about hue separation do not, because these are steps of one
 * quantity rather than distinct identities.
 *
 * Keyed on the share of a state's works above the review threshold, not average
 * score: all 36 states average inside the LOW band, so a band-coloured map is a
 * uniform sheet. Share runs 0% to 43.1%.
 */
export const CHOROPLETH_STEPS = [
  { upTo: 5, fill: "#fdecea", label: "under 5%" },
  { upTo: 15, fill: "#f9d2cd", label: "5–15%" },
  { upTo: 25, fill: "#f0a79e", label: "15–25%" },
  { upTo: 35, fill: "#d9695c", label: "25–35%" },
  { upTo: Infinity, fill: "#a82e22", label: "35% and above" },
] as const;

export const NO_DATA_FILL = "#e4e4e7";

export function choroplethFill(share: number | null | undefined): string {
  if (share === null || share === undefined || Number.isNaN(share)) return NO_DATA_FILL;
  return (CHOROPLETH_STEPS.find((s) => share < s.upTo) ?? CHOROPLETH_STEPS[4]).fill;
}

/**
 * Same value as DUPLICATE_SIMILARITY_THRESHOLD in data/scoring.py.
 *
 * Every scored work carries the nearest other work in its district and sector,
 * whatever the distance - 249,933 of 250,839 of them. Only the 102,290 at or
 * above this line are what the system calls a near-duplicate. Showing the link
 * without this check told a reviewer two works resembled each other when the
 * measured similarity was 0.1.
 */
export const DUPLICATE_SIMILARITY_THRESHOLD = 0.94;

export function isNearDuplicate(score: number | null | undefined): boolean {
  return score !== null && score !== undefined && score >= DUPLICATE_SIMILARITY_THRESHOLD;
}
