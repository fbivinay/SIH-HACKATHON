import { api } from "@/lib/api";
import { formatCount } from "@/lib/format";
import WhereTheAI from "@/components/WhereTheAI";
import ArchitectureFlow from "@/components/ArchitectureFlow";

export const metadata = { title: "Where the numbers come from" };

export default async function ProvenancePage() {
  // The architecture, where the AI is, and the detector catalogue. The
  // compliance rule book and its blind spots were here until the owner removed
  // them (2026-09-21); /api/compliance still serves both, and compliance is
  // still 15% of every score.
  const [p, detectors, overview] = await Promise.all([
    api.provenance(),
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
          refused={p.rejects.reduce((t, r) => t + r.rows, 0)}
          inQueue={overview.anomaly_count}
        />

        <WhereTheAI />

        {detectors.length > 0 && (
          <div className="mt-12">
            <h2 className="section-head">What each detector looks for</h2>
            <p className="lede !mx-0 !max-w-3xl">
              Four tests run across whole populations rather than single works. An agency or
              a member can show a pattern that no individual work explains, so these are
              reported at that grain and never folded into any work&rsquo;s score. Each one
              is printed here with what it does <em>not</em> claim, because a statistic
              without its limits is an accusation.
            </p>
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
                    Per {d.subject} · {formatCount(d.findings)} findings on record
                  </p>
                  <p className="model-card__does">{d.what}</p>
                  <p className="model-card__decides">
                    <span>Does not claim</span>
                    {d.limit}
                  </p>
                </article>
              ))}
            </div>
          </div>
        )}


      </section>
    </main>
  );
}
