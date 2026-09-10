import "./globals.css";
import "leaflet/dist/leaflet.css";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import { api } from "@/lib/api";
import { formatCount, formatFreshnessTimestamp } from "@/lib/format";
import Logo from "@/components/Logo";
import NavLinks from "@/components/NavLinks";

const sans = Geist({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = Geist_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  // Kasauti (कसौटी) is the touchstone a jeweller rubs gold against to judge it.
  // It destroys nothing and accuses nothing; it says which pieces are worth
  // assaying. That is the claim this system makes and the one it refuses.
  title: {
    default: "Kasauti — MPLADS verification",
    template: "%s · Kasauti",
  },
  description:
    "Reads every MPLADS work, scores the ones that do not resemble their peers, and hands officials a ranked list of what to verify.",
};

export const navLinks = [
  { href: "/", label: "Overview" },
  { href: "/alerts", label: "Alerts" },
  { href: "/signals", label: "Signals" },
  { href: "/compliance", label: "Rules" },
  { href: "/projects", label: "Works" },
  { href: "/trends", label: "Trends" },
  { href: "/states", label: "States" },
  { href: "/map", label: "Map" },
  { href: "/analysis", label: "Agencies" },
  { href: "/provenance", label: "Sources" },
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
              <Logo />
              <span className="wordmark__text">
                Kasauti
                <span className="wordmark__sub">MPLADS verification</span>
              </span>
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
                Kasauti is the touchstone a jeweller rubs gold against: it says which
                pieces are worth testing, never which are false. MPLADS programme data
                via{" "}
                <a href="https://empoweredindian.in" target="_blank" rel="noopener noreferrer">
                  Empowered Indian
                </a>
                , which aggregates the official MoSPI portal. Not affiliated with any
                ministry.
              </span>
            </div>
            <div className="footer__wordmark" aria-hidden="true">
              Kasauti
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
