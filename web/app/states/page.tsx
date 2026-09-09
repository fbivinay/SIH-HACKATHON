import Link from "next/link";
import { api } from "@/lib/api";
import type { StateSummary } from "@/lib/api";
import { formatCount, formatINR } from "@/lib/format";

// The source's own bands, so a state falls in the same bucket on both sites.
const HIGH = 80;
const AVERAGE = 50;

const SORTS = {
  paid: { label: "Paid out", get: (s: StateSummary) => s.paid_rate ?? -1 },
  committed: { label: "Committed", get: (s: StateSummary) => s.committed_rate ?? -1 },
  completion: { label: "Completion", get: (s: StateSummary) => s.completion_rate ?? -1 },
  allocated: { label: "Allocation", get: (s: StateSummary) => s.allocated ?? -1 },
  queue: { label: "Works to verify", get: (s: StateSummary) => s.in_queue },
} as const;

type SortKey = keyof typeof SORTS;

function band(rate: number | null): "high" | "average" | "low" {
  if (rate === null) return "low";
  if (rate >= HIGH) return "high";
  if (rate >= AVERAGE) return "average";
  return "low";
}

const BAR_TONE: Record<string, string> = {
  high: "var(--risk-low)",
  average: "var(--risk-medium)",
  low: "var(--risk-high)",
};

function Rate({ label, value, tone }: { label: string; value: number | null; tone?: string }) {
  const pct = Math.max(0, Math.min(100, value ?? 0));
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[0.76rem]" style={{ color: "var(--ink-2)" }}>
          {label}
        </span>
        <span
          className="text-[0.82rem] tabular-nums"
          style={{ fontFamily: "var(--font-data)", color: tone ?? "var(--ink)" }}
        >
          {value === null ? "—" : `${value.toFixed(1)}%`}
        </span>
      </div>
      <div className="statebar">
        <span
          className="statebar__fill"
          style={{ width: `${pct}%`, background: tone ?? "var(--ink)" }}
        />
      </div>
    </div>
  );
}

