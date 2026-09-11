import Link from "next/link";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { formatCount, formatINR, riskLevelClass, riskLevelLabel } from "@/lib/format";

export default async function MpPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { id } = await params;
  const sp = await searchParams;
  const wantedTerm = typeof sp.ls_term === "string" ? sp.ls_term : undefined;

  let mp;
  try {
    // Without ls_term the works block spans BOTH terms (see mp_detail), while
    // the money block below reads one - so a member with works in the 17th and
    // 18th Lok Sabha got one term's allocation shown against two terms' works.
    // Scoped to a single term, and the reader chooses which: the earlier record
    // used to be named on the page and then unreachable.
    mp = await api.mp(decodeURIComponent(id));
    if (mp.terms.length > 1) {
      const chosen =
        mp.terms.find((t) => String(t.ls_term) === wantedTerm) ?? mp.terms[0];
      mp = await api.mp(decodeURIComponent(id), { ls_term: String(chosen.ls_term) });
    }
  } catch {
    notFound();
  }

  const current = mp.terms.find((t) => String(t.ls_term) === wantedTerm) ?? mp.terms[0];
  const w = mp.works;
  const pct = (v: number | null) => (v === null ? "—" : `${Number(v).toFixed(0)}%`);

  return (
    <main className="shell py-8">
      <Link href="/analysis" className="text-xs link-quiet">
        &larr; Back to members
      </Link>

      <h1 className="display mt-4">{current.mp_name}</h1>
      <p className="mt-2 text-[0.9rem]" style={{ color: "var(--ink-2)" }}>
        {/* Rajya Sabha members carry "Sitting Rajya Sabha" as their
            constituency, which repeats the house verbatim. Dedupe rather than
            print the same words twice. */}
        {Array.from(
          new Set(
            [current.constituency, current.state, current.house].filter(
              (x): x is string => Boolean(x)
            )
          )
        )
          .filter((part, _, all) =>
            all.every((other) => other === part || !other.includes(part))
          )
          .join(" · ")}
        {mp.terms.length > 1 && ` · ${mp.terms.length} terms on record`}
      </p>

      {mp.terms.length > 1 && (
        <nav className="mt-4 flex flex-wrap gap-2" aria-label="Lok Sabha term">
          {mp.terms.map((t) => (
            <Link
              key={t.ls_term}
              href={`/mp/${encodeURIComponent(id)}?ls_term=${t.ls_term}`}
              className="review-btn"
              aria-current={t.ls_term === current.ls_term ? "true" : undefined}
              style={
                t.ls_term === current.ls_term
                  ? { color: "var(--ink)", borderColor: "var(--ink)" }
                  : undefined
              }
            >
              {t.ls_term}th Lok Sabha
            </Link>
          ))}
        </nav>
      )}

      <div className="mt-6 grid grid-cols-2 lg:grid-cols-5 gap-3">
        {[
          {
            label: "Allocated",
            value: formatINR(current.allocated_amount),
            note: `${pct(current.utilization_pct)} committed to works`,
          },
          {
            label: "Never committed",
            value: formatINR(current.idle_amount),
            note: "Allocation not attached to any work",
            tone: "medium" as const,
          },
          {
            label: "Works recommended",
            value: formatCount(w.works),
            note: `${formatCount(w.completed)} completed, ${formatCount(w.pending)} pending`,
          },
          {
            label: "Awaiting payment",
            value: formatINR(current.unspent_amount),
            note: "Committed to a work, not yet paid out",
          },
          {
            label: "To verify",
            value: formatCount(w.in_queue),
            note: `${formatCount(w.high_risk)} high risk · ${formatINR(w.flagged_value)} sanctioned`,
            tone: "high" as const,
          },
        ].map((c) => (
          <div key={c.label} className={`stat-card${c.tone ? ` stat-card--${c.tone}` : ""}`}>
            <div className="stat-card__label">{c.label}</div>
            <div className="stat-card__value">{c.value}</div>
            <div className="stat-card__note">{c.note}</div>
          </div>
        ))}
      </div>

      {w.in_queue > 0 && (
        <div className="mt-4">
          <Link
            href={`/alerts?mp_id=${encodeURIComponent(id)}`}
            className="btn btn--solid"
          >
            Open these {formatCount(w.in_queue)} works in the queue
          </Link>
        </div>
      )}

      <p className="mt-4 text-[0.82rem]" style={{ color: "var(--ink-3)" }}>
        Works span {formatCount(w.districts)}{" "}
        {w.districts === 1 ? "district" : "districts"} and {formatCount(w.agencies)}{" "}
        {w.agencies === 1 ? "implementing agency" : "implementing agencies"}. Money figures
        are the portal&rsquo;s own per-MP aggregates, so this page can be checked against the
        Ministry&rsquo;s.
      </p>

      {mp.findings.length > 0 && (
        <section className="mt-8">
          <h2 className="section-head">Flagged at member level</h2>
          <div className="mt-4 flex flex-col gap-2">
            {mp.findings.map((f) => (
              <div key={f.code + f.headline} className="card">
                <span
                  className="mr-2 text-[0.78rem]"
                  style={{ fontFamily: "var(--font-data)", color: "var(--ink-3)" }}
                >
                  {f.code}
                </span>
                <span className="text-[0.9rem]">{f.headline}</span>
                {/* A named individual is on screen here, so the detector's own
                    statement of what it does not claim matters more on this
                    page than anywhere else. */}
                {f.limit ? <p className="finding-limit">{f.limit}</p> : null}
              </div>
            ))}
          </div>
        </section>
      )}

      {mp.sectors.length > 0 && (
        <section className="mt-8">
          <h2 className="section-head">What the money went on</h2>
          <div className="mt-4 data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Sector</th>
                  <th className="num">Works</th>
                  <th className="num">Sanctioned</th>
                </tr>
              </thead>
              <tbody>
                {mp.sectors.map((s) => (
                  <tr key={s.sector}>
                    <td>{s.sector}</td>
                    <td className="num">{formatCount(s.works)}</td>
                    <td className="num">{formatINR(Number(s.sanctioned))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {mp.top_flagged.length > 0 && (
        <section className="mt-8">
          <h2 className="section-head">Highest-scoring works</h2>
          <div className="mt-4 data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Work</th>
                  <th>District</th>
                  <th className="num">Sanctioned</th>
                  <th>Risk</th>
                </tr>
              </thead>
              <tbody>
                {mp.top_flagged.map((t) => (
                  <tr key={t.id}>
                    <td className="max-w-[28rem]">
                      <Link
                        href={`/projects/${encodeURIComponent(t.work_key ?? String(t.id))}`}
                        className="link-quiet"
                      >
                        {t.work_name}
                      </Link>
                      {t.flagged_reasons.length > 0 && (
                        <ul className="reason-list">
                          {t.flagged_reasons.slice(0, 2).map((r) => (
                            <li key={r}>{r}</li>
                          ))}
                        </ul>
                      )}
                    </td>
                    <td>{t.district}</td>
                    <td className="num">{formatINR(Number(t.sanctioned_amount))}</td>
                    <td>
                      <span className={riskLevelClass(t.risk_level)}>
                        {riskLevelLabel(t.risk_level)}
                        {t.overall_risk_score !== null
                          ? ` ${Number(t.overall_risk_score).toFixed(0)}`
                          : ""}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </main>
  );
}
