"use client";

import { useEffect } from "react";

/**
 * The pointer: a dot that sits exactly under the mouse and a ring that
 * follows it with a little lag, so a fast move stretches the pair apart and a
 * stop lets the ring settle onto the dot.
 *
 * Only on devices with a real pointer that can hover - on touch it renders
 * nothing and the native cursor rules never apply. Over anything clickable the
 * ring opens up and the dot shrinks; over a text field both step aside and the
 * native caret takes over, because typing under a ring is miserable.
 *
 * Moves are the `translate` property on two fixed elements, updated in one
 * rAF loop that stops when the ring has settled - no work is done while the
 * mouse is still. `translate` rather than `transform`, because the hover
 * states use the independent `scale`, and scale wraps `transform`: a ring at
 * transform: translate(449px) scaled 1.55 drew at 696px, half a screen from
 * the mouse. `translate` is applied outermost, so the scale turns about the
 * ring's own centre.
 */

const CLICKABLE = "a, button, [role='button'], summary, label, select";
const TYPING = "input, textarea, [contenteditable='true']";
// How much of the remaining distance the ring closes each frame. Lower is
// lazier. 0.18 at 60fps settles a 400px gap in about half a second.
const FOLLOW = 0.18;

export default function Cursor() {
  useEffect(() => {
    if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;
    const dot = document.createElement("div");
    const ring = document.createElement("div");
    dot.className = "cursor cursor--dot";
    ring.className = "cursor cursor--ring";
    document.body.append(dot, ring);
    document.documentElement.classList.add("has-cursor");

    const snap = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let mx = -100;
    let my = -100;
    let rx = -100;
    let ry = -100;
    let frame = 0;
    let shown = false;

    const tick = () => {
      frame = 0;
      const dx = mx - rx;
      const dy = my - ry;
      if (snap || (Math.abs(dx) < 0.3 && Math.abs(dy) < 0.3)) {
        rx = mx;
        ry = my;
      } else {
        rx += dx * FOLLOW;
        ry += dy * FOLLOW;
        frame = requestAnimationFrame(tick);
      }
      ring.style.translate = `${rx}px ${ry}px`;
    };

    const onMove = (e: MouseEvent) => {
      // clientX/Y are screen pixels; the elements are translated in the
      // root's zoomed pixels (the site zooms the root at desktop widths), so
      // without this the pair drew a third of the way off from the mouse.
      const z = dot.currentCSSZoom ?? 1;
      mx = e.clientX / z;
      my = e.clientY / z;
      dot.style.translate = `${mx}px ${my}px`;
      if (!shown) {
        // First appearance: the ring starts under the dot rather than
        // sliding in from the corner.
        rx = mx;
        ry = my;
        shown = true;
        document.documentElement.classList.add("cursor-shown");
      }
      if (!frame) frame = requestAnimationFrame(tick);
    };
    const onOver = (e: MouseEvent) => {
      const t = e.target as Element | null;
      const typing = !!t?.closest(TYPING);
      const clickable = !typing && !!t?.closest(CLICKABLE);
      document.documentElement.classList.toggle("cursor-typing", typing);
      document.documentElement.classList.toggle("cursor-hover", clickable);
    };
    const onDown = () => document.documentElement.classList.add("cursor-down");
    const onUp = () => document.documentElement.classList.remove("cursor-down");
    // Leaving the window: relatedTarget is null only when the mouse has gone
    // off the document entirely, not when it moves between elements.
    const onOut = (e: MouseEvent) => {
      if (e.relatedTarget === null) document.documentElement.classList.remove("cursor-shown");
    };
    const onEnter = () => {
      if (shown) document.documentElement.classList.add("cursor-shown");
    };

    window.addEventListener("mousemove", onMove, { passive: true });
    document.addEventListener("mouseover", onOver, { passive: true });
    window.addEventListener("mousedown", onDown, { passive: true });
    window.addEventListener("mouseup", onUp, { passive: true });
    document.addEventListener("mouseout", onOut, { passive: true });
    document.addEventListener("mouseenter", onEnter, { passive: true });

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseover", onOver);
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("mouseup", onUp);
      document.removeEventListener("mouseout", onOut);
      document.removeEventListener("mouseenter", onEnter);
      dot.remove();
      ring.remove();
      document.documentElement.classList.remove(
        "has-cursor", "cursor-shown", "cursor-hover", "cursor-typing", "cursor-down"
      );
    };
  }, []);

  return null;
}
