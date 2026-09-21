"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { cleanPortalName } from "@/lib/names";

/**
 * Search, in the masthead, for anything on the site.
 *
 * Two speeds, because the things being searched are two different sizes.
 * Every state, district, agency and member - about 3,200 names - arrives in
 * one request the first time the box is used and stays in memory, so those
 * matches are computed locally and appear in the same frame as the keystroke.
 * Works cannot travel that way (250,839 of them), so they are fetched, and
 * only they wait: the request is debounced, the previous one is abandoned, and
 * every answer is kept, so a backspace to something already typed is instant.
 *
 * Ranking is where the word starts: the name that begins with what was typed
 * comes before one with it at the start of a later word, which comes before
 * one with it buried mid-word. A search box is judged on the first line.
 */
const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Member = { mp_id: string; mp_name: string; state: string | null; constituency: string | null };
type Work = {
  work_key: string | null;
  id: number;
  work_name: string;
  state: string | null;
  district: string | null;
  risk_level: string | null;
  overall_risk_score: number | null;
};
type Index = {
  states: string[];
  districts: { state: string; district: string }[];
  agencies: string[];
  members: Member[];
};
type Hit = { kind: string; label: string; sub?: string; href: string };

const PAGES: Hit[] = [
  { kind: "Page", label: "Overview", sub: "The headline figures", href: "/" },
  { kind: "Page", label: "Projects", sub: "The review queue and every work", href: "/projects" },
  { kind: "Page", label: "States", sub: "The map and every state", href: "/states" },
  { kind: "Page", label: "MPs", sub: "Every member, with photographs and comparison", href: "/mps" },
  { kind: "Page", label: "Sources", sub: "Where the numbers come from", href: "/provenance" },
];

// Held outside the component so a client navigation does not fetch it again.
let indexCache: Index | null = null;
const workCache = new Map<string, Work[]>();

