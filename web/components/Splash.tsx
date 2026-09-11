"use client";

import { useEffect, useRef, useState } from "react";

/**
 * A short loading screen: the mark, the name, and a bar that fills to 100%.
 *
 * It is cover, not theatre. These pages are server-rendered against a database
 * of 250,000 works, so the first paint can arrive while fonts are still
 * swapping and the client is still hydrating - and the reader sees that as the
 * page assembling itself in front of them. A second of a deliberate, finished
 * screen is calmer than a second of a page putting itself together.
 *
 * Rules it follows so it can never be the thing that breaks the site:
 *
 *   - It is client-only. Without JavaScript it never renders and the page is
 *     simply there, which is the correct fallback rather than a blank screen.
 *   - It removes itself on a timer it owns, so a font that never loads or an
 *     image that never decodes cannot strand a reader behind it.
 *   - It waits for `document.fonts.ready` but only up to that same deadline.
 *   - Under reduced motion it does not appear at all: a progress bar the
 *     reader did not ask for is motion like any other.
 */

// Long enough to cover hydration on a cold load, short enough that a warm one
// does not feel held back. The bar reaches 100% just before this.
const MAX_MS = 1100;

export default function Splash() {
  const [progress, setProgress] = useState(0);
  const [leaving, setLeaving] = useState(false);
  const [gone, setGone] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setGone(true);
      return;
    }

    // Hide the page's own scrollbar while the cover is up, so the layout does
    // not jump sideways as it leaves.
    const prev = document.documentElement.style.overflow;
    document.documentElement.style.overflow = "hidden";

    // Time since navigation, not since mount: hydration IS the slow part, so
    // measuring from mount left the bar at 0% for the whole of it.
    const start = 0;
    let frame = 0;

    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / MAX_MS);
      // Fast at first and easing into the finish, so it reads as loading
      // rather than as a fixed-length animation pretending to.
      setProgress(Math.round((1 - Math.pow(1 - t, 2.2)) * 100));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);

    const finish = () => {
      setProgress(100);
      setLeaving(true);
      document.documentElement.style.overflow = prev;
      window.setTimeout(() => setGone(true), 420);
    };

    // Whichever comes first: the fonts settling, or the deadline. The deadline
    // is what guarantees this always ends.
    const deadline = window.setTimeout(finish, Math.max(120, MAX_MS - performance.now()));
    let cancelled = false;
    document.fonts?.ready.then(() => {
      if (cancelled) return;
      const elapsed = performance.now();
      // Never snap away instantly - a cover that flashes is worse than none.
      window.setTimeout(finish, Math.max(0, 620 - elapsed));
    });

    return () => {
      cancelled = true;
      cancelAnimationFrame(frame);
      window.clearTimeout(deadline);
      document.documentElement.style.overflow = prev;
    };
  }, []);

  if (gone) return null;

  return (
    <div className={`splash${leaving ? " splash--leaving" : ""}`} aria-hidden="true">
      <div className="splash__inner">
        <svg className="splash__mark" viewBox="0 0 32 32" width="56" height="56">
          <rect width="32" height="32" rx="8" fill="var(--ink)" />
          <g stroke="var(--ground)" strokeWidth="2.6" strokeLinecap="round">
            <path d="M10.4 15.6 L15.6 10.4" />
            <path d="M11 21 L21 11" />
            <path d="M16.4 21.6 L21.6 16.4" />
          </g>
        </svg>
        <div className="splash__name">Kasauti</div>
        <div className="splash__sub">MPLADS verification</div>
        {/* The bar's width is a CSS animation, not this component's state: a
            CSS animation outranks an inline style in the cascade, so setting
            width here would have been dead code that read as if it worked.
            JavaScript owns the number and the exit; CSS owns the bar. */}
        <div className="splash__track">
          <span className="splash__fill" />
        </div>
        <div className="splash__pct">{progress}%</div>
      </div>
    </div>
  );
}
