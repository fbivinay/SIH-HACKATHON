"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import MpPhoto from "@/components/MpPhoto";
import { formatCount, formatINR } from "@/lib/format";

export type MpCardRow = {
  id: string;
  term: number;
  name: string;
  photo: string | null;
  party: string | null;
  partyShort: string | null;
  house: string | null;
  seat: string | null;
  state: string | null;
  allocated: number | null;
  committed: number | null;
  paid: number | null;
  idle: number | null;
  committedRate: number | null;
  paidRate: number | null;
  works: number;
  inQueue: number;
  highRisk: number;
  status: string | null;
  // Sitting, but not in the MPLADS record yet: no money, no works.
  unlisted: boolean;
};

const TERMS = [
  { value: "18", label: "18th Lok Sabha" },
  { value: "17", label: "17th Lok Sabha" },
] as const;

const SORTS: Array<{ value: string; label: string; key: (r: MpCardRow) => number | string | null; asc?: boolean }> = [
  { value: "name", label: "Name", key: (r) => r.name.toLowerCase(), asc: true },
  { value: "allocated", label: "Allocated", key: (r) => r.allocated },
  { value: "paid", label: "Paid out %", key: (r) => r.paidRate },
  { value: "committed", label: "Committed %", key: (r) => r.committedRate },
  { value: "idle", label: "Never committed", key: (r) => r.idle },
  { value: "works", label: "Works", key: (r) => r.works },
  { value: "queue", label: "Works to verify", key: (r) => r.inQueue },
];

// Sixty at a time. Every card carries a photograph and a dozen figures, and
// 774 of them at once is a DOM the pointer effects then have to walk.
const STEP = 60;
export const MAX_COMPARE = 4;