export default async function StatesPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  const rawTerm = typeof sp.ls_term === "string" ? sp.ls_term : "18";
  const term = ["17", "18"].includes(rawTerm) ? rawTerm : "18";
  const rawSort = typeof sp.sort === "string" ? sp.sort : "paid";
  const sort: SortKey = rawSort in SORTS ? (rawSort as SortKey) : "paid";

  const states = await api.states({ ls_term: term });
  const ranked = [...states].sort((a, b) => SORTS[sort].get(b) - SORTS[sort].get(a));

  const sum = (get: (s: StateSummary) => number | null) =>
    states.reduce((t, s) => t + (get(s) ?? 0), 0);
  const allocated = sum((s) => s.allocated);
  const expenditure = sum((s) => s.expenditure);
  const buckets = {
    high: states.filter((s) => band(s.paid_rate) === "high").length,
    average: states.filter((s) => band(s.paid_rate) === "average").length,
    low: states.filter((s) => band(s.paid_rate) === "low").length,
  };

  const href = (next: Record<string, string>) => {
    const params = new URLSearchParams({ ls_term: term, sort, ...next });
    return `/states?${params}`;
  };

  return (
    <main>
      <section className="shell page-head">
        <h1 className="display">Where the money went, state by state</h1>
        <p className="lede">
          Allocation, spending and completion for all {formatCount(states.length)} states and
          union territories, alongside how many of their works are waiting to be verified.
          Every money figure is the portal&rsquo;s own published aggregate, so any row here can
          be checked against the same row on empoweredindian.in.
        </p>
        <nav className="mt-6 flex flex-wrap justify-center gap-2" aria-label="Lok Sabha term">
          {[
            { value: "18", label: "18th Lok Sabha" },
            { value: "17", label: "17th Lok Sabha" },
          ].map((t) => (
            <Link
              key={t.value}
              href={href({ ls_term: t.value })}
              className="review-btn"
              aria-current={term === t.value ? "true" : undefined}
              style={term === t.value ? { color: "var(--ink)", borderColor: "var(--ink)" } : undefined}
            >
              {t.label}
            </Link>
          ))}
        </nav>
      </section>

      <section className="shell">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { label: "States and UTs", value: formatCount(states.length), note: "Every one on record" },
            { label: "Allocated", value: formatINR(allocated), note: `Across ${formatCount(sum((s) => s.mp_count))} members` },
            { label: "Paid to vendors", value: formatINR(expenditure), note: "Recorded expenditure" },
            {
              label: "Paid out",
              value: allocated > 0 ? `${((expenditure / allocated) * 100).toFixed(1)}%` : "—",
              note: "Share of allocation actually spent",
            },
          ].map((c) => (
            <div key={c.label} className="stat-card">
              <div className="stat-card__label">{c.label}</div>
              <div className="stat-card__value">{c.value}</div>
              <div className="stat-card__note">{c.note}</div>
            </div>
          ))}
        </div>

        <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            { key: "high", label: "Spending well", note: `80% or more of allocation paid out`, n: buckets.high },
            { key: "average", label: "Spending slowly", note: "50% to 79% paid out", n: buckets.average },
            { key: "low", label: "Barely spending", note: "Under 50% paid out", n: buckets.low },
          ].map((b) => (
            <div key={b.key} className="card flex items-baseline justify-between gap-3">
              <div>
                <div className="text-[0.92rem] font-medium">{b.label}</div>
                <div className="cell-sub">{b.note}</div>
              </div>
              <div
                className="text-[1.5rem] tabular-nums font-semibold"
                style={{ color: BAR_TONE[b.key] }}
              >
                {b.n}
              </div>
            </div>
          ))}
        </div>

        <p className="mt-3 text-[0.78rem]" style={{ color: "var(--ink-3)" }}>
          &ldquo;Paid out&rdquo; above divides total expenditure by total allocation. The
          source&rsquo;s own state page reports 33.2% here because it averages the 36 state
          percentages instead, which counts Lakshadweep&rsquo;s two members equally with Uttar
          Pradesh&rsquo;s hundred and eleven; its overview page reports 34.2%, the same figure
          shown here. Per-state values are identical on both sites.
        </p>

        <div className="mt-6 flex flex-wrap items-center gap-2">
          <span className="text-[0.8rem]" style={{ color: "var(--ink-2)" }}>
            Rank by
          </span>
          {(Object.keys(SORTS) as SortKey[]).map((k) => (
            <Link
              key={k}
              href={href({ sort: k })}
              className="review-btn"
              aria-current={sort === k ? "true" : undefined}
              style={sort === k ? { color: "var(--ink)", borderColor: "var(--ink)" } : undefined}
            >
              {SORTS[k].label}
            </Link>
          ))}
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {ranked.map((s, i) => {
            const tone = BAR_TONE[band(s.paid_rate)];
            return (
              <article key={s.state} className="card statecard">
                <header className="flex items-baseline justify-between gap-2">
                  <h2 className="text-[0.98rem] font-medium leading-tight">{s.state}</h2>
                  <span
                    className="text-[0.72rem] tabular-nums whitespace-nowrap"
                    style={{ fontFamily: "var(--font-data)", color: "var(--ink-3)" }}
                  >
                    #{i + 1}
                  </span>
                </header>
                <div className="cell-sub">
                  {formatCount(s.mp_count)} {s.mp_count === 1 ? "member" : "members"}
                </div>

                <dl className="statecard__money">
                  <div>
                    <dt>Allocated</dt>
                    <dd>{formatINR(s.allocated)}</dd>
                  </div>
                  <div>
                    <dt>Paid to vendors</dt>
                    <dd>{formatINR(s.expenditure)}</dd>
                  </div>
                </dl>

                <div className="mt-3 flex flex-col gap-2.5">
                  <Rate label="Paid out" value={s.paid_rate} tone={tone} />
                  <Rate label="Committed to works" value={s.committed_rate} />
                </div>

                <div className="statecard__foot">
                  <span>
                    {formatCount(s.completed_works)} completed
                    {s.completion_rate !== null ? ` · ${s.completion_rate.toFixed(1)}%` : ""}
                  </span>
                  {s.in_queue > 0 ? (
                    <Link href={`/alerts?state=${encodeURIComponent(s.state)}`} className="link-quiet">
                      {formatCount(s.in_queue)} to verify
                    </Link>
                  ) : (
                    <span style={{ color: "var(--ink-3)" }}>none flagged</span>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </main>
  );
}