/** Where the needle sits in the name: 0 at the start, 1 at a word's start, 2 inside one. */
function score(text: string, needle: string): number | null {
  const at = text.toLowerCase().indexOf(needle);
  if (at < 0) return null;
  if (at === 0) return 0;
  return /[\s(,\-/]/.test(text[at - 1]) ? 1 + at / 1000 : 2 + at / 1000;
}

function localHits(index: Index | null, q: string): Hit[] {
  const needle = q.toLowerCase();
  const found: { hit: Hit; rank: number }[] = [];
  const add = (hit: Hit, text: string, bias: number) => {
    const s = score(text, needle);
    if (s !== null) found.push({ hit, rank: s + bias });
  };
  for (const p of PAGES) add(p, p.label, 0);
  for (const s of index?.states ?? []) {
    add({ kind: "State", label: s, href: `/state/${encodeURIComponent(s)}` }, s, 0.1);
  }
  for (const d of index?.districts ?? []) {
    add(
      {
        kind: "District",
        label: d.district,
        sub: d.state,
        href: `/district/${encodeURIComponent(d.state)}/${encodeURIComponent(d.district)}`,
      },
      d.district,
      0.2
    );
  }
  for (const m of index?.members ?? []) {
    add(
      {
        kind: "Member",
        label: cleanPortalName(m.mp_name),
        sub: [m.constituency, m.state].filter(Boolean).join(" · "),
        href: `/mp/${encodeURIComponent(m.mp_id)}`,
      },
      m.mp_name,
      0.3
    );
  }
  for (const a of index?.agencies ?? []) {
    add(
      { kind: "Agency", label: a, sub: "Its works", href: `/projects?q=${encodeURIComponent(a)}&risk_level=ALL` },
      a,
      0.4
    );
  }
  found.sort((x, y) => x.rank - y.rank || x.hit.label.length - y.hit.label.length);
  return found.slice(0, 8).map((f) => f.hit);
}

export default function SiteSearch() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState<Index | null>(indexCache);
  // Bumped when an answer lands in the cache below. The results themselves are
  // read from that cache during render rather than held in state: a lint rule
  // this project keeps forbids setState in an effect body, and deriving is the
  // better shape anyway - one source of truth for what a query answered.
  const [answered, setAnswered] = useState(0);
  const [active, setActive] = useState(0);
  const box = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);

  const needle = q.trim();
  const key = needle.toLowerCase();
  const works = needle.length >= 2 ? workCache.get(key) : [];
  const busy = works === undefined;

  // The names arrive once, on the first sign of interest rather than on every
  // page load: nobody pays for a search they never open.
  useEffect(() => {
    if (indexCache || !open) return;
    fetch(`${API}/api/search/index`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((data: Index) => {
        indexCache = data;
        setIndex(data);
      })
      .catch(() => {});
  }, [open]);

  useEffect(() => {
    if (needle.length < 2 || workCache.has(key)) return;
    const stop = new AbortController();
    const timer = window.setTimeout(() => {
      fetch(`${API}/api/search/works?q=${encodeURIComponent(needle)}`, { signal: stop.signal })
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
        .then((data: { works: Work[] }) => {
          workCache.set(key, data.works);
          setAnswered((n) => n + 1);
        })
        .catch((err) => {
          // A failed search must not retry forever on every keystroke.
          if (err?.name !== "AbortError") {
            workCache.set(key, []);
            setAnswered((n) => n + 1);
          }
        });
    }, 140);
    return () => {
      window.clearTimeout(timer);
      stop.abort();
    };
  }, [needle, key]);

  const hits = useMemo(() => {
    if (needle.length < 1) return [];
    const workHits: Hit[] = (workCache.get(key) ?? []).map((w) => ({
      kind: "Work",
      label: w.work_name,
      sub: [w.district, w.state].filter(Boolean).join(" · "),
      href: `/projects/${encodeURIComponent(w.work_key ?? String(w.id))}`,
    }));
    // `answered` is not used for its value: it changes when an answer lands in
    // the cache above, which is what tells this to run again.
    void answered;
    return [...localHits(index, needle), ...workHits];
  }, [needle, key, index, answered]);

  // Anywhere on the site: "/" puts the cursor here, unless the reader is
  // already typing into something.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = document.activeElement;
      const typing = el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement;
      if (e.key === "/" && !typing && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        input.current?.focus();
      }
    };
    const onClick = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    document.addEventListener("click", onClick);
    return () => {
      window.removeEventListener("keydown", onKey);
      document.removeEventListener("click", onClick);
    };
  }, []);

  const go = (hit: Hit | undefined) => {
    if (!hit) return;
    setOpen(false);
    setQ("");
    router.push(hit.href);
  };

  return (
    <div className="sitesearch" ref={box}>
      <input
        ref={input}
        type="search"
        className="sitesearch__input"
        placeholder="Search anything"
        aria-label="Search works, states, districts, agencies and members"
        autoComplete="off"
        value={q}
        onFocus={() => setOpen(true)}
        onChange={(e) => {
          setQ(e.target.value);
          setActive(0);
          setOpen(true);
        }}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setActive((a) => Math.min(a + 1, hits.length - 1));
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setActive((a) => Math.max(a - 1, 0));
          } else if (e.key === "Enter") {
            e.preventDefault();
            go(hits[active]);
          } else if (e.key === "Escape") {
            setOpen(false);
            input.current?.blur();
          }
        }}
      />

      {open && q.trim().length > 0 && (
        <div className="sitesearch__panel" role="listbox">
          {hits.map((hit, i) => (
            <button
              key={`${hit.kind}-${hit.href}-${hit.label}`}
              type="button"
              role="option"
              aria-selected={i === active}
              className={`sitesearch__hit${i === active ? " is-active" : ""}`}
              onMouseEnter={() => setActive(i)}
              onClick={() => go(hit)}
            >
              <span className="sitesearch__kind">{hit.kind}</span>
              <span className="sitesearch__label">{hit.label}</span>
              {hit.sub && <span className="sitesearch__sub">{hit.sub}</span>}
            </button>
          ))}
          {hits.length === 0 && !busy && (
            <p className="sitesearch__empty">Nothing matches “{needle}”.</p>
          )}
          {busy && <p className="sitesearch__empty">Searching works…</p>}
        </div>
      )}
    </div>
  );
}
