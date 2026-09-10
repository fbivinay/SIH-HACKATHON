import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { api } from "@/lib/api";
import type { StateDesk } from "@/lib/api";
import { formatCount, formatINR, riskLevelClass, riskLevelLabel } from "@/lib/format";

type Params = { state: string };
type Search = Record<string, string | string[] | undefined>;

function term(sp: Search): "17" | "18" {
  const raw = typeof sp.ls_term === "string" ? sp.ls_term : "18";
  return raw === "17" ? "17" : "18";
}

export async function generateMetadata({
  params,
}: {
  params: Promise<Params>;
}): Promise<Metadata> {
  const { state } = await params;
  return { title: `${decodeURIComponent(state)} — state desk` };
}

/** A percentage that reads as a bar. Same idiom as /states. */
function Rate({ label, value }: { label: string; value: number | null }) {
  const pct = Math.max(0, Math.min(100, value ?? 0));
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[0.76rem]" style={{ color: "var(--ink-2)" }}>
          {label}
        </span>
        <span
          className="text-[0.82rem] tabular-nums"
          style={{ fontFamily: "var(--font-data)" }}
        >
          {value === null ? "—" : `${value.toFixed(1)}%`}
        </span>
      </div>
      <div className="statebar">
        <span className="statebar__fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default async function StateDeskPage({
  params,
  searchParams,
}: {
  params: Promise<Params>;
  searchParams: Promise<Search>;
}) {
  const { state: raw } = await params;
  const state = decodeURIComponent(raw);
  const sp = await searchParams;
  const ls_term = term(sp);

  let desk: StateDesk;
  try {
    desk = await api.stateDesk(state, { ls_term });
  } catch {
    notFound();
  }

  const { money, works } = desk;
  const paidRate =
    money.allocated && money.allocated > 0
      ? ((money.expenditure ?? 0) / money.allocated) * 100
      : null;
  const committedRate =
    money.allocated && money.allocated > 0
      ? ((money.recommended ?? 0) / money.allocated) * 100
      : null;
  const completionRate =
    money.recommended_works && money.recommended_works > 0
      ? ((money.completed_works ?? 0) / money.recommended_works) * 100
      : null;
  const queueShare = works.works > 0 ? (works.in_queue / works.works) * 100 : 0;

  const href = (next: Record<string, string>) =>
    `/state/${encodeURIComponent(state)}?${new URLSearchParams({ ls_term, ...next })}`;

  return (
    <main>
      <section className="shell page-head">
        <div className="eyebrow">State Nodal Authority · {ls_term}th Lok Sabha</div>
        <h1 className="display">{state}</h1>
        <p className="lede">
          What the state was allocated, what its districts have actually built, and which
          of its {formatCount(works.works)} works are waiting on someone to look at them.
          Money is the portal&rsquo;s own per-member aggregate; everything below the fold
          is counted from the works themselves.
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
          <Link href="/states" className="review-btn">
            All states
          </Link>
        </nav>
      </section>

      <section className="shell">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            {
              label: "Allocated",
              value: formatINR(money.allocated),
              note: `${formatCount(money.mp_count)} members of parliament`,
            },
            {
              label: "Paid to vendors",
              value: formatINR(money.expenditure),
              note: paidRate === null ? "—" : `${paidRate.toFixed(1)}% of allocation`,
            },
            {
              label: "Works on record",
              value: formatCount(works.works),
              note: `${formatCount(works.completed)} completed · ${formatCount(works.districts)} districts`,
            },
            {
              label: "Waiting to be verified",
              value: formatCount(works.in_queue),
              note: `${queueShare.toFixed(1)}% of the state's works · ${formatINR(works.flagged_amount)}`,
              tone: works.in_queue > 0,
            },
          ].map((c) => (
            <div key={c.label} className={c.tone ? "stat-card stat-card--medium" : "stat-card"}>
              <div className="stat-card__label">{c.label}</div>
              <div className="stat-card__value">{c.value}</div>
              <div className="stat-card__note">{c.note}</div>
            </div>
          ))}
        </div>

        <div className="mt-3 card">
          <div className="grid gap-4 sm:grid-cols-3">
            <Rate label="Paid out" value={paidRate} />
            <Rate label="Committed to works" value={committedRate} />
            <Rate label="Works completed" value={completionRate} />
          </div>
        </div>
      </section>

      <section className="shell mt-10">
        <div className="mb-4">
          <h2 className="section-head">Districts</h2>
          <p className="lede !mx-0 !max-w-2xl">
            Ranked by how many works are waiting on verification, which is the queue a
            nodal authority actually has to clear. Open a district to see the agencies
            behind those works.
          </p>
        </div>
        <div className="data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th className="rank">#</th>
                <th>District</th>
                <th className="num">Works</th>
                <th className="num">Completed</th>
                <th className="num">Agencies</th>
                <th className="num">Sanctioned</th>
                <th className="num">To verify</th>
                <th className="num">Flagged value</th>
                <th className="num">Avg score</th>
              </tr>
            </thead>
            <tbody>
              {desk.districts.map((d, i) => (
                <tr key={d.district}>
                  <td className="rank">{i + 1}</td>
                  <td>
                    <Link
                      href={`/district/${encodeURIComponent(state)}/${encodeURIComponent(
                        d.district
                      )}?ls_term=${ls_term}`}
                      className="link-quiet"
                    >
                      {d.district}
                    </Link>
                    {d.high_risk > 0 ? (
                      <div className="cell-sub">{formatCount(d.high_risk)} high risk</div>
                    ) : null}
                  </td>
                  <td className="num">{formatCount(d.works)}</td>
                  <td className="num">{formatCount(d.completed)}</td>
                  <td className="num">{formatCount(d.agencies)}</td>
                  <td className="num">{formatINR(d.sanctioned)}</td>
                  <td className="num">{formatCount(d.in_queue)}</td>
                  <td className="num">{formatINR(d.flagged_amount)}</td>
                  <td className="num">{d.avg_risk === null ? "—" : d.avg_risk.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="shell mt-10">
        <div className="mb-4">
          <h2 className="section-head">Members</h2>
          <p className="lede !mx-0 !max-w-2xl">
            Ordered by the share of allocation actually paid out, lowest first — the
            members whose funds are moving slowest are the ones a nodal authority chases.
          </p>
        </div>
        <div className="data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Member</th>
                <th className="num">Allocated</th>
                <th className="num">Paid out</th>
                <th className="num">Never committed</th>
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
                    <div className="cell-sub">
                      {m.constituency ?? m.house ?? "—"}
                      {m.works ? ` · ${formatCount(m.works)} works` : ""}
                    </div>
                  </td>
                  <td className="num">{formatINR(m.allocated_amount)}</td>
                  <td className="num">
                    {m.utilization_pct === null ? "—" : `${m.utilization_pct.toFixed(1)}%`}
                  </td>
                  <td className="num">{formatINR(m.idle_amount)}</td>
                  <td className="num">{formatCount(m.in_queue)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="shell mt-10 grid gap-6 lg:grid-cols-2">
        <div>
          <div className="mb-4">
            <h2 className="section-head">What the money built</h2>
            <p className="lede !mx-0 !max-w-2xl">
              Sector is read from each work&rsquo;s own description, because the
              portal&rsquo;s category column says &ldquo;Normal/Others&rdquo; on almost
              every row.
            </p>
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
        </div>

        <div>
          {desk.findings.length > 0 ? (
            <>
              <div className="mb-4">
                <h2 className="section-head">Population signals</h2>
                <p className="lede !mx-0 !max-w-2xl">
                  Patterns across a whole agency or member, not a judgement on any one
                  work — which is why none of these change a work&rsquo;s score.
                </p>
              </div>
              <ul className="reason-list">
                {desk.findings.slice(0, 8).map((f, i) => (
                  <li key={`${f.code}-${f.subject}-${i}`}>
                    <span style={{ fontFamily: "var(--font-data)", color: "var(--ink-3)" }}>
                      {f.code}
                    </span>{" "}
                    {f.headline}
                    <div className="cell-sub">
                      {f.subject_type === "agency" ? (
                        f.subject
                      ) : (
                        <Link href={`/mp/${encodeURIComponent(f.subject)}`} className="link-quiet">
                          Open this member
                        </Link>
                      )}
                      {f.period ? ` · FY ${f.period}` : ""}
                    </div>
                  </li>
                ))}
              </ul>
              <Link href={`/signals?state=${encodeURIComponent(state)}`} className="link-quiet">
                All signals →
              </Link>
            </>
          ) : null}
        </div>
      </section>

      <section className="shell mt-10">
        <div className="mb-4">
          <h2 className="section-head">Highest-scoring works in {state}</h2>
          <p className="lede !mx-0 !max-w-2xl">
            The ten works least like their peers. A score is a reason to look, never a
            finding of wrongdoing.
          </p>
        </div>
        <div className="data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Work</th>
                <th>District</th>
                <th>Agency</th>
                <th className="num">Sanctioned</th>
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
                  <td>{w.district}</td>
                  <td>
                    <span className="cell-sub">{w.implementing_agency}</span>
                  </td>
                  <td className="num">{formatINR(w.sanctioned_amount)}</td>
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
        <div className="mt-4">
          <Link href={`/alerts?state=${encodeURIComponent(state)}`} className="btn btn--solid">
            Open {state} in the queue
          </Link>
        </div>
      </section>
    </main>
  );
}
