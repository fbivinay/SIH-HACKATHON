import Link from "next/link";
import { api } from "@/lib/api";
import { formatCount, formatINR, isAggregateScoringPending, riskLevelClass, riskLevelLabel, riskScoreToLevel } from "@/lib/format";
import CountUp from "@/components/CountUp";
import Pager from "@/components/Pager";

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

  // Trend analysis and the early-warning signal both lost their page when
  // /trends was removed. The brief names both, and both are about agencies -
  // when they pay, and which have stopped - so this is where they belong.
  // Neither failing takes the ranking down.
  const [agencies, mps, trends] = await Promise.all([
    api.agencies({
      limit: String(PAGE_SIZE),
      offset: String(offset),
      ...(term ? { ls_term: term } : {}),
    }),
    api.mps(),
    api.trends().catch(() => null),
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
        high share is not wrongdoing — it is a reason to look. The score behind that column
        is not the column: it is a Herfindahl-Hirschman index over the agency&apos;s whole
        vendor spend, so an agency spreading money across three vendors still concentrates
        where one spreading it across forty does not.
      </p>

      <div className="mt-6 grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: "Agencies ranked", value: formatCount(agencies.length), note: "Ten works or more, this page" },
          { label: "Works they hold", value: formatCount(agencies.reduce((t, a) => t + a.total_projects, 0)), note: "Across the agencies shown" },
          { label: "Gone quiet", value: formatCount(trends?.quiet_agencies.length ?? 0), note: trends ? `No payment in ${trends.quiet_rule.days} days` : "—", tone: "medium" },
          { label: "Members listed", value: formatCount(mps.length), note: "Ranked by idle allocation" },
        ].map((c) => (
          <div key={c.label} className={`stat-card${c.tone ? ` stat-card--${c.tone}` : ""}`}>
            <div className="stat-card__label">{c.label}</div>
            <div className="stat-card__value">
              <CountUp text={String(c.value)} />
            </div>
            <div className="stat-card__note">{c.note}</div>
          </div>
        ))}
      </div>

      {trends && trends.quiet_agencies.length > 0 && (
        <section className="mt-8">
          <h2 className="section-head">Gone quiet</h2>
          <p className="lede !mx-0 !max-w-3xl">
            Agencies holding {trends.quiet_rule.min_open_works} or more works still open
            that have not paid anybody in {trends.quiet_rule.days} days. This is the one
            forward-looking signal the published record honestly supports: it does not
            predict that anything will go wrong, it reports that money is committed
            somewhere nothing is moving.
          </p>
          <div className="data-table-wrap mt-4">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Agency</th>
                  <th className="num">Open works</th>
                  <th className="num">Committed</th>
                  <th className="num">Last paid</th>
                  <th className="num">Days silent</th>
                </tr>
              </thead>
              <tbody>
                {trends.quiet_agencies.map((q) => (
                  <tr key={q.implementing_agency}>
                    <td>{q.implementing_agency}</td>
                    <td className="num">{formatCount(q.open_works)}</td>
                    <td className="num">{formatINR(q.open_value)}</td>
                    <td className="num">{q.last_paid?.slice(0, 10) ?? "—"}</td>
                    <td className="num">{formatCount(q.days_silent)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {trends && trends.fiscal_years.length > 1 && (
        <section className="mt-10">
          <h2 className="section-head">When the money moves</h2>
          <p className="lede !mx-0 !max-w-3xl">
            March is the month the Indian financial year closes and unspent money can
            lapse, so a payment run concentrated there is a spending pattern worth
            knowing. The current year is part-way through and is shown for completeness,
            not compared.
          </p>
          <div className="data-table-wrap mt-4">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Fiscal year</th>
                  <th className="num">Payments</th>
                  <th className="num">Amount</th>
                  <th className="num">Share paid in March</th>
                </tr>
              </thead>
              <tbody>
                {trends.fiscal_years.map((f, i) => {
                  const partial = i === trends.fiscal_years.length - 1;
                  return (
                    <tr key={f.fy}>
                      <td>
                        {f.fy}–{String(f.fy + 1).slice(2)}
                        {partial ? <span className="cell-sub">still running</span> : null}
                      </td>
                      <td className="num">{formatCount(f.payments)}</td>
                      <td className="num">{formatINR(f.amount)}</td>
                      <td className="num">
                        {f.march_share === null || partial
                          ? "—"
                          : `${Number(f.march_share).toFixed(1)}%`}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <h2 className="section-head mt-10">Ranking</h2>
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

      {/* The agencies endpoint returns a page, not a count, so the total is
          genuinely unknown here - the pager says so rather than inventing one. */}
      <Pager
        offset={offset}
        pageSize={PAGE_SIZE}
        shown={agencies.length}
        total={null}
        hrefFor={(o) =>
          `/analysis?${new URLSearchParams({
            ...(term ? { ls_term: term } : {}),
            ...(o > 0 ? { offset: String(o) } : {}),
          })}`
        }
        label="Agency pages"
        noun="agencies"
      />

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
