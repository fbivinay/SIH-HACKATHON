"use client";

import { useEffect, useRef } from "react";

/**
 * A field of ink-coloured points drifting slowly behind the overview headline.
 *
 * One 2D canvas, four hundred points, no dependencies. Each point has a depth
 * that sets its size, weight and speed, so the field has a little parallax
 * without any camera. The colour is whatever `--ink` is, read from the canvas
 * itself, so the field follows the theme.
 *
 * It costs under a millisecond a frame and stops entirely when the hero is
 * scrolled away or the tab is hidden - a background that keeps drawing for
 * nobody is the kind of thing that made the site laggy before. Under reduced
 * motion it draws once and stays still.
 */

const COUNT = 400;
// Pixels per second at depth 1. Slow enough to be felt rather than watched.
const SPEED = 9;

export default function HeroField() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    // x, y, depth, phase - one flat array, no per-point objects to collect.
    const pts = new Float32Array(COUNT * 4);
    let w = 0;
    let h = 0;
    let ink = "rgb(20, 20, 24)";
    let last = 0;
    let frame = 0;
    let onScreen = true;
    let tabShown = !document.hidden;

    const resize = () => {
      // Layout size, not getBoundingClientRect: the hero is scaled to 0.95
      // while its entrance animation waits, and a backing store sized from
      // that rect was 5% short and drawn blurry for the life of the page.
      // The zoom factor turns layout pixels into the screen pixels the
      // backing store needs (the site zooms the root at desktop widths).
      const scale = Math.min(window.devicePixelRatio || 1, 2) * (canvas.currentCSSZoom ?? 1);
      const nw = canvas.clientWidth;
      const nh = canvas.clientHeight;
      // Keep every point where it was, proportionally, so a resize does not
      // reshuffle the field in front of the reader.
      if (w && h) {
        for (let i = 0; i < COUNT; i++) {
          pts[i * 4] *= nw / w;
          pts[i * 4 + 1] *= nh / h;
        }
      }
      w = nw;
      h = nh;
      canvas.width = Math.round(w * scale);
      canvas.height = Math.round(h * scale);
      ctx.setTransform(scale, 0, 0, scale, 0, 0);
    };

    const seed = () => {
      for (let i = 0; i < COUNT; i++) {
        pts[i * 4] = Math.random() * w;
        pts[i * 4 + 1] = Math.random() * h;
        pts[i * 4 + 2] = Math.random();
        pts[i * 4 + 3] = Math.random() * Math.PI * 2;
      }
    };

    const draw = (now: number) => {
      // Clamped so a tab coming back after a minute does not fling every
      // point across the field in one step.
      const dt = last ? Math.min((now - last) / 1000, 0.05) : 0;
      last = now;
      const t = now / 1000;
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = ink;
      for (let i = 0; i < COUNT; i++) {
        const o = i * 4;
        const z = pts[o + 2];
        const ph = pts[o + 3];
        // A slow wander with a slight rightward bias, faster nearer the front.
        let x = pts[o] + (Math.sin(t * 0.18 + ph) * 0.6 + 0.35) * SPEED * (0.3 + z) * dt;
        let y = pts[o + 1] + Math.cos(t * 0.14 + ph * 1.7) * 0.5 * SPEED * (0.3 + z) * dt;
        if (x < -4) x += w + 8;
        else if (x > w + 4) x -= w + 8;
        if (y < -4) y += h + 8;
        else if (y > h + 4) y -= h + 8;
        pts[o] = x;
        pts[o + 1] = y;
        // Fade toward the edges so the field reads as something the words sit
        // in, not a box behind them. Done here rather than with a CSS mask -
        // a mask over a canvas that repaints every frame halved the frame
        // rate. An ellipse, wider than tall, centred a little above middle.
        const ex = (x / w - 0.5) / 0.55;
        const ey = (y / h - 0.45) / 0.6;
        const edge = 1 - Math.min(1, ex * ex + ey * ey);
        if (edge <= 0) continue;
        ctx.globalAlpha = (0.07 + z * 0.15) * edge;
        // A filled square, not an arc: at one to three pixels the eye cannot
        // tell, and a path per point was the whole cost of the frame.
        const r = 1.2 + z * 2;
        ctx.fillRect(x - r / 2, y - r / 2, r, r);
      }
      ctx.globalAlpha = 1;
    };

    const readInk = () => {
      ink = getComputedStyle(canvas).color || ink;
    };

    const tick = (now: number) => {
      frame = 0;
      if (!onScreen || !tabShown) return;
      draw(now);
      frame = requestAnimationFrame(tick);
    };
    const start = () => {
      if (frame || still) return;
      last = 0;
      frame = requestAnimationFrame(tick);
    };

    resize();
    seed();
    readInk();
    draw(performance.now());
    canvas.classList.add("is-on");
    if (!still) start();

    // Every second, not every frame: a theme switch is rare and the call is
    // not free.
    const inkTimer = window.setInterval(readInk, 1000);

    const io = new IntersectionObserver(([e]) => {
      onScreen = e.isIntersecting;
      if (onScreen) start();
    });
    io.observe(canvas);
    const onVis = () => {
      tabShown = !document.hidden;
      if (tabShown) start();
    };
    document.addEventListener("visibilitychange", onVis);
    const ro = new ResizeObserver(() => {
      resize();
      if (still) draw(performance.now());
    });
    ro.observe(canvas);

    return () => {
      cancelAnimationFrame(frame);
      window.clearInterval(inkTimer);
      io.disconnect();
      ro.disconnect();
      document.removeEventListener("visibilitychange", onVis);
    };
  }, []);

  return <canvas ref={ref} className="herofield" aria-hidden="true" />;
}
