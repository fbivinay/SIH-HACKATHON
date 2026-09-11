import { api } from "@/lib/api";
import { formatCount, formatFreshnessTimestamp } from "@/lib/format";

export const metadata = { title: "Where the numbers come from" };

export default async function ProvenancePage() {
  // The detector catalogue and the compliance rule book used to have pages of
  // their own. Those were removed from the interface, but the problem statement
  // names both capabilities - "deviations from established norms", "automated
  // compliance monitoring" - so the evidence page is where they belong. Neither
  // failing takes the page down: provenance is the point, these are the detail.
  const [p, detectors, rules] = await Promise.all([
    api.provenance(),
    api.detectors().catch(() => []),
    api.compliance().catch(() => null),
  ]);
  const worst = p.worst_gap_pct;

  return (
    <main>
      <section className="shell page-head">
        <h1 className="display">Where the numbers come from</h1>
        <p className="lede">
          Every figure in this system can be traced to the Ministry&rsquo;s own published
          record, and the trace is run rather than claimed. The table below compares our
          totals against the official MPLADS dashboard at mplads.mospi.gov.in, using the
          endpoints that dashboard itself calls.
        </p>
      </section>

      <section className="shell">
        <div className="grid gap-3 md:grid-cols-3">
          {p.chain.map((c, i) => (
            <div key={c.step} className="card">
              <div
                className="text-[0.75rem] tabular-nums"
                style={{ fontFamily: "var(--font-data)", color: "var(--ink-3)" }}
              >
                {String(i + 1).padStart(2, "0")}
              </div>
              <h2 className="mt-1 text-[0.98rem] font-medium">{c.step}</h2>
              <p className="mt-2 text-[0.85rem] leading-relaxed" style={{ color: "var(--ink-2)" }}>
                {c.what}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-10">
          <h2 className="section-head">Why not the link in the problem statement?</h2>
          <p className="lede !mx-0 !max-w-3xl">
            It does publish works &mdash; but only completed ones, only for one member in
            one ward at a time, and only after an SMS one-time password sent to an Indian
            mobile number, under a rate limit its own code apologises for. There is no bulk
            export. Below is the portal&rsquo;s entire interface, enumerated from its own
            JavaScript and then called directly on {p.official_interface.checked_on}.{" "}
            {p.official_interface.login_wall}
          </p>
          <div className="data-table-wrap mt-4">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Endpoint</th>
                  <th>What it returns</th>
                  <th className="num">Needs</th>
                </tr>
              </thead>
              <tbody>
                {p.official_interface.endpoints.map((e) => (
                  <tr key={e.endpoint}>
                    <td style={{ fontFamily: "var(--font-data)", fontSize: "0.78rem" }}>
                      {e.endpoint}
                    </td>
                    <td>
                      <span className="cell-sub">{e.returns}</span>
                    </td>
                    <td className="num">
                      {e.access === "open" ? "nothing" : e.access === "otp" ? "mobile + OTP" : "an account"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-[0.85rem] leading-relaxed" style={{ color: "var(--ink-2)" }}>
            {p.official_interface.verdict}
          </p>
        </div>

        {p.rows.length === 0 ? (
          <div className="notice mt-6" role="status">
            <span aria-hidden="true">&#9679;</span>
            <span>
              No reconciliation on record yet. It is written by
              scripts/verify_mospi.py on each refresh.
            </span>
          </div>
        ) : (
          <>
            <div className="mt-6 flex flex-wrap items-baseline justify-between gap-3">
              <h2 className="section-head">Checked against the official dashboard</h2>
              {worst !== null && (
                <span className="text-[0.85rem]" style={{ color: "var(--ink-2)" }}>
                  Largest difference{" "}
                  <b style={{ fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
                    {worst.toFixed(1)}%
                  </b>
                </span>
              )}
            </div>

            <div className="mt-4 data-table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Figure</th>
                    <th className="num">This system</th>
                    <th className="num">Empowered Indian</th>
                    <th className="num">MoSPI dashboard</th>
                    <th className="num">Us vs source</th>
                    <th className="num">Source vs MoSPI</th>
                  </tr>
                </thead>
                <tbody>
                  {p.rows.map((r) => {
                    const show = (v: number) =>
                      r.unit === "crore" ? `₹${v.toLocaleString("en-IN", {
                        minimumFractionDigits: 1, maximumFractionDigits: 1 })} Cr`
                        : formatCount(v);
                    return (
                      <tr key={r.metric}>
                        <td>{r.metric}</td>
                        <td className="num">{show(Number(r.ours))}</td>
                        <td className="num">
                          {r.aggregator === null ? "—" : show(Number(r.aggregator))}
                        </td>
                        <td className="num">{show(Number(r.official))}</td>
                        <td className="num">
                          {r.aggregator === null || Number(r.aggregator) === 0
                            ? "—"
                            : `${(
                                ((Number(r.ours) - Number(r.aggregator)) /
                                  Number(r.aggregator)) *
                                100
                              ).toFixed(2)}%`}
                        </td>
                        <td className="num">
                          {r.aggregator_gap_pct === null
                            ? "—"
                            : `${Number(r.aggregator_gap_pct).toFixed(2)}%`}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <p className="mt-4 text-[0.84rem] leading-relaxed" style={{ color: "var(--ink-2)", maxWidth: "46rem" }}>
              There are two hops here, and only one of them is ours. Between this system and
              the export it loads the difference is{" "}
              <b style={{ fontWeight: 600 }}>
                {p.worst_our_hop_pct === null
                  ? "—"
                  : `${p.worst_our_hop_pct.toFixed(2)}% at worst`}
              </b>{" "}
              — and that hop is fully accounted for: it is works the loader refuses. On the
              latest extract it refused{" "}
              {p.rejects.length ? (
                p.rejects.map((r, i) => (
                  <span key={r.reason}>
                    {i > 0 ? ", " : ""}
                    <b style={{ fontWeight: 600 }}>{formatCount(r.rows)}</b> for{" "}
                    {r.reason.toLowerCase()}
                  </span>
                ))
              ) : (
                <b style={{ fontWeight: 600 }}>nothing</b>
              )}
              . A work with no description cannot be assigned a sector or matched against a
              duplicate, so it is rejected and written to a rejects table with its reason
              rather than dropped quietly. Every remaining row of the export is loaded. The
              rest{" "}
              {p.worst_upstream_hop_pct !== null && (
                <>
                  (up to{" "}
                  <b style={{ fontWeight: 600 }}>
                    {Math.abs(p.worst_upstream_hop_pct).toFixed(2)}%
                  </b>
                  )
                </>
              )}{" "}
              is the aggregator trailing the Ministry: it re-crawls a quarter-million-work
              portal at one request every three seconds, so it is permanently a little
              behind. Every difference is negative, never ahead — which is what lag looks
              like. A mangled load would miss in both directions, and the allocation figure,
              which does not move day to day, would be the first to break.
            </p>

            <div className="card mt-5" style={{ maxWidth: "44rem" }}>
              <h3 className="text-[0.95rem] font-medium">What the portal has that we do not</h3>
              <p className="mt-2 text-[0.85rem] leading-relaxed" style={{ color: "var(--ink-2)" }}>
                The official dashboard reports a <b style={{ fontWeight: 600 }}>Works Sanctioned</b>{" "}
                stage between recommendation and completion. The machine-readable export we
                load carries no sanction flag, so a work here is recommended or completed
                and nothing in between. Delay is therefore measured from recommendation, not
                from sanction, which is the more forgiving of the two readings.
              </p>
            </div>
          </>
        )}

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
