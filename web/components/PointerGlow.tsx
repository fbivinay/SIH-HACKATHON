"use client";

import { useEffect } from "react";

/**
 * Makes every surface respond to the pointer that is over it.
 *
 * Two effects, both driven from here so the CSS can stay declarative:
 *
 *   --mx / --my   where the pointer is inside the element, as a percentage.
 *                 The card's highlight is drawn at that point, so the sheen
 *                 tracks the cursor instead of sitting in a fixed corner.
 *   --tilt-x/y    a small rotation away from the pointer, which is what makes
 *                 the surface read as a physical panel being leaned on rather
 *                 than a rectangle that got bigger.
 *
 * ONE listener on the document, not one per card. There are up to sixty cards
 * on /analysis and per-element handlers would mean sixty closures and sixty
 * subscriptions for a cursor that can only be over one of them. Coordinates
 * are written inside requestAnimationFrame so a fast pointer cannot queue more
 * style writes than the compositor will draw.
 *
 * Everything here is an enhancement over CSS that already works: without
 * JavaScript the hover lift and the press response still happen, the sheen
 * simply stays centred.
 */

// Kept in sync with the selector list in globals.css - anything that should
// respond to the pointer has to be findable from the event target.
const INTERACTIVE =
  ".stat-card, .card, .slab-card, .model-card, .statecard, .rulecard, .data-table-wrap";

export default function PointerGlow() {
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    // A coarse pointer has no hover state; tracking it would mean the sheen
    // only appears under a finger that is already covering it.
    if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;

    let frame = 0;
    let pending: { el: HTMLElement; x: number; y: number } | null = null;
    let current: HTMLElement | null = null;

    const paint = () => {
      frame = 0;
      if (!pending) return;
      const { el, x, y } = pending;
      el.style.setProperty("--mx", `${x}%`);
      el.style.setProperty("--my", `${y}%`);
      // Away from the pointer, and deliberately small: 3 degrees reads as a
      // surface responding, 8 reads as a novelty.
      el.style.setProperty("--tilt-x", `${(50 - y) * 0.06}deg`);
      el.style.setProperty("--tilt-y", `${(x - 50) * 0.06}deg`);
      pending = null;
    };

    const clear = (el: HTMLElement) => {
      el.style.removeProperty("--mx");
      el.style.removeProperty("--my");
      el.style.removeProperty("--tilt-x");
      el.style.removeProperty("--tilt-y");
    };

    const onMove = (e: PointerEvent) => {
      const el = (e.target as Element | null)?.closest?.(INTERACTIVE) as HTMLElement | null;
      if (el !== current) {
        if (current) clear(current);
        current = el;
      }
      if (!el) return;
      const r = el.getBoundingClientRect();
      pending = {
        el,
        x: ((e.clientX - r.left) / r.width) * 100,
        y: ((e.clientY - r.top) / r.height) * 100,
      };
      if (!frame) frame = requestAnimationFrame(paint);
    };

    const onLeave = () => {
      if (current) clear(current);
      current = null;
    };

    document.addEventListener("pointermove", onMove, { passive: true });
    document.addEventListener("pointerleave", onLeave);
    // A card that scrolls out from under a stationary pointer would otherwise
    // keep its highlight.
    window.addEventListener("blur", onLeave);

    return () => {
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerleave", onLeave);
      window.removeEventListener("blur", onLeave);
      if (frame) cancelAnimationFrame(frame);
      if (current) clear(current);
    };
  }, []);

  return null;
}
