import { riskScoreColorHex } from "@/lib/format";

// Same weights as RISK_WEIGHTS in data/scoring.py. Duplicated here rather than
// fetched because they are what the bar's widths mean — if they ever diverge,
// the bar would silently misattribute the score.
const WEIGHTS = [
  { key: "cost", label: "cost", weight: 0.25 },
  { key: "delay", label: "delay", weight: 0.25 },
  { key: "duplicate", label: "duplication", weight: 0.2 },
  { key: "agency", label: "agency", weight: 0.15 },
  { key: "compliance", label: "compliance", weight: 0.15 },
] as const;

// One hue, five steps. Five distinct colours would read as five categories of
// risk; these are five parts of one number, so only their order and size
// differ. The legend names them, which is what actually identifies a segment.
const STEPS = [1, 0.8, 0.62, 0.46, 0.32];

export type RiskComponents = {
  cost_risk: number | null;
  delay_risk: number | null;
  duplicate_risk: number | null;
  agency_risk: number | null;
  compliance_risk: number | null;
  overall_risk_score: number | null;
};

/**
 * The five weighted components as one bar. Total fill equals the score, and
 * each segment is that component's contribution to it — so a reviewer can see
 * whether a 72 came from cost or from the implementing agency without opening
 * the work.
 */
export default function RiskBar({ p }: { p: RiskComponents }) {
  if (p.overall_risk_score === null) return null;

  const parts = WEIGHTS.map((w, i) => {
    const raw = p[`${w.key}_risk` as keyof RiskComponents];
    const value = typeof raw === "number" ? raw : 0;
    return { ...w, points: value * w.weight, opacity: STEPS[i] };
  });

  const colour = riskScoreColorHex(p.overall_risk_score);
  const ranked = [...parts].sort((a, b) => b.points - a.points).filter((x) => x.points >= 1);

  return (
    <div>
      <div
        className="riskbar"
        role="img"
        aria-label={`Risk ${p.overall_risk_score.toFixed(0)} of 100, driven by ${
          ranked.length > 0 ? ranked.map((r) => r.label).join(", ") : "no single component"
        }`}
      >
        {parts.map((part) => (
          <span
            key={part.key}
            className="riskbar__seg"
            style={{
              width: `${part.points}%`,
              background: colour,
              opacity: part.opacity,
            }}
          />
        ))}
      </div>
      <div className="riskbar__legend" aria-hidden="true">
        {ranked.length === 0 ? (
          <span>no component above 1 point</span>
        ) : (
          ranked.slice(0, 3).map((r) => (
            <span key={r.key}>
              {r.label} <b>{r.points.toFixed(0)}</b>
            </span>
          ))
        )}
      </div>
    </div>
  );
}
