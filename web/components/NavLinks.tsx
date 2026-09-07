"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/**
 * Marks the current section. Client-side because the active link depends on the
 * pathname, and a server layout would have to be re-rendered per route to know
 * it — this is the only reason any of the shell ships JavaScript.
 */
export default function NavLinks({
  links,
}: {
  links: ReadonlyArray<{ href: string; label: string }>;
}) {
  const pathname = usePathname();
  return (
    <nav className="nav">
      {links.map((link) => {
        const active =
          link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            className="nav__link"
            aria-current={active ? "page" : undefined}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
