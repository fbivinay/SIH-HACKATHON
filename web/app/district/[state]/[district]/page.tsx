import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { api } from "@/lib/api";
import type { DistrictDesk } from "@/lib/api";
import {
  formatCount,
  formatINR,
  riskLevelClass,
  riskLevelLabel,
  workStatusLabel,
} from "@/lib/format";

type Params = { state: string; district: string };
type Search = Record<string, string | string[] | undefined>;

export async function generateMetadata({
  params,
}: {
  params: Promise<Params>;
}): Promise<Metadata> {
  const { district } = await params;
  return { title: `${decodeURIComponent(district)} — district desk` };
}

export default async function DistrictDeskPage({
  params,
  searchParams,
}: {
  params: Promise<Params>;
  searchParams: Promise<Search>;
}) {
  const raw = await params;
  const state = decodeURIComponent(raw.state);
  const district = decodeURIComponent(raw.district);
  const sp = await searchParams;
  const ls_term = (typeof sp.ls_term === "string" ? sp.ls_term : "18") === "17" ? "17" : "18";

  let desk: DistrictDesk;
  try {
    desk = await api.districtDesk(state, district, { ls_term });
  } catch {
    notFound();
  }

  const { works } = desk;
  const queueShare = works.works > 0 ? (works.in_queue / works.works) * 100 : 0;
  const completionShare = works.works > 0 ? (works.completed / works.works) * 100 : 0;

  const href = (next: Record<string, string>) =>
    `/district/${encodeURIComponent(state)}/${encodeURIComponent(district)}?` +
    new URLSearchParams({ ls_term, ...next });

  return (
    <main>
      <section className="shell page-head">
        <div className="eyebrow">
          District Authority ·{" "}
          <Link href={`/state/${encodeURIComponent(state)}?ls_term=${ls_term}`} className="link-quiet">
            {state}
          </Link>{" "}
          · {ls_term}th Lok Sabha
        </div>
        <h1 className="display">{district}</h1>
        <p className="lede">
          {formatCount(works.works)} works across {formatCount(works.agencies)}{" "}
          {works.agencies === 1 ? "implementing agency" : "implementing agencies"}, recommended
          by {formatCount(works.members)}{" "}
          {works.members === 1 ? "member" : "members"} of parliament. No allocation figure is
          published per district — every rupee below is summed from the works themselves.
        </p>
        <nav className="mt-6 flex flex-wrap justify-center gap-2" aria-label="Lok Sabha term">
          {["18", "17"].map((t) => (
            <Link
              key={t}
              href={href({ ls_term: t })}
              className="review-btn"
              aria-current={ls_term === t ? "true" : undefined}
              style={ls_term === t ? { color: "var(--ink)", borderColor: "var(--ink)" } : undefined}
            >
              {t}th Lok Sabha
            </Link>
          ))}
        </nav>
      </section>

      <section className="shell">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            {
              label: "Sanctioned",
              value: formatINR(works.sanctioned),
              note: `${formatCount(works.works)} works on record`,
            },
            {
              label: "Completed",
              value: formatCount(works.completed),
              note: `${completionShare.toFixed(1)}% of this district's works`,
            },
            {
              label: "Still open",
              value: formatCount(works.pending),
              note: "Recommended, not yet reported complete",
            },
            {
              label: "Waiting to be verified",
              value: formatCount(works.in_queue),
              note: `${queueShare.toFixed(1)}% of works · ${formatINR(works.flagged_amount)}`,
              tone: works.high_risk > 0 ? "stat-card stat-card--high" : "stat-card stat-card--medium",
            },
          ].map((c) => (
            <div key={c.label} className={c.tone ?? "stat-card"}>
              <div className="stat-card__label">{c.label}</div>
              <div className="stat-card__value">{c.value}</div>
              <div className="stat-card__note">{c.note}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="shell mt-10">
        <div className="mb-4">
          <h2 className="section-head">Implementing agencies</h2>
          <p className="lede !mx-0 !max-w-2xl">
            The people a district authority actually supervises. Vendor concentration is
            counted from the payment records: an agency paying almost everything to one
            vendor is worth a question, not an accusation.
          </p>
        </div>
        <div className="data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th className="rank">#</th>
                <th>Agency</th>
                <th className="num">Works</th>
                <th className="num">Completed</th>
                <th className="num">Sanctioned</th>
                <th className="num">To verify</th>
                <th className="num">Avg score</th>
                <th>Top vendor</th>
              </tr>
            </thead>
            <tbody>
              {desk.agencies.map((a, i) => (
                <tr key={a.implementing_agency}>
                  <td className="rank">{i + 1}</td>
                  <td>
                    {a.implementing_agency}
                    {a.high_risk > 0 ? (
                      <div className="cell-sub">{formatCount(a.high_risk)} high risk</div>
                    ) : null}
                  </td>
                  <td className="num">{formatCount(a.works)}</td>
                  <td className="num">{formatCount(a.completed)}</td>
                  <td className="num">{formatINR(a.sanctioned)}</td>
                  <td className="num">{formatCount(a.in_queue)}</td>
                  <td className="num">{a.avg_risk === null ? "—" : a.avg_risk.toFixed(1)}</td>
                  <td>
                    {a.top_vendor ? (
                      <>
                        <span className="cell-sub">{a.top_vendor}</span>
                        {a.top_vendor_share_pct !== null ? (
                          <div className="cell-sub">
                            {a.top_vendor_share_pct.toFixed(0)}% of spend
                            {a.vendor_count ? ` · ${formatCount(a.vendor_count)} vendors` : ""}
                          </div>
                        ) : null}
                      </>
                    ) : (
                      <span style={{ color: "var(--ink-3)" }}>no payments on record</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="shell mt-10 grid gap-6 lg:grid-cols-2">
        <div>
          <div className="mb-4">
            <h2 className="section-head">Members recommending here</h2>
            <p className="lede !mx-0 !max-w-2xl">Whose funds paid for this district&rsquo;s works.</p>
          </div>
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Member</th>
                  <th className="num">Works</th>
                  <th className="num">Sanctioned</th>
                  <th className="num">To verify</th>
                </tr>
              </thead>
              <tbody>
                {desk.members.map((m) => (
                  <tr key={m.mp_id}>
                    <td>
                      <Link href={`/mp/${encodeURIComponent(m.mp_id)}`} className="link-quiet">
                        {m.mp_name}
                      </Link>
                      {m.constituency ? <div className="cell-sub">{m.constituency}</div> : null}
                    </td>
                    <td className="num">{formatCount(m.works)}</td>
                    <td className="num">{formatINR(m.sanctioned)}</td>
                    <td className="num">{formatCount(m.in_queue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <div className="mb-4">
            <h2 className="section-head">What was built</h2>
            <p className="lede !mx-0 !max-w-2xl">Sector read from each work&rsquo;s description.</p>
          </div>
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Sector</th>
                  <th className="num">Works</th>
                  <th className="num">Sanctioned</th>
                  <th className="num">To verify</th>
                </tr>
              </thead>
              <tbody>
                {desk.sectors.map((s) => (
                  <tr key={s.sector}>
                    <td>{s.sector}</td>
                    <td className="num">{formatCount(s.works)}</td>
                    <td className="num">{formatINR(s.sanctioned)}</td>
                    <td className="num">{formatCount(s.in_queue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {desk.findings.length > 0 ? (
            <>
              <div className="mb-4 mt-8">
                <h2 className="section-head">Agency signals</h2>
                <p className="lede !mx-0 !max-w-2xl">
                  Patterns across an agency&rsquo;s whole book of work. None of these move
                  any individual work&rsquo;s score.
                </p>
              </div>
              <ul className="reason-list">
                {desk.findings.slice(0, 6).map((f, i) => (
                  <li key={`${f.code}-${f.subject}-${i}`}>
                    <span style={{ fontFamily: "var(--font-data)", color: "var(--ink-3)" }}>
                      {f.code}
                    </span>{" "}
                    {f.headline}
                    <div className="cell-sub">
                      {f.subject}
                      {f.period ? ` · FY ${f.period}` : ""}
                    </div>
                  </li>
                ))}
              </ul>
            </>
          ) : null}
        </div>
      </section>

      <section className="shell mt-10">
        <div className="mb-4">
          <h2 className="section-head">Works to look at first</h2>
          <p className="lede !mx-0 !max-w-2xl">
            Ranked by score. Cost is judged against comparable works in this district and
            sector, so a high cost score means unlike its neighbours — not overpriced.
          </p>
        </div>
        <div className="data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Work</th>
                <th>Agency</th>
                <th>Status</th>
                <th className="num">Sanctioned</th>
                <th className="num">Delay</th>
                <th className="num">Cost vs peers</th>
                <th className="num">Score</th>
                <th>Band</th>
              </tr>
            </thead>
            <tbody>
              {desk.top_flagged.map((w) => (
                <tr key={w.id}>
                  <td>
                    <Link href={`/projects/${w.id}`} className="link-quiet">
                      {w.work_name}
                    </Link>
                    {w.flagged_reasons?.length ? (
                      <div className="cell-sub">{w.flagged_reasons[0]}</div>
                    ) : null}
                  </td>
                  <td>
                    <span className="cell-sub">{w.implementing_agency}</span>
                  </td>
                  <td>{workStatusLabel(w.work_status)}</td>
                  <td className="num">{formatINR(w.sanctioned_amount)}</td>
                  <td className="num">
                    {w.delay_days === null || w.delay_days <= 0
                      ? "—"
                      : `${formatCount(w.delay_days)} d`}
                  </td>
                  <td className="num">
                    {w.cost_deviation_pct === null
                      ? "—"
                      : `${w.cost_deviation_pct > 0 ? "+" : ""}${w.cost_deviation_pct.toFixed(0)}%`}
                  </td>
                  <td className="num">
                    {w.overall_risk_score === null ? "—" : w.overall_risk_score.toFixed(1)}
                  </td>
                  <td>
                    <span className={riskLevelClass(w.risk_level)}>
                      {riskLevelLabel(w.risk_level)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link
            href={`/alerts?state=${encodeURIComponent(state)}&district=${encodeURIComponent(
              district
            )}`}
            className="btn btn--solid"
          >
            Open {district} in the queue
          </Link>
          <Link href={`/state/${encodeURIComponent(state)}?ls_term=${ls_term}`} className="btn">
            Back to {state}
          </Link>
        </div>
      </section>
    </main>
  );
}