const titleCase = (s: string) =>
  s.toLowerCase().replace(/(^|[\s(-])([a-z])/g, (_, a: string, b: string) => a + b.toUpperCase());

const pct = (v: number | null) => (v === null ? "—" : `${v.toFixed(0)}%`);

export default function MpDirectory({
  byTerm,
  initialTerm,
  initialPicked,
}: {
  byTerm: Record<string, MpCardRow[]>;
  initialTerm: string;
  initialPicked: string[];
}) {
  // From the URL, read on the server, so a link back from the compare page
  // lands on the same term with the same members still picked - and the
  // first render is the same on both sides.
  const [term, setTerm] = useState(initialTerm);
  const [picked, setPicked] = useState<string[]>(initialPicked);
  const [q, setQ] = useState("");
  const [house, setHouse] = useState("");
  const [state, setState] = useState("");
  const [party, setParty] = useState("");
  const [sort, setSort] = useState("name");
  const [shown, setShown] = useState(STEP);
  const [find, setFind] = useState("");

  const rows = useMemo(() => byTerm[term] ?? [], [byTerm, term]);
  const byId = useMemo(() => new Map(rows.map((r) => [r.id, r])), [rows]);

  const states = useMemo(
    () => Array.from(new Set(rows.map((r) => r.state).filter((s): s is string => !!s))).sort(),
    [rows]
  );
  const parties = useMemo(() => {
    const n = new Map<string, number>();
    for (const r of rows) if (r.party) n.set(r.party, (n.get(r.party) ?? 0) + 1);
    return Array.from(n.entries()).sort((a, b) => b[1] - a[1]);
  }, [rows]);

  const list = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const s = SORTS.find((x) => x.value === sort) ?? SORTS[0];
    const out = rows.filter(
      (r) =>
        (!house || r.house === house) &&
        (!state || r.state === state) &&
        (!party || r.party === party) &&
        (!needle ||
          r.name.toLowerCase().includes(needle) ||
          (r.seat ?? "").toLowerCase().includes(needle) ||
          (r.state ?? "").toLowerCase().includes(needle) ||
          (r.party ?? "").toLowerCase().includes(needle) ||
          (r.partyShort ?? "").toLowerCase() === needle)
    );
    return out.sort((a, b) => {
      const ka = s.key(a);
      const kb = s.key(b);
      // Missing values last whichever way the sort runs: a member with no
      // allocation yet is not the lowest-allocated member.
      if (ka === null && kb === null) return a.name.localeCompare(b.name);
      if (ka === null) return 1;
      if (kb === null) return -1;
      if (ka === kb) return a.name.localeCompare(b.name);
      return (ka < kb ? -1 : 1) * (s.asc ? 1 : -1);
    });
  }, [rows, q, house, state, party, sort]);

  // The compare panel's own search: up to six members not already picked.
  const suggestions = useMemo(() => {
    const n = find.trim().toLowerCase();
    if (!n) return [];
    return rows
      .filter((r) => !picked.includes(r.id))
      .filter(
        (r) =>
          r.name.toLowerCase().includes(n) ||
          (r.seat ?? "").toLowerCase().includes(n) ||
          (r.partyShort ?? "").toLowerCase() === n
      )
      .sort((a, b) => {
        // Names that start with what was typed first.
        const sa = a.name.toLowerCase().startsWith(n) ? 0 : 1;
        const sb = b.name.toLowerCase().startsWith(n) ? 0 : 1;
        return sa - sb || a.name.localeCompare(b.name);
      })
      .slice(0, 6);
  }, [rows, find, picked]);

  const syncUrl = (t: string, ids: string[]) => {
    const u = new URL(window.location.href);
    u.searchParams.set("ls_term", t);
    if (ids.length) u.searchParams.set("compare", ids.join(","));
    else u.searchParams.delete("compare");
    window.history.replaceState(null, "", u);
  };

  const pickTerm = (t: string) => {
    // A Lok Sabha member has a different id in each term; a Rajya Sabha one
    // keeps theirs. Keep whoever is still in the record for the new term.
    const next = picked.filter((id) => (byTerm[t] ?? []).some((r) => r.id === id));
    setTerm(t);
    setPicked(next);
    setShown(STEP);
    syncUrl(t, next);
  };

  const toggle = (id: string) => {
    const next = picked.includes(id)
      ? picked.filter((x) => x !== id)
      : picked.length < MAX_COMPARE
        ? [...picked, id]
        : picked;
    setPicked(next);
    syncUrl(term, next);
  };

  const resetFilters = () => {
    setQ("");
    setHouse("");
    setState("");
    setParty("");
    setShown(STEP);
  };
  const filtered = Boolean(q || house || state || party);
  const chosen = picked.map((id) => byId.get(id)).filter((r): r is MpCardRow => !!r);

  const compareHref = `/mps/compare?ls_term=${term}&ids=${chosen.map((r) => r.id).join(",")}`;
  const add = (id: string) => {
    toggle(id);
    setFind("");
  };

  return (
    <>
      {/* Compare comes first (owner's call, 2026-09-21): four slots, a search
          that fills them, and the cards below fill them too. */}
      <section className="comparepanel mt-6" aria-label="Compare members">
        <div className="comparepanel__head">
          <h2 className="comparepanel__title">Compare MPs</h2>
          <span className="comparepanel__hint">
            {chosen.length === 0
              ? `Pick up to ${MAX_COMPARE} members`
              : chosen.length === 1
                ? "Pick one more to compare"
                : `${chosen.length} of ${MAX_COMPARE} picked`}
          </span>
        </div>
        <div className="comparepanel__row">
          <div className="comparepanel__slots">
            {Array.from({ length: MAX_COMPARE }, (_, i) => {
              const r = chosen[i];
              return r ? (
                <div key={r.id} className="compareslot">
                  <MpPhoto src={r.photo} name={r.name} size={40} />
                  <div className="compareslot__who">
                    <span className="compareslot__name">{r.name}</span>
                    <span className="compareslot__meta">
                      {[r.partyShort, r.state ?? r.seat].filter(Boolean).join(" · ")}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="compareslot__remove"
                    onClick={() => toggle(r.id)}
                    aria-label={`Remove ${r.name}`}
                  >
                    ×
                  </button>
                </div>
              ) : (
                <div key={`empty-${i}`} className="compareslot compareslot--empty">
                  Member {i + 1}
                </div>
              );
            })}
          </div>
          <div className="comparepanel__actions">
            {chosen.length >= 2 ? (
              <Link href={compareHref} className="btn btn--solid">
                Compare {chosen.length}
              </Link>
            ) : (
              <span className="btn btn--solid is-disabled" aria-disabled="true">
                Compare
              </span>
            )}
            {chosen.length > 0 && (
              <button type="button" className="filter-clear" onClick={() => { setPicked([]); syncUrl(term, []); }}>
                Clear
              </button>
            )}
          </div>
        </div>
        {chosen.length < MAX_COMPARE && (
          <div className="comparepanel__find">
            <label htmlFor="mp-find" className="sr-only">Add a member to compare</label>
            <input
              id="mp-find"
              type="search"
              value={find}
              onChange={(e) => setFind(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && suggestions[0]) {
                  e.preventDefault();
                  add(suggestions[0].id);
                }
              }}
              placeholder="Add a member to compare — type a name or constituency"
              className="filter-input"
              autoComplete="off"
            />
            {suggestions.length > 0 && (
              <ul className="comparepanel__suggest" role="listbox">
                {suggestions.map((r) => (
                  <li key={r.id}>
                    <button type="button" onClick={() => add(r.id)}>
                      <MpPhoto src={r.photo} name={r.name} size={28} />
                      <span className="compareslot__name">{r.name}</span>
                      <span className="compareslot__meta">
                        {[r.partyShort, r.house, r.state ?? r.seat].filter(Boolean).join(" · ")}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </section>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <nav className="nav nav--inline" aria-label="Lok Sabha term">
          {TERMS.map((t) => (
            <a
              key={t.value}
              href={`/mps?ls_term=${t.value}`}
              className="nav__link"
              aria-current={t.value === term ? "true" : undefined}
              onClick={(e) => {
                if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
                e.preventDefault();
                pickTerm(t.value);
              }}
            >
              {t.label}
            </a>
          ))}
        </nav>
        <p className="text-[0.85rem]" style={{ color: "var(--ink-2)" }}>
          {formatCount(list.length)} {list.length === 1 ? "member" : "members"}
          {filtered ? ` of ${formatCount(rows.length)}` : ""}
        </p>
      </div>

      <div className="filter-bar mpfilter mt-4">
        <div className="filter-field filter-field--grow">
          <label htmlFor="mp-search" className="sr-only">
            Search members by name, constituency, state or party
          </label>
          <input
            id="mp-search"
            type="search"
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setShown(STEP);
            }}
            placeholder="Search for a member"
            className="filter-input"
          />
        </div>
        <div className="filter-field">
          <label htmlFor="mp-house" className="sr-only">House</label>
          <select id="mp-house" value={house} onChange={(e) => { setHouse(e.target.value); setShown(STEP); }} className="filter-select">
            <option value="">Both houses</option>
            <option value="Lok Sabha">Lok Sabha</option>
            <option value="Rajya Sabha">Rajya Sabha</option>
          </select>
        </div>
        <div className="filter-field">
          <label htmlFor="mp-state" className="sr-only">State</label>
          <select id="mp-state" value={state} onChange={(e) => { setState(e.target.value); setShown(STEP); }} className="filter-select">
            <option value="">All states</option>
            {states.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div className="filter-field">
          <label htmlFor="mp-party" className="sr-only">Party</label>
          <select id="mp-party" value={party} onChange={(e) => { setParty(e.target.value); setShown(STEP); }} className="filter-select">
            <option value="">All parties</option>
            {parties.map(([p, n]) => (
              <option key={p} value={p}>{p} ({formatCount(n)})</option>
            ))}
          </select>
        </div>
        <div className="filter-field">
          <label htmlFor="mp-sort" className="sr-only">Sort by</label>
          <select id="mp-sort" value={sort} onChange={(e) => setSort(e.target.value)} className="filter-select">
            {SORTS.map((s) => (
              <option key={s.value} value={s.value}>Sort: {s.label}</option>
            ))}
          </select>
        </div>
        {filtered ? (
          <button type="button" onClick={resetFilters} className="filter-clear">
            Clear filters
          </button>
        ) : (
          <span />
        )}
      </div>

      {list.length === 0 && (
        <p className="mt-6 text-[0.9rem]" style={{ color: "var(--ink-2)" }}>
          No member matches these filters.
        </p>
      )}

      <div className="mpgrid mt-5">
        {list.slice(0, shown).map((r) => {
          const on = picked.includes(r.id);
          const full = !on && picked.length >= MAX_COMPARE;
          return (
            <article key={r.id} className={`mpcard${on ? " is-picked" : ""}`}>
              <MpPhoto src={r.photo} name={r.name} size={64} />
              <div className="mpcard__body">
                {/* One real link, drawn over the whole card; the compare
                    button sits above it (the state card's pattern). */}
                <Link href={`/mp/${encodeURIComponent(r.id)}?ls_term=${r.term}`} className="mpcard__name mpcard__open">
                  {r.name}
                </Link>
                <div className="mpcard__meta">
                  {[r.partyShort ?? r.party, r.house].filter(Boolean).join(" · ")}
                </div>
                <div className="mpcard__meta">
                  {[r.seat && r.house === "Lok Sabha" ? titleCase(r.seat) : r.seat, r.state]
                    .filter(Boolean)
                    .join(", ")}
                </div>
                {r.term === 18 && !r.unlisted && r.status && r.status !== "Sitting" && (
                  <div className="mpcard__tag">Seat ended{r.status === "Retirement" ? " (term completed)" : ""}</div>
                )}
                {r.unlisted ? (
                  <p className="mpcard__none">
                    Sitting member. No MPLADS fund record published for them yet.
                  </p>
                ) : (
                <dl className="mpcard__figs">
                  <div>
                    <dt>Allocated</dt>
                    <dd>{formatINR(r.allocated)}</dd>
                  </div>
                  <div>
                    <dt>Paid out</dt>
                    <dd>{pct(r.paidRate)}</dd>
                  </div>
                  <div>
                    <dt>Works</dt>
                    <dd>{formatCount(r.works)}</dd>
                  </div>
                  <div>
                    <dt>To verify</dt>
                    <dd className={r.highRisk > 0 ? "mpcard__risk" : undefined}>
                      {formatCount(r.inQueue)}
                    </dd>
                  </div>
                </dl>
                )}
              </div>
              <button
                type="button"
                className="mpcard__compare"
                aria-pressed={on}
                disabled={full}
                title={full ? `Up to ${MAX_COMPARE} members at a time` : undefined}
                onClick={() => toggle(r.id)}
              >
                {on ? "✓ Comparing" : "+ Compare"}
              </button>
            </article>
          );
        })}
      </div>

      {list.length > shown && (
        <div className="mt-6 flex justify-center">
          <button type="button" className="btn" onClick={() => setShown((n) => n + STEP)}>
            Show {formatCount(Math.min(STEP, list.length - shown))} more of{" "}
            {formatCount(list.length - shown)}
          </button>
        </div>
      )}

    </>
  );
}
