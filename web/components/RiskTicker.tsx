import Link from "next/link";
import { api } from "@/lib/api";
import { formatCount, formatINR } from "@/lib/format";

/**
 * The highest-scoring works, scrolling under the masthead.
 *
 * A queue of 47,719 is a number nobody feels. This puts the actual works in
 * front of whoever opens the site — named, scored, one click from the evidence.
 *
 * Server-rendered and animated in CSS: no JavaScript ships for this, the marquee
 * cannot desynchronise, and it degrades to a scrollable strip when the reader
 * has asked for reduced motion.
 *
 * A score is not an allegation (CLAUDE.md §1), so the strip says "worth a look"
 * rather than anything stronger, and every row links to the page that shows the
 * peer comparison behind the number.
 */

// Enough to read as continuous at any viewport, few enough that the duplicated
// track stays cheap. The row is ~320px, so 18 gives ~5,800px per copy.
const COUNT = 18;

// HIGH starts at 70 (RISK_LEVEL_THRESHOLDS in data/scoring.py). Asking for the
// band by name as well as the score means this keeps meaning "high risk" if the
// threshold is ever recalibrated.
const HIGH_SCORE = "70";

export default async function RiskTicker() {
  let alerts;
  try {
    const page = await api.alerts({
      risk_level: "HIGH",
      min_score: HIGH_SCORE,
      limit: String(COUNT),
    });
    alerts = page.alerts;
  } catch {
    // The masthead must not fail with the API. A missing ticker is invisible;
    // a thrown render is the whole site.
    return null;
  }
  if (!alerts?.length) return null;

  const items = alerts.map((a) => {
    const score = a.overall_risk_score;
    return (
      <Link
        key={a.work_key ?? a.id}
        href={`/projects/${encodeURIComponent(a.work_key ?? String(a.id))}`}
        className="ticker__item"
      >
        <span className="ticker__score">{score === null ? "—" : score.toFixed(0)}</span>
        <span className="ticker__name">{a.work_name}</span>
        <span className="ticker__meta">
          {a.district}
          {a.sanctioned_amount ? ` · ${formatINR(a.sanctioned_amount)}` : ""}
        </span>
      </Link>
    );
  });

  return (
    <div className="ticker">
      <span className="ticker__label">
        Highest risk
        <span className="ticker__count">{formatCount(alerts.length)} shown</span>
      </span>
      <div className="ticker__viewport">
        {/* Two identical copies. The track translates exactly -50%, so the
            second copy lands where the first began and the loop has no seam.
            The copy is aria-hidden so a screen reader hears each work once. */}
        <div className="ticker__track">
          <div className="ticker__set">{items}</div>
          <div className="ticker__set" aria-hidden="true">
            {items}
          </div>
        </div>
      </div>
      <Link href="/alerts?risk_level=HIGH" className="ticker__all">
        All high risk
      </Link>
    </div>
  );
}
