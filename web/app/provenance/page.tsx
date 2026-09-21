import { api } from "@/lib/api";
import { formatCount, formatFreshnessTimestamp } from "@/lib/format";
import WhereTheAI from "@/components/WhereTheAI";
import ArchitectureFlow from "@/components/ArchitectureFlow";

export const metadata = { title: "Where the numbers come from" };

export default async function ProvenancePage() {
  // The detector catalogue and the compliance rule book used to have pages of
  // their own. Those were removed from the interface, but the problem statement
  // names both capabilities - "deviations from established norms", "automated
  // compliance monitoring" - so the evidence page is where they belong. Neither
  // failing takes the page down: provenance is the point, these are the detail.
  const [p, detectors, rules, overview] = await Promise.all([
    api.provenance(),
    api.detectors().catch(() => []),
    api.compliance().catch(() => null),
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

        {rules && (
          <div className="mt-12">
            <h2 className="section-head">The compliance rule book</h2>
            <p className="lede !mx-0 !max-w-3xl">
              {formatCount(rules.works_breaching)} of {formatCount(rules.works_scored)} works
              breach at least one stated rule, and compliance carries{" "}
              {rules.weight_in_score}% of every score. A rule that finds nothing means one of
              two very different things, so each says which:{" "}
              <b style={{ fontWeight: 600 }}>clear</b> is the data satisfying it,{" "}
              <b style={{ fontWeight: 600 }}>inert</b> is the rule unable to fire at all on
              what the source publishes.
            </p>
            <div className="data-table-wrap mt-4">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Rule</th>
                    <th>What it checks</th>
                    <th>Condition</th>
                    <th className="num">Breaches</th>
                    <th className="num">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.rules.map((r) => (
                    <tr key={r.code}>
                      <td>
                        <span style={{ fontFamily: "var(--font-data)", color: "var(--ink-3)" }}>
                          {r.code}
                        </span>{" "}
                        {r.name}
                        <div className="cell-sub">{r.basis}</div>
                      </td>
                      <td>
                        <span className="cell-sub">{r.checks}</span>
                      </td>
                      <td>
                        <code style={{ fontFamily: "var(--font-data)", fontSize: "0.72rem" }}>
                          {r.predicate}
                        </code>
                      </td>
                      <td className="num">{formatCount(r.breaches)}</td>
                      <td className="num">{r.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="card mt-5" style={{ maxWidth: "52rem" }}>
              <h3 className="text-[0.95rem] font-medium">What this data cannot answer</h3>
              <p className="mt-1 text-[0.82rem]" style={{ color: "var(--ink-3)" }}>
                A rule book listing only what passes is the more misleading half.
              </p>
              <ul className="reason-list mt-3">
                {rules.blind_spots.map((b) => (
                  <li key={b.name}>
                    <b style={{ fontWeight: 600 }}>{b.name}</b>
                    <p className="finding-limit">{b.why}</p>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {p.last_refresh.finished_at && (
          <p className="mt-6 text-[0.8rem]" style={{ color: "var(--ink-3)" }}>
            Last refresh {formatFreshnessTimestamp(p.last_refresh.finished_at)} —{" "}
            {formatCount(p.last_refresh.rows_loaded ?? 0)} works loaded,{" "}
            {formatCount(p.last_refresh.rows_scored ?? 0)} scored, from{" "}
            {p.last_refresh.source ?? "the committed snapshot"}.
          </p>
        )}

      </section>
    </main>
  );
}
