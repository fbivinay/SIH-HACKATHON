"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";

// useLayoutEffect runs before the browser paints, so the reset to zero never
// reaches the screen; on the server it does not exist and React warns if you
// call it, hence the swap. Without this the figure was painted at its real
// value, then visibly snapped back to zero once hydration caught up.
const useIsomorphicLayoutEffect =
  typeof window === "undefined" ? useEffect : useLayoutEffect;

/**
 * Counts a figure up to its real value when it first comes into view.
 *
 * Takes the ALREADY FORMATTED string — "₹11,681.90 Cr", "1,31,116", "43.2%" —
 * and animates the number inside it, keeping the prefix, the suffix, the Indian
 * digit grouping and the decimal places exactly as they were. That is why call
 * sites need no change beyond wrapping: no raw value has to be threaded through
 * a page that has already formatted it, and there is one place where the
 * behaviour lives rather than nineteen.
 *
 * The server renders the final string. If JavaScript never arrives, or the
 * reader has asked for reduced motion, or the text holds no number at all
 * ("—"), what is on screen is simply the correct figure — the animation is an
 * enhancement on top of a page that is already right.
 */

const DURATION = 900;

// Digits with Indian grouping, optionally a decimal part. The first such run in
// the string is the figure; everything before and after is kept verbatim.
const NUMBER = /\d[\d,]*(?:\.\d+)?/;

function easeOut(t: number) {
  // Decelerating, no overshoot — a figure that springs past its value and comes
  // back reads as decorative, and these are audited numbers.
  return 1 - Math.pow(1 - t, 3);
}

export default function CountUp({ text }: { text: string }) {
  const [shown, setShown] = useState(text);
  // Opacity is owned here rather than by a CSS timer. A timer has to guess how
  // long hydration takes; on a slow load it finished first and the real figure
  // sat fully visible until the counter reset it to zero, which read as a
  // glitch. Driving it from the component means the fade-out and the reset
  // happen in one commit, so a wrong number is never on screen at full
  // strength no matter when the JavaScript lands.
  const [dim, setDim] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  useIsomorphicLayoutEffect(() => {
    const match = text.match(NUMBER);
    const node = ref.current;
    if (!node || !match) {
      setShown(text);
      return;
    }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setShown(text);
      return;
    }


    const raw = match[0];
    const target = Number(raw.replace(/,/g, ""));
    if (!Number.isFinite(target)) {
      setShown(text);
      return;
    }
    const decimals = raw.includes(".") ? raw.split(".")[1].length : 0;
    const prefix = text.slice(0, match.index);
    const suffix = text.slice((match.index ?? 0) + raw.length);
    const render = (n: number) =>
      prefix +
      n.toLocaleString("en-IN", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      }) +
      suffix;

    let frame = 0;
    let start = 0;
    const step = (now: number) => {
      if (!start) start = now;
      const t = Math.min(1, (now - start) / DURATION);
      setShown(t === 1 ? text : render(target * easeOut(t)));
      if (t > 0.05) setDim(false);
      if (t < 1) frame = requestAnimationFrame(step);
    };

    // Runs every time the figure comes into view, not once per page load.
    // Disconnecting after the first pass meant scrolling away and back left a
    // dead number on screen, which is the opposite of looking live.
    let running = false;
    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries[0].isIntersecting) {
          // Left the screen: stop, and arm it to count again on return.
          cancelAnimationFrame(frame);
          running = false;
          start = 0;
          return;
        }
        if (running) return;
        running = true;
        setDim(true);
        setShown(render(0));
        start = 0;
        frame = requestAnimationFrame(step);
      },
      { threshold: 0.25 }
    );
    observer.observe(node);

    return () => {
      observer.disconnect();
      cancelAnimationFrame(frame);
    };
  }, [text]);

  // tabular-nums is what stops the box juddering as the digits change width.
  return (
    <span
      ref={ref}
      style={{
        fontVariantNumeric: "tabular-nums",
        opacity: dim ? 0 : 1,
        transition: "opacity 260ms var(--ease-out)",
      }}
    >
      {shown}
    </span>
  );
}
