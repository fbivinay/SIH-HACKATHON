"use client";

import { useState } from "react";
import CountUp from "@/components/CountUp";
import { TERMS, termHref } from "@/lib/terms";

/**
 * The scope line, the term switcher and the six figures - and the whole reason
 * switching a term is instant.
 *
 * The server renders every scope's figures, already formatted, and hands all
 * three here. Changing the term is then a `useState` and nothing else: no
 * fetch, no navigation, no server work, so there is no latency left to hide.
 * Two earlier passes tried to hide it instead - `<Link>` (which tore the page
 * down for `loading.tsx`'s skeleton) and `router.replace` in a transition
 * (which kept the page but still waited on the round trip) - and both still
 * read as lag, because they were lag.
 *
 * The URL is kept in step with `history.replaceState`, not the router: it must
 * describe what is on screen so the page can be shared or reloaded, and that
 * is a fact about the address bar rather than a reason to re-render anything.
 *
 * The figures are keyed by term, so React replaces the cards on a change
 * rather than updating them - which is what makes CountUp run again and the
 * numbers climb to their new values.
 */
type Stat = { label: string; value: string; note: string; tone?: "high" | "medium" };
type Scope = { term: string; stats: Stat[]; pendingNote: string | null };

export default function FiguresBoard({ scopes, initial }: { scopes: Scope[]; initial: string }) {
  const [term, setTerm] = useState(initial);
  const scope = scopes.find((s) => s.term === term) ?? scopes[0];
  const meta = TERMS.find((t) => t.value === term) ?? TERMS[0];

  const pick = (value: string) => {
    if (value === term) return;
    setTerm(value);
    window.history.replaceState(null, "", termHref(value));
  };

  return (
    <section className="shell home-figures">
      {scope.pendingNote && (
        <div className="notice mb-5" role="status">
          <span aria-hidden="true">&#9679;</span>
          <span>{scope.pendingNote}</span>
        </div>
      )}
      {/* The term switcher sits with the figures it filters rather than in the
          hero, where it cost 66px of the fold and explained nothing. */}
      <div className="mb-3 flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        {/* flex-1 min-w-0 so the sentence wraps inside its own column instead of
            pushing the term buttons onto a second row, which cost a whole
            card-row of the fold at 1280. */}
        <p className="flex-1 min-w-0 text-[0.95rem]" style={{ color: "var(--ink-3)" }}>
          {meta.label}
          {meta.note ? ` (${meta.note})` : ""} — figures cover this scope only, matching the
          same view on the source&rsquo;s dashboard.
        </p>
        <nav className="nav nav--inline" aria-label="Lok Sabha term">
          {TERMS.map((t) => (
            <a
              key={t.value || "all"}
              href={termHref(t.value)}
              className="nav__link"
              aria-current={t.value === term ? "true" : undefined}
              onClick={(e) => {
                // A modified click still opens the link in a tab of its own.
                if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
                e.preventDefault();
                pick(t.value);
              }}
            >
              {t.label}
            </a>
          ))}
        </nav>
      </div>
      <div className="figures-panel">
        <div className="figures" key={term}>
          {scope.stats.map((s) => (
            <div key={s.label} className={`figure${s.tone ? ` figure--${s.tone}` : ""}`}>
              <div className="figure__label">{s.label}</div>
              <div className="figure__value">
                <CountUp text={s.value} />
              </div>
              <div className="figure__note">{s.note}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
