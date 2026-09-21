import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Old addresses. The queue lives at /projects (renamed from /alerts on
  // 2026-09-20, after the Works list was folded into it on 2026-09-19), the
  // map at the top of /states. Query values pass through on their own. Exact
  // paths only - /projects/[id], the page for one work, is untouched. Done
  // here rather than with redirect() in a page, because the layout streams
  // first and a page redirect then arrives as a client-side hop rather than a
  // real 308.
  async redirects() {
    return [
      { source: "/alerts", destination: "/projects", permanent: true },
      { source: "/map", destination: "/states", permanent: true },
      // The Agencies page became the MPs page (owner's call, 2026-09-21).
      { source: "/analysis", destination: "/mps", permanent: true },
    ];
  },
  // Member photographs and the emblem are ours and change at most nightly
  // (scripts/fetch_mp_profiles.py), but Vercel serves public/ with
  // max-age=0 by default, so every visit re-asked for every face on the page.
  // A day in the browser, and a week of serving the old one while fetching the
  // new: a replaced photograph shows by the next day at the latest.
  async headers() {
    const day = "public, max-age=86400, stale-while-revalidate=604800";
    return [
      { source: "/mps/:file*", headers: [{ key: "Cache-Control", value: day }] },
      { source: "/emblem-of-india.webp", headers: [{ key: "Cache-Control", value: day }] },
      { source: "/logo.png", headers: [{ key: "Cache-Control", value: day }] },
    ];
  },
  // The desks' term moves from the query string into the path, invisibly:
  // /state/Kerala?ls_term=17 is served by /state/Kerala/t/17. A page that
  // reads searchParams is rendered on every request; one whose inputs are all
  // in the path is cached on its first visit and prefetched in full by every
  // link to it. Every existing link keeps its address. beforeFiles, because
  // /state/Kerala is itself a page and an ordinary rewrite would never run.
  async rewrites() {
    const term = [{ type: "query" as const, key: "ls_term", value: "(?<t>17|18)" }];
    return {
      beforeFiles: [
        { source: "/state/:state", has: term, destination: "/state/:state/t/:t" },
        { source: "/district/:state/:district", has: term, destination: "/district/:state/:district/t/:t" },
        { source: "/mp/:id", has: term, destination: "/mp/:id/t/:t" },
      ],
      afterFiles: [],
      fallback: [],
    };
  },
};

export default nextConfig;
