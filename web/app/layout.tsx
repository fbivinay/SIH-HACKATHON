import "./globals.css";
import "leaflet/dist/leaflet.css";
import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import { api } from "@/lib/api";
import { formatCount, formatFreshnessTimestamp } from "@/lib/format";
import Logo from "@/components/Logo";
import Cursor from "@/components/Cursor";
import NavLinks from "@/components/NavLinks";
import OnHome from "@/components/OnHome";
import RiskTicker from "@/components/RiskTicker";
import ScrollReveal from "@/components/ScrollReveal";
import Splash from "@/components/Splash";

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

// Light only, whatever the OS or browser asks for: this writes the
// `color-scheme` meta so even the first paint before CSS arrives is light.
// The palette itself has no dark variant (globals.css).
export const viewport: Viewport = { colorScheme: "light" };

// Seven, in the order an official actually works: what is happening, what needs
// me, where, and then the supporting evidence.
//
// /signals, /compliance and /trends were deleted, not just de-navigated - the
// comment here used to say otherwise and was wrong the moment the files went.
// Their endpoints still serve, and because the problem statement names all
// three capabilities, their content moved rather than left:
//
//   cohort detectors + compliance rule book + blind spots -> /provenance
//   trend analysis + the quiet-agency early warning       -> /analysis
//
// If any of that goes missing again, those are the pages to look at.
export const navLinks = [
  { href: "/", label: "Overview" },
  { href: "/alerts", label: "Alerts" },
  { href: "/states", label: "States" },
  { href: "/map", label: "Map" },
  { href: "/projects", label: "Works" },
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
        {/* Phones are refused (see .phone-wall in globals.css). Inline and
            first in <body> so the flag lands before the first paint; a
            component would run after hydration and flash the site first. */}
        <script
          dangerouslySetInnerHTML={{
            __html:
              '(function(){var s=screen,r=Math.min(s.width,s.height)/Math.max(s.width,s.height),' +
              'c=matchMedia("(pointer: coarse)").matches;' +
              'if(/iPhone|Mobi/i.test(navigator.userAgent)||(c&&r<=0.6))document.documentElement.dataset.phone="1"})()',
          }}
        />
        <div className="phone-wall">
          <Logo size={72} />
          <h1>Kasauti can only be opened on a desktop or laptop.</h1>
          <p>Open this link on a larger screen to see the verification queue.</p>
        </div>
        {/* Client-only: with no JavaScript the page is simply there. */}
        <Splash />
        {/* Marks below-fold blocks so only those animate on scroll. */}
        <ScrollReveal />
        {/* The dot-and-ring pointer; renders nothing on touch devices. */}
        <Cursor />
        <div className="topbar">
        <header className="masthead">
          <div className="shell masthead__inner">
            <Link href="/" className="wordmark">
              <Logo size={62} />
              <span className="wordmark__text">
                Kasauti
                <span className="wordmark__sub"><b className="ai-word">AI-powered</b> MPLADS verification</span>
              </span>
            </Link>
            <NavLinks links={navLinks} />
            <Link href="/alerts" className="btn btn--solid">
              Open the queue
            </Link>
          </div>
        </header>

        {/* Under the masthead rather than inside it: the nav is navigation and
            this is content, and a reader who wants the nav should not have to
            wait for an API call to render it. Both sit in one sticky wrapper so
            the strip follows the nav without either knowing the other's height.
            Not on the overview, where the strip runs along the bottom instead
            (owner's call) so the opening screen is the masthead and the hero. */}
        <OnHome not>
          <RiskTicker />
        </OnHome>
        </div>

        <div className="flex-1">{children}</div>

        <OnHome>
          <div className="bottombar">
            <RiskTicker />
          </div>
        </OnHome>

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
