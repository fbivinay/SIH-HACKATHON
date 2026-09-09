import "./globals.css";
import "leaflet/dist/leaflet.css";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import { api } from "@/lib/api";
import { formatCount, formatFreshnessTimestamp } from "@/lib/format";
import NavLinks from "@/components/NavLinks";

const sans = Geist({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = Geist_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "MPLADS Risk Monitor",
  description:
    "Reads every MPLADS work, scores the ones that do not fit, and hands officials a ranked list of what to verify.",
};

export const navLinks = [
  { href: "/", label: "Overview" },
  { href: "/alerts", label: "Alerts" },
  { href: "/signals", label: "Signals" },
  { href: "/projects", label: "Works" },
  { href: "/states", label: "States" },
  { href: "/map", label: "Map" },
  { href: "/analysis", label: "Agencies" },
];

// A freshness hiccup must not take the page with it: fall back to a plain
// string rather than a bare null or a thrown render.
async function freshnessLine(): Promise<string> {
  try {
    const f = await api.dataFreshness();
    if (!f.finished_at) return "Data freshness unavailable";
    const scored = f.rows_scored ? `, ${formatCount(f.rows_scored)} works scored` : "";
    return `Last refreshed ${formatFreshnessTimestamp(f.finished_at)}${scored}`;
  } catch {
    return "Data freshness unavailable";
  }
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const freshness = await freshnessLine();
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable}`}>
      <body className="flex min-h-screen flex-col">
        <header className="masthead">
          <div className="shell masthead__inner">
            <Link href="/" className="wordmark">
              <span className="wordmark__mark" aria-hidden="true">
                MR
              </span>
              MPLADS Risk Monitor
            </Link>
            <NavLinks links={navLinks} />
            <Link href="/alerts" className="btn btn--solid">
              Open the queue
            </Link>
          </div>
        </header>

        <div className="flex-1">{children}</div>

        <footer className="footer">
          <div className="shell">
            <div className="footer__meta">
              <span className="footer__freshness">{freshness}</span>
              <span className="max-w-md">
                MPLADS programme data via{" "}
                <a href="https://empoweredindian.in" target="_blank" rel="noopener noreferrer">
                  Empowered Indian
                </a>
                , which aggregates the official MoSPI portal. Not affiliated with any
                ministry.
              </span>
            </div>
            <div className="footer__wordmark" aria-hidden="true">
              MPLADS
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
