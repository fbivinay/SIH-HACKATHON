"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

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

  // Once, after the first-load entrance has finished: from here on, every
  // page entrance is a client navigation with nothing covering it, and
  // globals.css reads this attribute to drop the entrance delay and shorten
  // the travel.
  //
  // After it has FINISHED, not after the cover has gone. Setting the attribute
  // changes --enter-at, which is the animation-delay of every entrance still
  // running, and a running CSS animation whose delay drops by three seconds
  // is retimed on the spot: measured, every card snapped from 47px to 0 in
  // one frame at the moment this landed. The last entrance ends at 3000ms +
  // 390ms stagger + 960ms, so this waits past that. A navigation before then
  // sets it early (below) - the old page's elements are gone by the time the
  // new ones animate, so nothing is retimed under the reader.
  useEffect(() => {
    const t = window.setTimeout(
      () => document.documentElement.setAttribute("data-entered", ""),
      4500
    );
    return () => window.clearTimeout(t);
  }, []);

  const firstPath = useRef(pathname);
  useEffect(() => {
    if (pathname !== firstPath.current) {
      document.documentElement.setAttribute("data-entered", "");
    }
  }, [pathname]);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (!CSS.supports("animation-timeline: view()")) return;

    // Where a block sits in the layout, ignoring transforms. Not
    // getBoundingClientRect: that reports the box as drawn, and every one of
    // these blocks is drawn 104px low and scaled down while its first-paint
    // animation waits behind the loading cover (`both` fill applies the from
    // state through the delay). Measured that way, a row sitting at 599px was
    // read as 765px, marked as below the fold, and then sat at 61% opacity in
    // the first viewport for as long as nobody scrolled. offsetTop is a layout
    // value; the zoom factor puts it in the same units as innerHeight.
    const layoutTop = (el: HTMLElement) => {
      let y = 0;
      for (let n: Element | null = el; n instanceof HTMLElement; n = n.offsetParent) {
        y += n.offsetTop;
      }
      return y * (el.currentCSSZoom ?? 1) - window.scrollY;
    };

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
        if (layoutTop(el) > fold * 0.92) {
          el.setAttribute("data-reveal", "");
        }
      });
    };

    // Marked more than once, because one measurement is not enough to trust.
    // Hydration now happens behind a three-second cover and before the webfont
    // has swapped, and both move the layout - a block measured above the fold
    // at hydration can be well below it by the time anyone sees the page, and
    // would then sit there never having animated. Measuring again when the
    // fonts settle and once more after the cover lifts costs three passes over
    // a few dozen elements and removes the whole class of mistake.
    const frame = requestAnimationFrame(mark);
    document.fonts?.ready.then(mark);
    const afterSplash = window.setTimeout(mark, 3600);

    return () => {
      cancelAnimationFrame(frame);
      window.clearTimeout(afterSplash);
    };
  }, [pathname]);

  return null;
}
