import Link from "next/link";
import { api } from "@/lib/api";
import type { Trends } from "@/lib/api";
import { formatCount, formatINR } from "@/lib/format";

export const metadata = { title: "Spending over time" };

const CRORE = 1e7;

/**
 * Monthly payment volume as bars.
 *
 * Server-rendered SVG with a native <title> per bar, so hovering names the
 * month and its total without shipping a charting library or any client
 * JavaScript. One series, so no legend — the heading names it.
 */
function MonthlyBars({ monthly }: { monthly: Trends["monthly"] }) {
  if (monthly.length === 0) return null;
  const max = Math.max(...monthly.map((m) => Number(m.amount)));
  const W = 960;
  const H = 190;
  const gap = 2;
  const barW = (W - gap * (monthly.length - 1)) / monthly.length;

  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${W} ${H + 22}`} role="img" className="chart__svg"
           aria-label={`Monthly MPLADS vendor payments across ${monthly.length} months`}>
        {monthly.map((m, i) => {
          const value = Number(m.amount);
          const h = max > 0 ? (value / max) * H : 0;
          const march = m.month.endsWith("-03");
          return (
            <g key={m.month}>
              <rect
                x={i * (barW + gap)}
                y={H - h}
                width={barW}
                height={Math.max(h, 1)}
                rx={Math.min(2, barW / 2)}
                /* March is the fiscal year's last month, when money not spent
                   can lapse. Marking it is the point of the chart. */
                fill={march ? "var(--risk-high)" : "var(--ink-3)"}
              >
                <title>
                  {`${m.month} — ₹${(value / CRORE).toFixed(1)} Cr across ${formatCount(
                    m.payments
                  )} payments${march ? " (fiscal year end)" : ""}`}
                </title>
              </rect>
            </g>
          );
        })}
        {monthly.map((m, i) =>
          m.month.endsWith("-04") || i === 0 ? (
            <text
              key={`l-${m.month}`}
              x={i * (barW + gap)}
              y={H + 16}
              className="chart__tick"
            >
              {m.month.slice(0, 4)}
            </text>
          ) : null
        )}
      </svg>
      <figcaption className="chart__caption">
        Each bar is one month of recorded vendor payments. Bars in{" "}
        <span style={{ color: "var(--risk-high)", fontWeight: 500 }}>red</span> are March,
        when the fiscal year closes and unspent money can lapse.
      </figcaption>
    </figure>
  );
}

export default async function TrendsPage() {
  const t = await api.trends();
  const complete = t.fiscal_years.filter((f) => f.march_share !== null);
  const first = complete[0];
  const latestFull = complete.length >= 2 ? complete[complete.length - 2] : undefined;
  // The headline asserted a decline in every year without ever checking one.
  // The current year is excluded because it is part-way through: its March has
  // not happened yet, so its share is 0 and would fake a fall.
  const judged = complete.slice(0, Math.max(0, complete.length - 1));
  const marchFellEveryYear =
    judged.length >= 2 &&
    judged.every((f, i) => i === 0 || Number(f.march_share) < Number(judged[i - 1].march_share));

  return (
    <main>
      <section className="shell page-head">
        <h1 className="display">Spending over time</h1>
        <p className="lede">
          {formatCount(t.monthly.length)} months of recorded vendor payments, the only
          genuinely temporal thing the published record contains. It answers one question
          worth asking of any public scheme: is money spent as work happens, or shovelled
          out in March before it lapses?
        </p>
      </section>

      <section className="shell">
        <MonthlyBars monthly={t.monthly} />

        <div className="mt-8 grid gap-3 md:grid-cols-2">
          <div>
            <h2 className="section-head">Year-end bunching is falling</h2>
            <p className="lede !mx-0 !max-w-none">
              {marchFellEveryYear
                ? "March\u2019s share of the year\u2019s payments has dropped in every complete fiscal year on record"
                : "March\u2019s share of the year\u2019s payments is lower now than when the record starts, though not in an unbroken line"}
              {first && latestFull
                ? ` — from ${first.march_share}% to ${latestFull.march_share}%`
                : ""}
              . That is the trend a scheme wants: spending that follows work rather than
              the calendar.
            </p>
          </div>
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Fiscal year</th>
                  <th className="num">Payments</th>
                  <th className="num">Value</th>
                  <th className="num">In March</th>
                </tr>
              </thead>
              <tbody>
                {t.fiscal_years.map((f, i) => {
                  const partial = i === 0 || i === t.fiscal_years.length - 1;
                  return (
                    <tr key={f.fy}>
                      <td>
                        {f.fy}–{String(f.fy + 1).slice(2)}
                        {partial && <div className="cell-sub">part year on record</div>}
                      </td>
                      <td className="num">{formatCount(f.payments)}</td>
                      <td className="num">{formatINR(Number(f.amount))}</td>
                      <td className="num">
                        {f.march_share === null ? "—" : `${f.march_share}%`}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div className="mt-8">
          <h2 className="section-head">Gone quiet</h2>
          <p className="lede !mx-0 !max-w-2xl">
            Agencies holding {t.quiet_rule.min_open_works} or more works still open that
            have not paid anybody in {t.quiet_rule.days} days. This is the one
            forward-looking signal the record honestly supports: it does not predict
            failure, it notices that nothing has happened for a long time where something
            was supposed to.
          </p>

          {t.quiet_agencies.length === 0 ? (
            <p className="notice mt-5" role="status">
              <span aria-hidden="true">&#9679;</span>
              <span>No agency currently meets that description.</span>
            </p>
          ) : (
            <div className="mt-5 data-table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Agency</th>
                    <th className="num">Silent for</th>
                    <th className="num">Open works</th>
                    <th className="num">Value held</th>
                    <th className="num">Last paid</th>
                  </tr>
                </thead>
                <tbody>
                  {t.quiet_agencies.map((q) => (
                    <tr key={q.implementing_agency}>
                      <td className="max-w-[26rem]">{q.implementing_agency}</td>
                      <td className="num">{formatCount(q.days_silent)} days</td>
                      <td className="num">{formatCount(q.open_works)}</td>
                      <td className="num">{formatINR(Number(q.open_value))}</td>
                      <td className="num">{q.last_paid}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <p className="mt-6 text-[0.84rem] leading-relaxed" style={{ color: "var(--ink-3)", maxWidth: "44rem" }}>
          What this cannot do is forecast. The record carries no schedule, no milestone and
          no progress figure, so nothing here predicts that a work will fail — only that
          money moved late, or has stopped moving. See{" "}
          <Link href="/compliance" className="link-quiet">the rule book</Link> for the rest
          of what the data cannot answer.
        </p>
      </section>
    </main>
  );
}
