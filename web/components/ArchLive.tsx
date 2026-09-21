"use client";

import { useEffect, useRef } from "react";

/**
 * Runs the architecture's motion only while the diagram is on screen.
 *
 * Every animation in `.archflow` is paused by default and set running by
 * `[data-live]`. CLAUDE.md §11: anything that keeps moving must stop when it
 * is off-screen, and this diagram loops forever by design.
 */
export default function ArchLive() {
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const flow = ref.current?.closest<HTMLElement>(".archflow");
    if (!flow) return;
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) flow.setAttribute("data-live", "");
        else flow.removeAttribute("data-live");
      },
      { threshold: 0.05 }
    );
    io.observe(flow);
    return () => io.disconnect();
  }, []);
  return <span ref={ref} hidden />;
}
