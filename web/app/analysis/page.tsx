import Link from "next/link";
import { api } from "@/lib/api";
import { formatCount, formatINR, isAggregateScoringPending, riskLevelClass, riskLevelLabel, riskScoreToLevel } from "@/lib/format";

// The page used to render every one of the 1,539 agency-terms, which is 2.5 MB
// of HTML and an 80,000-pixel scroll. It shows a page at a time now.
const PAGE_SIZE = 60;

export default async function AnalysisPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  const term = typeof sp.ls_term === "string" ? sp.ls_term : "";
  const offset = Math.max(0, Number.parseInt(String(sp.offset ?? "0"), 10) || 0);

  const [agencies, mps] = await Promise.all([
    api.agencies({
      limit: String(PAGE_SIZE),
      offset: String(offset),
      ...(term ? { ls_term: term } : {}),
    }),
    api.mps(),
  ]);
  const scoringPending = isAggregateScoringPending(agencies, "anomaly_count");

  return (
    <main className="shell py-8">
      <h1 className="display">Implementing agencies</h1>
      <p className="lede !mx-0 !max-w-2xl">
        Ranked by average risk score. An agency is reported once per Lok Sabha term —
        its vendor mix in one says nothing about the other. Agencies with fewer than ten
        works are left out: an average over one work is whatever that work scored, and
        those agencies were crowding out ones with a thousand. Vendor share is the
        portion of an agency&apos;s recorded spend going to its single largest vendor. A
        high share is not wrongdoing — it is a reason to look.
      </p>

      <nav className="mt-5 flex flex-wrap items-center gap-2" aria-label="Filter by term">
        {[
          { value: "", label: "Both terms" },
          { value: "17", label: "17th Lok Sabha" },
          { value: "18", label: "18th Lok Sabha" },
        ].map((t) => (
          <Link
            key={t.value || "all"}
            href={t.value ? `/analysis?ls_term=${t.value}` : "/analysis"}
            className="review-btn"
            aria-current={term === t.value ? "true" : undefined}
            style={term === t.value ? { color: "var(--ink)", borderColor: "var(--ink)" } : undefined}
          >
            {t.label}
          </Link>
        ))}
      </nav>

      {scoringPending && (
        <div className="notice mt-5" role="status">
          <span aria-hidden="true">&#9679;</span>
          <span>
            Risk scoring is running across all works. Delayed/anomaly counts and average
            risk will populate once it completes.
          </span>
        </div>
      )}

      <div className="mt-6 data-table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Agency</th>
              <th className="num">Works</th>
              <th className="num">Delayed</th>
              <th className="num">Anomalies</th>
              <th className="num">Vendors</th>
              <th className="num">Top vendor share</th>
              <th className="num">Avg Risk</th>
              <th>Level</th>
            </tr>
          </thead>
          <tbody>
            {agencies.map((a) => (
              <tr key={`${a.implementing_agency}-${a.ls_term}`}>
                <td className="max-w-[24rem] truncate">
                  {a.implementing_agency}
                  <span className="ml-2 text-xs text-[color:var(--muted)]">LS{a.ls_term}</span>
                </td>
                <td className="num">{formatCount(a.total_projects)}</td>
                <td className="num">{scoringPending ? "—" : formatCount(a.delayed_count)}</td>
                <td className="num">{scoringPending ? "—" : formatCount(a.anomaly_count)}</td>
                <td className="num">{a.vendor_count === null ? "—" : formatCount(a.vendor_count)}</td>
                <td className="num">
                  {a.top_vendor_share_pct === null ? (
                    "—"
                  ) : (
                    <span title={a.top_vendor ?? undefined}>
                      {a.top_vendor_share_pct.toFixed(0)}%
                    </span>
                  )}
                </td>
                <td className="num">{scoringPending ? "—" : a.avg_risk_score.toFixed(1)}</td>
                <td>
                  <span className={riskLevelClass(scoringPending ? null : riskScoreToLevel(a.avg_risk_score))}>
                    {scoringPending ? "Pending" : riskLevelLabel(riskScoreToLevel(a.avg_risk_score))}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <nav className="pager" aria-label="Agency pages">
        {offset > 0 ? (
          <Link
            href={`/analysis?${new URLSearchParams({
              ...(term ? { ls_term: term } : {}),
              ...(offset - PAGE_SIZE > 0 ? { offset: String(offset - PAGE_SIZE) } : {}),
            })}`}
            className="pager__link"
          >
            ← Previous
          </Link>
        ) : (
          <span className="pager__link is-disabled">← Previous</span>
        )}
        <span className="pager__link is-disabled" style={{ borderColor: "transparent" }}>
          {formatCount(offset + 1)}–{formatCount(offset + agencies.length)}
        </span>
        {agencies.length === PAGE_SIZE ? (
          <Link
            href={`/analysis?${new URLSearchParams({
              ...(term ? { ls_term: term } : {}),
              offset: String(offset + PAGE_SIZE),
            })}`}
            className="pager__link"
          >
            Next →
          </Link>
        ) : (
          <span className="pager__link is-disabled">Next →</span>
        )}
      </nav>

      <section className="mt-12">
        <h2 className="section-head">Allocation never committed</h2>
        <p className="lede !mx-0 !max-w-2xl">
          Allocation the MP has never committed to any work — what the portal publishes as
          allocated, less what it publishes as recommended. This is not the source&apos;s
          &ldquo;Balance Not Yet Paid to Vendors&rdquo;, which is money already committed
          and merely awaiting payment; both are shown. Every figure is the source&apos;s own,
          so it can be checked against empoweredindian.in for the same MP.
        </p>

        <div className="mt-6 data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>MP</th>
                <th>Constituency</th>
                <th className="num">Allocated</th>
                <th className="num">Never committed</th>
                <th className="num">Awaiting payment</th>
                <th className="num">Utilisation</th>
                <th className="num">Works</th>
              </tr>
            </thead>
            <tbody>
              {mps.map((m) => (
                <tr key={`${m.mp_id}-${m.ls_term}`}>
                  <td className="max-w-[20rem] truncate">
                    <Link href={`/mp/${encodeURIComponent(m.mp_id)}`} className="link-quiet">
                      {m.mp_name}
                    </Link>
                    <span className="ml-2 text-xs text-[color:var(--muted)]">
                      {m.house} &middot; LS{m.ls_term}
                    </span>
                  </td>
                  <td className="max-w-[14rem] truncate">{m.constituency ?? "—"}</td>
                  <td className="num">{formatINR(m.allocated_amount)}</td>
                  <td className="num">{formatINR(m.idle_amount)}</td>
                  <td className="num">{formatINR(m.unspent_amount)}</td>
                  <td className="num">
                    {m.utilization_pct === null ? "—" : `${m.utilization_pct.toFixed(0)}%`}
                  </td>
                  <td className="num">{formatCount(m.total_projects)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
