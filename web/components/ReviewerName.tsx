"use client";

import { useEffect, useRef } from "react";

export const REVIEWER_STORAGE_KEY = "mplads.reviewer";

/**
 * Who is triaging. Self-declared and kept in this browser only — the prototype
 * has no accounts, so this is attribution, not authentication, and the label
 * says so rather than implying a verified identity.
 *
 * Uncontrolled on purpose. The stored name cannot be read during the server
 * render, so seeding React state from it would either mismatch on hydration or
 * require a setState inside an effect (cascading renders). Writing straight to
 * the DOM node once, after mount, is what an effect is actually for.
 */
export default function ReviewerName() {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    try {
      el.value = window.localStorage.getItem(REVIEWER_STORAGE_KEY) ?? "";
    } catch {
      /* private mode or blocked storage: the reviewer stays unnamed */
    }
  }, []);

  return (
    <div className="reviewer-bar">
      <label htmlFor="reviewer-name" className="reviewer-bar__label">
        Reviewing as
      </label>
      <input
        ref={inputRef}
        id="reviewer-name"
        type="text"
        defaultValue=""
        onChange={(e) => {
          try {
            window.localStorage.setItem(REVIEWER_STORAGE_KEY, e.target.value);
          } catch {
            /* decisions still record, just without a name attached */
          }
        }}
        placeholder="Your name or office"
        className="filter-input reviewer-bar__input"
        autoComplete="off"
      />
      <span className="reviewer-bar__hint">
        Stored in this browser and attached to your decisions. Not a login.
      </span>
    </div>
  );
}
