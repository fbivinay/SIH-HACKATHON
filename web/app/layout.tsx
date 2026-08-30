import "./globals.css";
import "leaflet/dist/leaflet.css";
import type { Metadata } from "next";
import { Source_Serif_4, Inter, IBM_Plex_Mono } from "next/font/google";
import Link from "next/link";
import { api } from "@/lib/api";
import { formatCount, formatFreshnessTimestamp } from "@/lib/format";

const sourceSerif = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-source-serif",
  display: "swap",
});
const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "MPLADS Risk Monitor",
  description: "Independent oversight of MPLADS local-area development works.",
};

const navLinks = [
  { href: "/", label: "Overview" },
  { href: "/map", label: "Risk Map" },
  { href: "/projects", label: "Projects" },
  { href: "/analysis", label: "Agency Analysis" },
];

// Never lets a data-freshness hiccup break the whole page - render a plain
// fallback string on any fetch/shape failure rather than a bare null or crash.
async function freshnessLine(): Promise<string> {
  try {
    const f = await api.dataFreshness();
    if (!f.finished_at) return "Data freshness unavailable";
    const scored = f.rows_scored ? ` · ${formatCount(f.rows_scored)} works scored` : "";
    return `Data last refreshed ${formatFreshnessTimestamp(f.finished_at)}${scored}`;
  } catch {
    return "Data freshness unavailable";
  }
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const freshness = await freshnessLine();
  return (
    <html lang="en" className={`${sourceSerif.variable} ${inter.variable} ${plexMono.variable}`}>
      <body className="flex min-h-screen flex-col">
        <header className="border-b border-[color:var(--line)] bg-[color:var(--surface)]">
          <div className="mx-auto max-w-7xl px-6 py-3 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0">
              <span className="seal" aria-hidden="true">MR</span>
              <div className="min-w-0">
                <div
                  className="truncate text-[1.05rem] font-semibold tracking-tight"
                  style={{ fontFamily: "var(--font-display)" }}
                >
                  MPLADS Risk Monitor
                </div>
                <div className="hidden sm:block text-xs text-[color:var(--muted)]">
                  Independent oversight of local-area development works
                </div>
              </div>
            </div>
            <nav className="flex items-center gap-1 text-sm">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="rounded px-3 py-1.5 text-[color:var(--ink)]/80 hover:bg-[color:var(--paper)] hover:text-[color:var(--ink)] transition-colors"
                >
                  {link.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <div className="flex-1">{children}</div>
        <footer className="mt-8 border-t border-[color:var(--line)] bg-[color:var(--surface)]">
          <div className="mx-auto max-w-7xl px-6 py-4 flex flex-wrap items-center justify-between gap-x-6 gap-y-1.5 text-xs text-[color:var(--muted)]">
            <span className="font-mono" style={{ fontFamily: "var(--font-data)" }}>
              {freshness}
            </span>
            <span>
              Data sourced from the MPLADS programme via{" "}
              <a
                href="https://empoweredindian.in"
                target="_blank"
                rel="noopener noreferrer"
                className="underline decoration-[color:var(--line)] underline-offset-2 hover:text-[color:var(--ink)]"
              >
                Empowered Indian
              </a>
              , which aggregates the official MoSPI MPLADS portal.
            </span>
          </div>
        </footer>
      </body>
    </html>
  );
}
