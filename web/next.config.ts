import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The Works list was folded into Alerts (2026-09-19). A link or bookmark to
  // /projects lands on the same filters there, scoped to every work unless it
  // named a band; query values pass through on their own. Exact path only -
  // /projects/[id], the page for one work, is untouched. Done here rather than
  // with redirect() in the page, because the layout streams first and a page
  // redirect then arrives as a client-side hop instead of a real 308.
  async redirects() {
    return [
      {
        source: "/projects",
        missing: [{ type: "query", key: "risk_level" }],
        destination: "/alerts?risk_level=ALL",
        permanent: true,
      },
      { source: "/projects", destination: "/alerts", permanent: true },
    ];
  },
};

export default nextConfig;
