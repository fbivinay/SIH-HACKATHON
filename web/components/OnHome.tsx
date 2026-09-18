"use client";

import { usePathname } from "next/navigation";

/**
 * Renders its children on the overview only.
 *
 * Client-side for the same reason NavLinks is: the shared layout does not know
 * the route, and this is cheaper than a second root layout, which would turn
 * every hop between the overview and the rest into a full page load.
 */
export default function OnHome({ children }: { children: React.ReactNode }) {
  return usePathname() === "/" ? <>{children}</> : null;
}
