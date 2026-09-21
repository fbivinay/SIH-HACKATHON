"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";

/**
 * Sets `--fold-h`: the height of the overview's first screen, measured.
 *
 * It is the window minus the masthead and the ticker, which sounds like
 * arithmetic CSS could do - and CSS cannot, because the root is zoomed.
 * `100dvh` under `zoom` resolved to neither the window nor the window over the
 * zoom in any consistent way here: measured on 2026-09-17 at five window
 * sizes, the same expression left the panel 85px short at 1440x810 and 47px
 * long at 1366x768. The browser knows both numbers exactly, so ask it.
 *
 * `getBoundingClientRect` is zoom-adjusted and `innerHeight` is in the same
 * screen pixels, so the subtraction is in screen pixels and the result is
 * divided by the zoom to land back in the units CSS lays out in.
 *
 * Without JavaScript the CSS fallback applies and the first screen is
 * approximately right rather than exact.
 */
export default function FoldHeight() {
  const pathname = usePathname();
  useEffect(() => {
    const root = document.documentElement;
    let last = "";
    const set = () => {
      // Any page with a screen-filling first section: the overview's fold and
      // the States page's map.
      if (!document.querySelector(".home-fold, .map-screen")) {
        // Unconditionally: the previous page may have left its value behind.
        root.style.removeProperty("--fold-h");
        last = "";
        return;
      }
      const zoom = root.currentCSSZoom || 1;
      const top = document.querySelector(".topbar")?.getBoundingClientRect().height ?? 0;
      const ticker = document.querySelector(".bottombar")?.getBoundingClientRect().height ?? 0;
      const value = `${(window.innerHeight - top - ticker) / zoom}px`;
      // Written only when it moves: a custom property set on the root
      // restyles the whole document, even to the value it already had.
      if (value !== last) root.style.setProperty("--fold-h", value);
      last = value;
    };
    set();
    // Again after fonts land: the masthead is type, so its height moves.
    document.fonts?.ready.then(set).catch(() => {});
    const t = window.setTimeout(set, 600);
    window.addEventListener("resize", set);
    // The two things the height depends on, watched for their own size. It
    // used to be a MutationObserver on the whole body, which measured (and
    // forced a layout) after every DOM change anywhere - every word WordLift
    // wrapped, every re-sort, every row - measured 2026-09-21 as 44ms of
    // forced layout in a single "Rank by" click. A navigation re-runs this
    // effect (pathname), which is the other time the answer can change.
    const ro = new ResizeObserver(set);
    for (const el of document.querySelectorAll(".topbar, .bottombar")) ro.observe(el);
    return () => {
      window.removeEventListener("resize", set);
      window.clearTimeout(t);
      ro.disconnect();
    };
  }, [pathname]);
  return null;
}
