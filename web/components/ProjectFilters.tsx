"use client";

import { useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { FilterOptions } from "@/lib/api";
import { formatCount, riskLevelLabel } from "@/lib/format";

const DEBOUNCE_MS = 300;

const STATUS_OPTION_LABELS: Record<string, string> = {
  pending: "Not yet reviewed",
  escalated: "Escalated",
  verified: "Verified",
  dismissed: "Dismissed",
};

export default function ProjectFilters({
  filterOptions,
  statuses,
}: {
  filterOptions: FilterOptions;
  // Only the alert queue has a review status to filter on; the works register
  // passes nothing and renders the same bar without it.
  statuses?: string[];
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const q = searchParams.get("q") ?? "";
  const state = searchParams.get("state") ?? "";
  const riskLevel = searchParams.get("risk_level") ?? "";
  const lsTerm = searchParams.get("ls_term") ?? "";
  const status = searchParams.get("status") ?? "";

  // Local echo of the search box so typing feels instant; URL (source of truth)
  // updates on a debounce so we don't fire a query per keystroke over 127k rows.
  const [qInput, setQInput] = useState(q);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Keep the box in sync when the URL changes some other way (back/forward,
  // clear). Derived-state-during-render rather than an effect: setting state in
  // an effect renders twice and briefly shows the stale value.
  const [lastQ, setLastQ] = useState(q);
  if (q !== lastQ) {
    setLastQ(q);
    setQInput(q);
  }

  function updateParams(next: Record<string, string>) {
    const params = new URLSearchParams(searchParams.toString());
    for (const [k, v] of Object.entries(next)) {
      if (v) params.set(k, v);
      else params.delete(k);
    }
    // Any filter change is a new result set, so go back to its first page -
    // keeping the old offset lands on an empty page whenever the narrowed set
    // is shorter than the offset.
    params.delete("offset");
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }

  function handleQChange(value: string) {
    setQInput(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => updateParams({ q: value }), DEBOUNCE_MS);
  }

  function clearAll() {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    setQInput("");
    router.replace(pathname, { scroll: false });
  }

  const hasFilters = Boolean(q || state || riskLevel || lsTerm || status);

  return (
    <div className="filter-bar">
      <div className="filter-field filter-field--grow">
        <label htmlFor="project-search" className="sr-only">
          Search works by name, MP, district, state, or agency
        </label>
        <input
          id="project-search"
          type="search"
          value={qInput}
          onChange={(e) => handleQChange(e.target.value)}
          placeholder="Search work, MP, district, state, agency…"
          className="filter-input"
        />
      </div>

      <div className="filter-field">
        <label htmlFor="project-state" className="sr-only">
          Filter by state
        </label>
        <select
          id="project-state"
          value={state}
          onChange={(e) => updateParams({ state: e.target.value })}
          className="filter-select"
        >
          <option value="">All states</option>
          {filterOptions.states.map((s) => (
            <option key={s.state} value={s.state}>
              {s.state} ({formatCount(s.count)})
            </option>
          ))}
        </select>
      </div>

      <div className="filter-field">
        <label htmlFor="project-risk" className="sr-only">
          Filter by risk level
        </label>
        <select
          id="project-risk"
          value={riskLevel}
          onChange={(e) => updateParams({ risk_level: e.target.value })}
          className="filter-select"
        >
          <option value="">Any risk level</option>
          {filterOptions.risk_levels.map((r) => (
            <option key={r} value={r}>
              {riskLevelLabel(r)}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-field">
        <label htmlFor="project-term" className="sr-only">
          Filter by Lok Sabha term
        </label>
        <select
          id="project-term"
          value={lsTerm}
          onChange={(e) => updateParams({ ls_term: e.target.value })}
          className="filter-select"
        >
          <option value="">Both terms</option>
          <option value="17">17th Lok Sabha</option>
          <option value="18">18th Lok Sabha</option>
        </select>
      </div>

      {statuses && statuses.length > 0 && (
        <div className="filter-field">
          <label htmlFor="project-status" className="sr-only">
            Filter by review status
          </label>
          <select
            id="project-status"
            value={status}
            onChange={(e) => updateParams({ status: e.target.value, offset: "" })}
            className="filter-select"
          >
            <option value="">Any review status</option>
            {statuses.map((s) => (
              <option key={s} value={s}>
                {STATUS_OPTION_LABELS[s] ?? s}
              </option>
            ))}
          </select>
        </div>
      )}

      {hasFilters && (
        <button type="button" onClick={clearAll} className="filter-clear">
          Clear filters
        </button>
      )}
    </div>
  );
}
