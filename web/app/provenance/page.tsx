import { api } from "@/lib/api";
import { formatCount } from "@/lib/format";
import WhereTheAI from "@/components/WhereTheAI";
import ArchitectureFlow from "@/components/ArchitectureFlow";

export const metadata = { title: "Sources" };

// Two points per detector (owner's call, 2026-09-21): what it measures, and
// what it does not claim. The second is the one that must survive any cut - a
// statistic about a named agency or member without its limit is an
// accusation. Kept here as short copy of the API's own text (data/detectors.py
// via /api/detectors), which a detector without an entry falls back to. No
// figure is repeated here that the data could move.
const DETECTOR_POINTS: Record<string, [string, string]> = {
  "D-01": [
    "Share of an agency's yearly payments made in March, when unspent money can lapse.",
    "A spending pattern, not a finding: an agency whose sanctions arrive late looks the same.",
  ],
  "D-02": [
    "How far an agency's payment amounts stray from Benford's first-digit law.",
    "Ranks agencies against each other - the weakest signal here, never evidence on its own.",
  ],
  "D-03": [
    "Allocation a member has never committed to any work.",
    "Not a suspicion: the money stays spendable after a term, so only members far above the typical share appear.",
  ],
  "D-04": [
    "Share of an agency's works sanctioned at one identical amount.",
    "Similar works can cost the same - it means the costing is worth a look, not that it is wrong.",
  ],
};

export default async function ProvenancePage() {
  // The architecture, where the AI is, and the detector catalogue. The
  // compliance rule book and its blind spots were here until the owner removed
  // them (2026-09-21); /api/compliance still serves both, and compliance is
  // still 15% of every score.
  const [detectors, overview] = await Promise.all([
    api.detectors().catch(() => []),
    api.overview(),
  ]);

  return (
    <main>
      {/* The header, its four reconciliation tiles, the data-chain cards and the
          whole "why not the portal" / reconciliation block went on the owner's
          call (2026-09-21) for the architecture below. The reconciliation
          itself still runs every night (scripts/verify_mospi.py). */}
      <section className="shell pt-8">
        <ArchitectureFlow
          works={overview.total_projects}
          payments={overview.payment_count}
          inQueue={overview.anomaly_count}
        />

        <WhereTheAI />

        {detectors.length > 0 && (
          <div className="mt-12">
            <h2 className="section-head">What each detector looks for</h2>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {detectors.map((d) => (
                <article key={d.code} className="card model-card">
                  <h3 className="model-card__name">
                    <span
                      style={{ fontFamily: "var(--font-data)", color: "var(--ink-3)" }}
                    >
                      {d.code}
                    </span>{" "}
                    {d.name}
                  </h3>
                  <p className="model-card__kind">
                    Per {d.subject === "mp" ? "member" : d.subject} ·{" "}
                    {formatCount(d.findings)} findings on record
                  </p>
                  <ul className="model-card__points">
                    <li>{DETECTOR_POINTS[d.code]?.[0] ?? d.what}</li>
                    <li>
                      <b>Does not claim.</b> {DETECTOR_POINTS[d.code]?.[1] ?? d.limit}
                    </li>
                  </ul>
                </article>
              ))}
            </div>
          </div>
        )}


      </section>
    </main>
  );
}
