import { api } from "@/lib/api";
import { formatCount, formatINR, isAggregateScoringPending, riskLevelClass, riskLevelLabel, riskScoreToLevel } from "@/lib/format";

export default async function AnalysisPage() {
  const [agencies, mps] = await Promise.all([api.agencies(), api.mps()]);
  const scoringPending = isAggregateScoringPending(agencies, "anomaly_count");

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <div className="eyebrow">Implementing agencies</div>
      <h1
        className="mt-1 text-2xl sm:text-3xl font-semibold tracking-tight"
        style={{ fontFamily: "var(--font-display)" }}
      >
        Agency Analysis
      </h1>
      <p className="mt-1.5 max-w-2xl text-sm text-[color:var(--muted)]">
        {formatCount(agencies.length)} implementing agencies, ranked by average risk score.
        Vendor share is the portion of an agency&apos;s recorded spend going to its single
        largest vendor. A high share is not wrongdoing — it is a reason to look.
      </p>

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
              <th className="text-right">Works</th>
              <th className="text-right">Delayed</th>
              <th className="text-right">Anomalies</th>
              <th className="text-right">Vendors</th>
              <th className="text-right">Top vendor share</th>
              <th className="text-right">Avg Risk</th>
              <th>Level</th>
            </tr>
          </thead>
          <tbody>
            {agencies.map((a) => (
              <tr key={a.implementing_agency}>
                <td className="max-w-[24rem] truncate">{a.implementing_agency}</td>
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

      <section className="mt-12">
        <div className="eyebrow">Members of Parliament</div>
        <h2
          className="mt-1 text-xl sm:text-2xl font-semibold tracking-tight"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Allocation still unspent
        </h2>
        <p className="mt-1.5 max-w-2xl text-sm text-[color:var(--muted)]">
          Utilisation and unspent figures are the source&apos;s own published
          per-MP aggregates, not computed here, so they can be checked against
          empoweredindian.in for the same MP. Ranked by unspent amount rather
          than by utilisation: the lowest utilisation belongs to members sworn in
          during 2025&ndash;26 who have had no time to spend anything.
        </p>

        <div className="mt-6 data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>MP</th>
                <th>Constituency</th>
                <th className="text-right">Allocated</th>
                <th className="text-right">Unspent</th>
                <th className="text-right">Utilisation</th>
                <th className="text-right">Works</th>
              </tr>
            </thead>
            <tbody>
              {mps.map((m) => (
                <tr key={`${m.mp_id}-${m.ls_term}`}>
                  <td className="max-w-[20rem] truncate">
                    {m.mp_name}
                    <span className="ml-2 text-xs text-[color:var(--muted)]">
                      {m.house} &middot; LS{m.ls_term}
                    </span>
                  </td>
                  <td className="max-w-[14rem] truncate">{m.constituency ?? "—"}</td>
                  <td className="num">{formatINR(m.allocated_amount)}</td>
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
