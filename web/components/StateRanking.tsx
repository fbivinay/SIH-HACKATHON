"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { StateSummary } from "@/lib/api";
import { formatCount, formatINR, paidRateTone } from "@/lib/format";

const SORTS = {
  paid: { label: "Paid out", get: (s: StateSummary) => s.paid_rate ?? -1 },
  committed: { label: "Committed", get: (s: StateSummary) => s.committed_rate ?? -1 },
  completion: { label: "Completion", get: (s: StateSummary) => s.completion_rate ?? -1 },
  allocated: { label: "Allocation", get: (s: StateSummary) => s.allocated ?? -1 },
  queue: { label: "Works to verify", get: (s: StateSummary) => s.in_queue },
} as const;

type SortKey = keyof typeof SORTS;

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
        <span className="statebar__fill" style={{ width: `${pct}%`, background: tone ?? "var(--ink)" }} />
      </div>
    </div>
  );
}

/**
 * The ranked state cards. Ranking was a link per order, so every "Rank by"
 * click was a full server round trip; it is a state change now and re-sorts
 * in the same frame. Both terms arrive with the page (36 states each), so the
 * page can be static; ?ls_term= and ?sort= in a link are read after hydration
 * and kept in the URL with replaceState, like the overview's term switcher.
 */
export default function StateRanking({ byTerm }: { byTerm: Record<string, StateSummary[]> }) {
  const [term, setTerm] = useState("18");
  const [sort, setSort] = useState<SortKey>("paid");

  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    const t = q.get("ls_term");
    const s = q.get("sort");
    /* eslint-disable react-hooks/set-state-in-effect -- the URL is only readable after hydration */
    if (t && byTerm[t]) setTerm(t);
    if (s && s in SORTS) setSort(s as SortKey);
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [byTerm]);

  const pick = (k: SortKey) => {
    setSort(k);
    const u = new URL(window.location.href);
    u.searchParams.set("sort", k);
    window.history.replaceState(null, "", u);
  };

  const ranked = useMemo(
    () => [...(byTerm[term] ?? [])].sort((a, b) => SORTS[sort].get(b) - SORTS[sort].get(a)),
    [byTerm, term, sort]
  );

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[0.8rem]" style={{ color: "var(--ink-2)" }}>
          Rank by
        </span>
        {(Object.keys(SORTS) as SortKey[]).map((k) => (
          <button
            key={k}
            type="button"
            onClick={() => pick(k)}
            className="review-btn"
            aria-pressed={sort === k}
            style={sort === k ? { color: "var(--ink)", borderColor: "var(--ink)" } : undefined}
          >
            {SORTS[k].label}
          </button>
        ))}
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {ranked.map((s, i) => {
          const tone = paidRateTone(s.paid_rate);
          return (
            <article key={s.state} className="card statecard">
              <header className="flex items-baseline justify-between gap-2">
                <h2 className="text-[0.98rem] font-medium leading-tight">
                  {/* The name's link stretches over the whole card (see
                      .statecard__open); "to verify" sits above it. */}
                  <Link
                    href={`/state/${encodeURIComponent(s.state)}?ls_term=${term}`}
                    className="link-quiet statecard__open"
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
                  <Link
                    href={`/projects?state=${encodeURIComponent(s.state)}`}
                    className="link-quiet statecard__above"
                  >
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
    </>
  );
}
