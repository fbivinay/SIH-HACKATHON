import type { Trends } from "@/lib/api";
import { formatCount, formatINR } from "@/lib/format";

/**
 * The early warning and the trend analysis the problem statement names. They
 * lived on the Agencies page; when that became the MPs page (owner's call,
 * 2026-09-21) they moved here rather than going with it, because both are
 * about how money moves through agencies over time - the same kind of
 * population-grain evidence as the detectors above them on this page.
 */
export default function MoneyMovement({ trends }: { trends: Trends | null }) {
  if (!trends) return null;
  return (
    <>
        {trends.quiet_agencies.length > 0 && (
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
  
        {trends.fiscal_years.length > 1 && (
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
    </>
  );
}
