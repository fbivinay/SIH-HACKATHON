"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { TERMS, termHref as href } from "@/lib/terms";

/**
 * The Lok Sabha scope, as the same pill group the navigation uses.
 *
 * It was three outline buttons and a `<Link>` each, which meant every switch
 * was a segment navigation: `app/loading.tsx` answered it in ~150ms with the
 * page skeleton, the figures vanished, and the whole screen rebuilt. That is
 * the lag - not the fetch, the teardown.
 *
 * `router.replace` inside `startTransition` navigates without ever unmounting
 * what is on screen: React keeps the current figures rendered until the new
 * ones are ready, and `isPending` is a real signal in the meantime rather than
 * a guess. The figures dim while it runs (`[data-pending]`, read by
 * `.home-figures:has(...)` in globals.css) and the new numbers count up from
 * the old ones when they arrive.
 *
 * `replace`, not `push`: a term is a view of one page, and three switches
 * should not be three entries in the reader's back history.
 */

export default function TermSwitch({ current }: { current: string }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  return (
    <nav
      className="nav nav--inline"
      aria-label="Lok Sabha term"
      data-pending={pending ? "" : undefined}
    >
      {TERMS.map((t) => {
        const active = t.value === current;
        return (
          <a
            key={t.value || "all"}
            href={href(t.value)}
            className="nav__link"
            aria-current={active ? "true" : undefined}
            // Warm the route on approach, so the switch itself has nothing to
            // wait for on a second visit.
            onMouseEnter={() => router.prefetch(href(t.value))}
            onFocus={() => router.prefetch(href(t.value))}
            onClick={(e) => {
              // Let a modified click open a new tab, as the link it is.
              if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
              e.preventDefault();
              if (active) return;
              startTransition(() => router.replace(href(t.value), { scroll: false }));
            }}
          >
            {t.label}
          </a>
        );
      })}
    </nav>
  );
}
