import { api } from "@/lib/api";
import { formatCount, formatFreshnessTimestamp } from "@/lib/format";

export const metadata = { title: "Where the numbers come from" };

export default async function ProvenancePage() {
  const p = await api.provenance();
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
            Because it does not publish the data this system reads. The designated
            dashboard&rsquo;s entire public interface is the seven calls below, enumerated
            from its own JavaScript bundle and then made directly on{" "}
            {p.official_interface.checked_on}. Not one of them returns a work: no
            description, no sanctioned amount, no start date, no implementing agency, no
            payment. {p.official_interface.login_wall}
          </p>
          <div className="data-table-wrap mt-4">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Endpoint</th>
                  <th>What it returns</th>
                  <th className="num">Work-level?</th>
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
                    <td className="num">{e.works ? "yes" : "no"}</td>
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
                    <th className="num">MoSPI dashboard</th>
                    <th className="num">Difference</th>
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
                        <td className="num">{show(Number(r.official))}</td>
                        <td className="num">
                          {r.gap_pct === null ? "—" : `${Number(r.gap_pct).toFixed(2)}%`}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <p className="mt-4 text-[0.84rem] leading-relaxed" style={{ color: "var(--ink-2)", maxWidth: "44rem" }}>
              Every difference is negative: this system is consistently a little behind the
              portal, never ahead of it. That is what a snapshot taken a day earlier looks
              like. A mangled load would miss in both directions, and the allocation figure
              — which does not move day to day — would be the first to break.
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
