"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";

/**
 * Decides which blocks get a scroll-driven arrival, and which are simply
 * already there.
 *
 * The problem this exists to solve: a scroll timeline has no progress until
 * the reader scrolls, so a block sitting in the first viewport is partway
 * through its range by geometry alone and renders half-faded until they do.
 * The only CSS answer to that is a very short range - which is what made the
 * animation too quick to see, because 260px is a single flick of a wheel.
 *
 * The two requirements are in direct conflict only if every block is treated
 * the same. They are not: content above the fold has already arrived and
 * should be solid, and content below it has a whole scroll to arrive over. So
 * this marks the below-the-fold blocks, CSS gives only those a timeline, and
 * the range can then be as long as it needs to be - currently 720px, nearly
 * three times what was possible before.
 *
 * Degrades to nothing. Without JavaScript no block is marked, so none gets a
 * scroll timeline and every one keeps the first-paint animation in globals.css
 * - the page is correct and still moves, it simply does not re-animate on
 * scroll.
 */

// Must match the selector list in globals.css. Anything that should arrive on
// scroll has to be findable here.
const REVEALABLE = [
  ".stat-card",
  ".card",
  ".slab-card",
  ".model-card",
  ".statecard",
  ".rulecard",
  ".data-table-wrap",
  ".section-head",
  ".display",
  ".lede",
  ".notice",
  ".reason-list",
  ".trail",
  ".chart",
  ".leaflet-container",
].join(",");

export default function ScrollReveal() {
  const pathname = usePathname();

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (!CSS.supports("animation-timeline: view()")) return;

    // After layout, so getBoundingClientRect reflects the real position rather
    // than whatever it was mid-paint.
    const frame = requestAnimationFrame(() => {
      const fold = window.innerHeight;
      document.querySelectorAll<HTMLElement>(REVEALABLE).forEach((el) => {
        // Anything nested inside another revealable block is left alone: two
        // nested fades multiply, and the inner one then arrives at a fraction
        // of the opacity of everything beside it.
        if (el.parentElement?.closest(REVEALABLE)) return;
        // A little past the fold, not exactly at it - a block straddling the
        // edge is already being read, and should not fade out from under the
        // reader the moment the page hydrates.
        if (el.getBoundingClientRect().top > fold * 0.92) {
          el.setAttribute("data-reveal", "");
        } else {
          el.removeAttribute("data-reveal");
        }
      });
    });

    return () => cancelAnimationFrame(frame);
  }, [pathname]);

  return null;
}
