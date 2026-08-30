import "./globals.css";
import type { Metadata } from "next";
import { Source_Serif_4, Inter, IBM_Plex_Mono } from "next/font/google";
import Link from "next/link";

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

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sourceSerif.variable} ${inter.variable} ${plexMono.variable}`}>
      <body>
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
        {children}
      </body>
    </html>
  );
}
