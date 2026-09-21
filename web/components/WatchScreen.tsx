import Link from "next/link";
import type { ComplianceBook, LateForecast, Trends } from "@/lib/api";
import { formatCount, formatINR } from "@/lib/format";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const titleCase = (s: string) =>
  s.toLowerCase().replace(/(^|[\s(-])([a-z])/g, (_, a: string, b: string) => a + b.toUpperCase());

/** "PRAYAGRAJ(DISTRICT MAGISTRAE ALLAHABAD_IDA)" -> "Prayagraj", with the
 * office kept for the tooltip: the place is what a reader recognises. */
const agencyPlace = (a: string) => titleCase(a.split("(")[0].trim() || a);

const queueFor = (agency: string) =>
  `/projects?${new URLSearchParams({ risk_level: "ALL", q: agency })}`;

/**
 * Trends and early warnings - the fourth screen of the overview, and the
 * part of the brief that is about time: "trend analysis", "early warning
 * mechanisms", "predictive insights", "automated compliance monitoring".
 *
 * Every figure is read from the API at build (the overview is static), and
 * none of it is folded into a work's score (CLAUDE.md §4): these describe
 * months, agencies and rules, and each links to the works behind it.
 */
export default function WatchScreen({
  trends,
  forecast,
  compliance,
}: {
  trends: Trends | null;
  forecast: LateForecast | null;
  compliance: ComplianceBook | null;
}) {
  if (!trends && !forecast && !compliance) return null;
  const months = trends?.monthly ?? [];
  const peak = Math.max(1, ...months.map((m) => m.amount));
  const fys = (trends?.fiscal_years ?? []).filter((f) => f.march_share !== null);
  const closed = fys.slice(0, -1); // the last year is still running
  const quiet = trends?.quiet_agencies ?? [];

  return (
    <section className="shell watch-screen" aria-label="Trends and early warnings">
      <div className="text-center section-intro">
        <h2 className="section-head">Trends and early warnings</h2>
        <p className="lede">
          What the record shows moving, and what it says to watch next - refreshed every night.
        </p>
      </div>

      <div className="watch-grid">
        {/* Trend: money paid, month by month. March - the month the financial
            year closes and unspent money can lapse - is set in full ink. */}
        {months.length > 0 && (
          <article className="card watch-card">
            <p className="watch-card__kind">Trend</p>
            <h3 className="watch-card__title">When the money moves</h3>
            <div className="watch-bars" role="img" aria-label="Money paid to vendors, month by month">
              {months.map((m) => {
                const [y, mo] = m.month.split("-").map(Number);
                const march = mo === 3;
                return (
                  <span
                    key={m.month}
                    className={`watch-bars__bar${march ? " is-march" : ""}`}
                    style={{ ["--h" as string]: `${Math.max(2, (m.amount / peak) * 100)}%` }}
                    title={`${MONTHS[mo - 1]} ${y}: ${formatINR(m.amount)} in ${formatCount(m.payments)} payments`}
                  />
                );
              })}
            </div>
            <div className="watch-bars__axis">
              <span>{months[0] && `${MONTHS[Number(months[0].month.split("-")[1]) - 1]} ${months[0].month.split("-")[0]}`}</span>
              <span className="watch-legend"><i /> March, the year-end</span>
              <span>{months.at(-1) && `${MONTHS[Number(months.at(-1)!.month.split("-")[1]) - 1]} ${months.at(-1)!.month.split("-")[0]}`}</span>
            </div>
            {closed.length > 1 && (
              <p className="watch-card__note">
                Share of a year&rsquo;s payments made in March:{" "}
                {closed.map((f, i) => (
                  <span key={f.fy}>
                    {i > 0 ? " → " : ""}
                    <b>{Number(f.march_share).toFixed(1)}%</b> in {f.fy}–{String(f.fy + 1).slice(2)}
                  </span>
                ))}
                . The record&rsquo;s payments begin in July {closed[0].fy}, so its first year is
                part of one.
              </p>
            )}
          </article>
        )}

        {/* Prediction: the one the record supports. */}
        {forecast && (
          <article className="card watch-card">
            <p className="watch-card__kind">Prediction</p>
            <h3 className="watch-card__title">Likely to run late</h3>
            <p className="watch-card__big">
              <b>{formatCount(forecast.likely_late)}</b> works due in the next {forecast.window_days} days
            </p>
            <p className="watch-card__note">
              {formatINR(forecast.sanctioned)} sanctioned, at {formatCount(forecast.agencies)} agencies
              where {forecast.cutoff_pct.toFixed(0)}% or more of their open works are already past
              their date - the worst quarter of {formatCount(forecast.agencies_rated)} agencies. A
              forecast from each agency&rsquo;s own record, not a finding about any work.
            </p>
            <ul className="watch-list">
              {forecast.agencies_worst.slice(0, 5).map((a) => (
                <li key={a.implementing_agency}>
                  <Link href={queueFor(a.implementing_agency)} title={a.implementing_agency}>
                    {agencyPlace(a.implementing_agency)}
                  </Link>
                  <span>
                    {formatCount(a.due_works)} due · {a.overdue_pct.toFixed(0)}% of{" "}
                    {formatCount(a.open_works)} open overdue
                  </span>
                </li>
              ))}
            </ul>
          </article>
        )}

        {/* Early warning: money committed where nothing is moving. */}
        {trends && (
          <article className="card watch-card">
            <p className="watch-card__kind">Early warning</p>
            <h3 className="watch-card__title">Gone quiet</h3>
            <p className="watch-card__big">
              <b>{formatCount(quiet.length)}</b>{" "}
              {quiet.length === 1 ? "agency has" : "agencies have"} paid nobody in{" "}
              {trends.quiet_rule.days} days
            </p>
            <p className="watch-card__note">
              Each holds {trends.quiet_rule.min_open_works} or more works still open. It does not
              say anything will go wrong - that money is committed where nothing is moving.
            </p>
            {quiet.length > 0 && (
              <ul className="watch-list">
                {quiet.slice(0, 5).map((q) => (
                  <li key={q.implementing_agency}>
                    <Link href={queueFor(q.implementing_agency)} title={q.implementing_agency}>
                      {agencyPlace(q.implementing_agency)}
                    </Link>
                    <span>
                      {formatCount(q.days_silent)} days silent · {formatCount(q.open_works)} open ·{" "}
                      {formatINR(q.open_value)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </article>
        )}

        {/* Automated compliance monitoring: the rules, checked every night. */}
        {compliance && (
          <article className="card watch-card">
            <p className="watch-card__kind">Compliance</p>
            <h3 className="watch-card__title">Checked every night</h3>
            <p className="watch-card__big">
              <b>{formatCount(compliance.works_breaching)}</b> of{" "}
              {formatCount(compliance.works_scored)} works breach at least one rule
            </p>
            <ul className="watch-rules">
              {compliance.rules.map((r) => (
                <li key={r.code}>
                  <span className="watch-rules__code">{r.code}</span>
                  <span className="watch-rules__name">{r.name}</span>
                  <span className={`watch-rules__status is-${r.status}`}>
                    {r.status === "breached"
                      ? formatCount(r.breaches)
                      : r.status === "inert"
                        ? "cannot fire"
                        : "clear"}
                  </span>
                </li>
              ))}
            </ul>
            <Link href="/projects?risk_level=ALL&compliance=breach" className="btn btn--solid watch-card__action">
              Open the {formatCount(compliance.works_breaching)} in the queue
            </Link>
          </article>
        )}
      </div>
    </section>
  );
}
