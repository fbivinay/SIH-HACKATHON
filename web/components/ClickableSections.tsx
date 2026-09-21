"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

/**
 * Makes every section that holds a link open that link from anywhere inside
 * it (owner's call, 2026-09-21: "the entire section clickable, not just the
 * underlined names, in the whole website").
 *
 * One delegated listener instead of a stretched link in every component. The
 * links stay real <a> elements - keyboard, screen reader, right-click and
 * middle-click all work on them exactly as before - and this only answers a
 * plain click that landed on the section's empty space or its text.
 *
 * Which link a section opens:
 *  - a table row: its first link, which on every table here is the row's
 *    subject (the district, the member, the work) - later links are context;
 *  - any other section: its link, if it has exactly one destination. A card
 *    listing four pages has no single meaning for a click on its blank space,
 *    so it is left alone rather than guessed.
 * The nearest section wins, so a list item with a link inside a card with
 * several opens the item's own link.
 */
const SECTIONS = [
  "tbody tr",
  "li",
  ".card",
  ".stat-card",
  ".slab-card",
  ".model-card",
  ".statecard",
  ".mpcard",
  ".archstep",
  ".compareslot",
  "article",
].join(",");

// A click on any of these already does its own thing.
const OWN_BEHAVIOUR =
  "a, button, input, select, textarea, label, summary, details[open] > *:not(summary), [role=button], [contenteditable], .leaflet-container, .review-actions";

export function targetFor(start: Element): HTMLAnchorElement | null {
  if (!start.closest("main")) return null;
  const section = start.closest<HTMLElement>(SECTIONS);
  if (!section || !section.closest("main")) return null;
  const links = Array.from(section.querySelectorAll<HTMLAnchorElement>("a[href]"));
  if (links.length === 0) return null;
  if (section.matches("tbody tr")) return links[0];
  const hrefs = new Set(links.map((a) => a.getAttribute("href")));
  return hrefs.size === 1 ? links[0] : null;
}

export default function ClickableSections() {
  const router = useRouter();

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0) return;
      const t = e.target as Element | null;
      if (!t || t.closest(OWN_BEHAVIOUR)) return;
      // Selecting a figure to copy it is not a request to leave the page.
      if (window.getSelection()?.toString()) return;
      const a = targetFor(t);
      if (!a) return;
      const href = a.getAttribute("href")!;
      const external = a.target === "_blank" || /^https?:\/\//.test(href) || a.hasAttribute("download");
      if (e.metaKey || e.ctrlKey || e.shiftKey || external) {
        window.open(a.href, "_blank", "noopener");
        return;
      }
      router.push(href);
    };
    // The pointer says so before the click does: a section is marked while the
    // pointer is in it, by the same test the click uses, so the ring cursor
    // never promises a click that would do nothing. Marked on entry rather
    // than for every section up front - a page can hold a thousand rows.
    // mouseover fires for every word span the pointer crosses, so the section
    // is found first and the link search runs only when it changes.
    let marked: HTMLElement | null = null;
    let lastSection: Element | null = null;
    const onOver = (e: MouseEvent) => {
      const t = e.target as Element | null;
      const section = t?.closest?.(SECTIONS) ?? null;
      if (section === lastSection) return;
      lastSection = section;
      const next = t && section && targetFor(t) ? (section as HTMLElement) : null;
      if (next === marked) return;
      marked?.removeAttribute("data-section-link");
      marked = next;
      marked?.setAttribute("data-section-link", "");
    };
    document.addEventListener("click", onClick);
    document.addEventListener("mouseover", onOver, { passive: true });
    return () => {
      document.removeEventListener("click", onClick);
      document.removeEventListener("mouseover", onOver);
      marked?.removeAttribute("data-section-link");
    };
  }, [router]);

  return null;
}
