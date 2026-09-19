"use client";

import { useEffect } from "react";

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
  useEffect(() => {
    const root = document.documentElement;
    const set = () => {
      // Any page with a screen-filling first section: the overview's fold and
      // the States page's map.
      if (!document.querySelector(".home-fold, .map-screen")) {
        root.style.removeProperty("--fold-h");
        return;
      }
      const zoom = root.currentCSSZoom || 1;
      const top = document.querySelector(".topbar")?.getBoundingClientRect().height ?? 0;
      const ticker = document.querySelector(".bottombar")?.getBoundingClientRect().height ?? 0;
      root.style.setProperty("--fold-h", `${(window.innerHeight - top - ticker) / zoom}px`);
    };
    set();
    // Again after fonts land: the masthead is type, so its height moves.
    document.fonts?.ready.then(set).catch(() => {});
    const t = window.setTimeout(set, 600);
    window.addEventListener("resize", set);
    const mo = new MutationObserver(set);
    mo.observe(document.body, { childList: true, subtree: true });
    return () => {
      window.removeEventListener("resize", set);
      window.clearTimeout(t);
      mo.disconnect();
      root.style.removeProperty("--fold-h");
    };
  }, []);
  return null;
}
