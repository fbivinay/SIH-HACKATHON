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
    ];
  },
};

export default nextConfig;
