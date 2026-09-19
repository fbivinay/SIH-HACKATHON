import "./globals.css";
import "leaflet/dist/leaflet.css";
import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import { api } from "@/lib/api";
import { formatCount, formatFreshnessTimestamp } from "@/lib/format";
import Logo from "@/components/Logo";
import NavLinks from "@/components/NavLinks";
import OnHome from "@/components/OnHome";
import RiskTicker from "@/components/RiskTicker";
import ScrollReveal from "@/components/ScrollReveal";
import WordLift from "@/components/WordLift";
import FoldHeight from "@/components/FoldHeight";
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

// Six, in the order an official actually works: what is happening, what needs
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
      <body>
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
        {/* Wraps words so only the one under the pointer zooms. */}
        <WordLift />
        {/* Measures the overview's first screen; see --fold-h. */}
        <FoldHeight />
        {/* See .viewport-column. On every page but the overview, main is a
            block child and takes its own height. */}
        <div className="viewport-column">
        <div className="topbar">
        <header className="masthead">
          <div className="shell masthead__inner">
            <Link href="/" className="wordmark">
              <Logo size={74} />
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

        </div>

        <div className="flex flex-1 flex-col">{children}</div>

        <OnHome>
          <div className="bottombar">
            <RiskTicker />
          </div>
        </OnHome>
        </div>

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
            {/* Who built it and how to reach them, laid out the way his own
                portfolio lays it out: labelled rows for the contact details,
                the profiles as marks beneath the name. Every value here is one
                he already publishes at rvinaykumar-my-portfolio.vercel.app;
                nothing is taken from the machine this was built on. The marks
                are drawn in currentColor - a logo in its own brand colour would
                be the one hue on this site that does not mean risk. */}
            <div className="footer__contact">
              <div className="footer__who">
                <span className="footer__byname">Built by R Vinay Kumar and team</span>
                <nav className="footer__social" aria-label="Profiles">
                  <a
                    href="https://www.linkedin.com/in/r-vinay-kumar-139938215"
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label="LinkedIn"
                    title="LinkedIn"
                  >
                    <svg viewBox="0 0 24 24" width="17" height="17" fill="currentColor" aria-hidden="true">
                      <path d="M20.45 20.45h-3.56v-5.57c0-1.33-.03-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.95v5.66H9.35V9h3.41v1.56h.05a3.74 3.74 0 0 1 3.37-1.85c3.6 0 4.27 2.37 4.27 5.46v6.28ZM5.34 7.43a2.07 2.07 0 1 1 0-4.13 2.07 2.07 0 0 1 0 4.13ZM7.12 20.45H3.55V9h3.57v11.45ZM22.22 0H1.77C.79 0 0 .77 0 1.72v20.56C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.72V1.72C24 .77 23.2 0 22.22 0Z" />
                    </svg>
                  </a>
                  <a
                    href="https://github.com/fbivinay/SIH-HACKATHON"
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label="This project on GitHub"
                    title="This project on GitHub"
                  >
                    <svg viewBox="0 0 24 24" width="17" height="17" fill="currentColor" aria-hidden="true">
                      <path d="M12 .3a12 12 0 0 0-3.8 23.4c.6.1.8-.3.8-.6v-2c-3.3.7-4-1.6-4-1.6-.6-1.4-1.4-1.8-1.4-1.8-1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.7-1.6-2.7-.3-5.5-1.3-5.5-5.9 0-1.3.5-2.4 1.2-3.2-.1-.3-.5-1.5.1-3.2 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0C17.1 4.9 18.1 5.2 18.1 5.2c.6 1.7.2 2.9.1 3.2.8.8 1.2 1.9 1.2 3.2 0 4.6-2.8 5.6-5.5 5.9.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A12 12 0 0 0 12 .3Z" />
                    </svg>
                  </a>
                  <a
                    href="https://rvinaykumar-my-portfolio.vercel.app/"
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label="Portfolio"
                    title="Portfolio"
                  >
                    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.9" aria-hidden="true">
                      <circle cx="12" cy="12" r="9.2" />
                      <path d="M2.8 12h18.4M12 2.8c2.4 2.5 3.7 5.8 3.7 9.2s-1.3 6.7-3.7 9.2c-2.4-2.5-3.7-5.8-3.7-9.2S9.6 5.3 12 2.8Z" />
                    </svg>
                  </a>
                </nav>
              </div>
              <dl className="footer__details">
                <div>
                  <dt>Email</dt>
                  <dd>
                    <a href="mailto:rvinaykumar6924@gmail.com">rvinaykumar6924@gmail.com</a>
                  </dd>
                </div>
                <div>
                  <dt>Location</dt>
                  <dd>Bengaluru, Karnataka, India</dd>
                </div>
              </dl>
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
