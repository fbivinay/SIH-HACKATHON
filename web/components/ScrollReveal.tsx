"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";

/**
 * Decides which blocks arrive on scroll, and which are simply already there.
 *
 * A scroll timeline has no progress until the reader scrolls, so a block
 * sitting in the first viewport is partway through its range by geometry alone
 * and renders half-faded until they do. Marking only the blocks that were below
 * the fold at load solves that, and has a second benefit that matters more now:
 * it is also what keeps the number of animated elements small. On a long page
 * that is a handful at a time rather than every card at once.
 *
 * Degrades to nothing: without JavaScript no block is marked, none gets a
 * timeline, and every one keeps the first-paint animation in globals.css.
 */

// Must match the selector list in globals.css.
const REVEALABLE = [
  ".stat-card",
  ".card",
  ".slab-card",
  ".model-card",
  ".statecard",
  ".rulecard",
  ".data-table-wrap",
  ".section-head",
  ".chart",
  ".leaflet-container",
].join(",");

export default function ScrollReveal() {
  const pathname = usePathname();

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (!CSS.supports("animation-timeline: view()")) return;

    const mark = () => {
      const fold = window.innerHeight;
      document.querySelectorAll<HTMLElement>(REVEALABLE).forEach((el) => {
        // Nothing nested inside another revealable block: two nested fades
        // multiply, and the inner one then arrives at a fraction of the
        // opacity of everything beside it.
        if (el.parentElement?.closest(REVEALABLE)) return;
        // A little past the fold, not exactly at it - a block straddling the
        // edge is already being read and must not fade out from under the
        // reader.
        //
        // Add only, never remove. Running this more than once is the point
        // (see below), and un-marking a block the reader has since scrolled
        // past would make it re-animate under them.
        if (el.getBoundingClientRect().top > fold * 0.92) {
          el.setAttribute("data-reveal", "");
        }
      });
    };

    // Marked more than once, because one measurement is not enough to trust.
    // Hydration now happens behind a two-second cover and before the webfont
    // has swapped, and both move the layout - a block measured above the fold
    // at hydration can be well below it by the time anyone sees the page, and
    // would then sit there never having animated. Measuring again when the
    // fonts settle and once more after the cover lifts costs three passes over
    // a few dozen elements and removes the whole class of mistake.
    const frame = requestAnimationFrame(mark);
    document.fonts?.ready.then(mark);
    const afterSplash = window.setTimeout(mark, 2400);

    return () => {
      cancelAnimationFrame(frame);
      window.clearTimeout(afterSplash);
    };
  }, [pathname]);

  return null;
}
