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
