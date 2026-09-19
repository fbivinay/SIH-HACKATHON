import Link from "next/link";
import { api } from "@/lib/api";
import type { StateSummary } from "@/lib/api";
import { formatCount, formatINR } from "@/lib/format";
import StateMap from "@/components/StateMap";

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

  // The map's figures are not term-scoped and change nightly; one cached read,
  // fetched beside the list rather than after it.
  const [states, mapStats] = await Promise.all([
    api.states({ ls_term: term }),
    api.mapStates().catch(() => []),
  ]);
  const ranked = [...states].sort((a, b) => SORTS[sort].get(b) - SORTS[sort].get(a));

  const href = (next: Record<string, string>) => {
    const params = new URLSearchParams({ ls_term: term, sort, ...next });
    return `/states?${params}`;
  };

  return (
    <main>
      {/* The first screen is the map and nothing else (owner's call,
          2026-09-19); the /map page it came from is gone. */}
      <section className="map-screen" aria-label="Risk by state, on the map">
        <StateMap stats={mapStats} />
      </section>

      {/* The heading, the term switch, the four totals, the three spending
          bands and the note on how "paid out" is averaged all went on the
          owner's call (2026-09-19): the map above says where, and the ranked
          states below say how much. The h1 stays for screen readers. The term
          is still read from ?ls_term, defaulting to the 18th. */}
      <h1 className="sr-only">Where the money went, state by state</h1>

      <section className="shell pt-8">
        <div className="flex flex-wrap items-center gap-2">
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
                  <h2 className="text-[0.98rem] font-medium leading-tight">
                    <Link
                      href={`/state/${encodeURIComponent(s.state)}?ls_term=${term}`}
                      className="link-quiet"
                    >
                      {s.state}
                    </Link>
                  </h2>
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
