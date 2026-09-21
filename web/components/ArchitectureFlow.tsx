import Image from "next/image";
import Link from "next/link";
import type { ComponentType, SVGProps } from "react";
import {
  Building2,
  CalendarClock,
  CloudDownload,
  Clock,
  Copy,
  Database,
  Equal,
  FileCheck2,
  FileSearch,
  FileX2,
  Gauge,
  Hash,
  Landmark,
  LayoutDashboard,
  ListChecks,
  ListOrdered,
  Map as MapIcon,
  Scale,
  Search,
  Sparkles,
  Tags,
  TrendingUp,
  UserCheck,
  Users,
  Wallet,
  Wand2,
} from "lucide-react";
import {
  siFastapi,
  siGithubactions,
  siGooglegemini,
  siHuggingface,
  siNextdotjs,
  siPandas,
  siPostgresql,
  siPython,
  siScikitlearn,
  siVercel,
  type SimpleIcon,
} from "simple-icons";
import Logo from "@/components/Logo";
import CountUp from "@/components/CountUp";
import ArchLive from "@/components/ArchLive";
import { formatCount } from "@/lib/format";

type Icon = ComponentType<SVGProps<SVGSVGElement> & { size?: number; strokeWidth?: number }>;

/** A product's own mark, drawn in ink like every other icon here. */
function BrandMark({ icon, size = 22 }: { icon: SimpleIcon; size?: number }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="currentColor" aria-hidden="true">
      <path d={icon.path} />
    </svg>
  );
}

/** A step's icon in its round tile, the way the deck sets its pictograms. */
function Tile({ icon: I, size = "md" }: { icon: Icon; size?: "md" | "sm" }) {
  return (
    <span className={`archicon archicon--${size}`} aria-hidden="true">
      <I size={size === "md" ? 22 : 16} strokeWidth={1.75} />
    </span>
  );
}

/**
 * How the system works, end to end - the deck's architecture (slides 2 and
 * 3), with its pictograms and the logos of what it is built on, in the
 * product's own ink: the only colour in it is on the three risk bands, where
 * colour means risk (CLAUDE.md §10).
 *
 * Step 1 carries the State Emblem beside the Ministry's name, as the deck's
 * slide does (owner's call, 2026-09-21), to say whose record this is. It
 * attributes the data and claims nothing more: the footer says the site is
 * not affiliated with any ministry, and that has to stay true beside it. The
 * Emblem's use is restricted by the State Emblem of India (Prohibition of
 * Improper Use) Act, 2005, which is why it appears nowhere else. The image is
 * Wikimedia Commons' "Emblem of India.svg", rendered once to a 9KB WebP.
 *
 * Every count comes from the live record, passed in by the page, so it cannot
 * go stale the way a typed figure did twice in the deck.
 */
export default function ArchitectureFlow({
  works,
  payments,
  refused,
  inQueue,
}: {
  works: number;
  payments: number;
  refused: number;
  inQueue: number;
}) {
  const ingest: Array<{ icon: Icon; label: string }> = [
    { icon: CloudDownload, label: "Fetch the extract" },
    { icon: FileCheck2, label: "Validate every file first" },
    { icon: Wand2, label: "Clean and normalise" },
    { icon: FileX2, label: `Refuse bad rows (${formatCount(refused)})` },
    { icon: Scale, label: "Reconcile with MoSPI" },
    { icon: Database, label: "Store in PostgreSQL" },
  ];
  const components: Array<{ icon: Icon; name: string; weight: number; how: string }> = [
    { icon: TrendingUp, name: "Cost", weight: 25, how: "District-and-sector median, with an Isolation Forest" },
    { icon: Clock, name: "Delay", weight: 25, how: "Days past the completion date the source publishes" },
    { icon: Copy, name: "Duplication", weight: 20, how: "Sentence-BERT similarity at the measured 0.94 cutoff" },
    { icon: Building2, name: "Agency", weight: 15, how: "Delay rate, vendor concentration, oldest unpaid bill" },
    { icon: ListChecks, name: "Compliance", weight: 15, how: "Checkable MPLADS rules, each naming what it rests on" },
  ];
  const cohort: Array<{ icon: Icon; label: string }> = [
    { icon: CalendarClock, label: "Year-end payment burst" },
    { icon: Hash, label: "First-digit (Benford) anomaly" },
    { icon: Wallet, label: "Idle allocation" },
    { icon: Equal, label: "Uniform sanction amounts" },
  ];
  const stack: Array<{ group: string; items: Array<{ icon: SimpleIcon; name: string; note: string }> }> = [
    { group: "Interface", items: [{ icon: siNextdotjs, name: "Next.js", note: "React, TypeScript" }, { icon: siVercel, name: "Vercel", note: "Hosting" }] },
    { group: "API", items: [{ icon: siFastapi, name: "FastAPI", note: "Python" }] },
    { group: "Data", items: [{ icon: siPostgresql, name: "PostgreSQL", note: "Neon" }, { icon: siPandas, name: "pandas", note: "Load and score" }] },
    {
      group: "AI and statistics",
      items: [
        { icon: siGooglegemini, name: "Gemini", note: "Sector labels" },
        { icon: siHuggingface, name: "Sentence-BERT", note: "Near-duplicates" },
        { icon: siScikitlearn, name: "scikit-learn", note: "Isolation Forest" },
      ],
    },
    { group: "Automation", items: [{ icon: siGithubactions, name: "GitHub Actions", note: "Nightly refresh" }, { icon: siPython, name: "Python", note: "Pipeline" }] },
  ];

  return (
    <section className="archflow" aria-label="How Kasauti works">
      <ArchLive />
      <div className="archflow__head">
        <Logo size={64} />
        <div>
          <h1 className="display">How Kasauti works</h1>
          <p className="archflow__tag">From the published record to a ranked list of what to verify</p>
        </div>
      </div>

      {/* 1 -> 2: where the record comes from, and what happens to it first. */}
      <div className="archflow__row archflow__row--source">
        <article className="archstep">
          <header className="archstep__head">
            <Tile icon={Landmark} />
            <div>
              <span className="archstep__n" style={{ ["--step" as string]: 0 }}>1</span>
              <h2 className="archstep__title">The published MPLADS record</h2>
            </div>
          </header>
          <div className="archgov">
            <Image
              src="/emblem-of-india.webp"
              alt="State Emblem of India"
              width={50}
              height={80}
              unoptimized
            />
            <div>
              <b className="archgov__name">Ministry of Statistics and Programme Implementation</b>
              <span className="archgov__sub">Government of India</span>
            </div>
          </div>
          <div className="archdata">
            <div className="archdata__item">
              <Tile icon={Database} size="sm" />
              <div>
                <b><CountUp text={formatCount(works)} /></b>
                <span>works</span>
              </div>
            </div>
            <div className="archdata__item">
              <Tile icon={Database} size="sm" />
              <div>
                <b><CountUp text={formatCount(payments)} /></b>
                <span>payments</span>
              </div>
            </div>
          </div>
          <p className="archstep__note">
            17th and 18th Lok Sabha - the Ministry&rsquo;s record, as Empowered Indian exports it.
          </p>
        </article>
        <span className="archflow__arrow" aria-hidden="true"><i className="archpacket" /></span>
        <article className="archstep">
          <header className="archstep__head">
            <Tile icon={FileCheck2} />
            <div>
              <span className="archstep__n" style={{ ["--step" as string]: 1 }}>2</span>
              <h2 className="archstep__title">Ingest and validate, every night</h2>
            </div>
          </header>
          <ol className="archpipe">
            {ingest.map((s, i) => (
              <li key={s.label} style={{ ["--station" as string]: i }}>
                <Tile icon={s.icon} />
                <span>{s.label}</span>
              </li>
            ))}
          </ol>
        </article>
      </div>

      <span className="archflow__down" aria-hidden="true"><i className="archpacket" /></span>

      {/* 3 -> 4: every work gets a peer group, then five scores. */}
      <div className="archflow__row archflow__row--engine">
        <article className="archstep">
          <header className="archstep__head">
            <Tile icon={Tags} />
            <div>
              <span className="archstep__n" style={{ ["--step" as string]: 2 }}>3</span>
              <h2 className="archstep__title">Find each work&rsquo;s peers</h2>
            </div>
          </header>
          <ol className="architems">
            <li>
              <Tile icon={Search} size="sm" />
              <span>Keyword rules read the description</span>
            </li>
            <li>
              <span className="archicon archicon--sm" aria-hidden="true">
                <BrandMark icon={siGooglegemini} size={16} />
              </span>
              <span>
                <b>Gemini</b> decides only where the rules cannot - and may answer &ldquo;Other&rdquo;
              </span>
            </li>
            <li>
              <Tile icon={Users} size="sm" />
              <span>Sector, district and term make the peer group</span>
            </li>
          </ol>
        </article>
        <span className="archflow__arrow" aria-hidden="true"><i className="archpacket" /></span>
        <article className="archstep">
          <header className="archstep__head">
            <Tile icon={Sparkles} />
            <div>
              <span className="archstep__n" style={{ ["--step" as string]: 3 }}>4</span>
              <h2 className="archstep__title">Score the work against its peers</h2>
            </div>
          </header>
          <ul className="archweights">
            {components.map((c) => (
              <li key={c.name}>
                <Tile icon={c.icon} size="sm" />
                <span className="archweights__pct">{c.weight}%</span>
                <span className="archweights__name">{c.name}</span>
                <span className="archweights__how">{c.how}</span>
                <span className="archweights__bar" aria-hidden="true">
                  <i style={{ ["--w" as string]: c.weight / 25 }} />
                </span>
              </li>
            ))}
          </ul>
        </article>
      </div>

      <span className="archflow__down" aria-hidden="true"><i className="archpacket" /></span>

      {/* 5 -> 6 -> 7: a number, its reasons, and the people who act on it. */}
      <div className="archflow__row archflow__row--out">
        <article className="archstep">
          <header className="archstep__head">
            <Tile icon={Gauge} />
            <div>
              <span className="archstep__n" style={{ ["--step" as string]: 4 }}>5</span>
              <h2 className="archstep__title">Risk score, 0 to 100</h2>
            </div>
          </header>
          <div className="archgauge" aria-hidden="true">
            <span className="archgauge__low" />
            <span className="archgauge__medium" />
            <span className="archgauge__high" />
            <span className="archgauge__sweep">
              <i />
            </span>
          </div>
          <ul className="archbands">
            <li className="archbands__low">
              <i aria-hidden="true" />
              <b>Low</b>
              <span>below 40</span>
            </li>
            <li className="archbands__medium">
              <i aria-hidden="true" />
              <b>Medium</b>
              <span>40 to 70</span>
            </li>
            <li className="archbands__high">
              <i aria-hidden="true" />
              <b>High</b>
              <span>70 and above</span>
            </li>
          </ul>
        </article>
        <span className="archflow__arrow" aria-hidden="true"><i className="archpacket" /></span>
        <article className="archstep">
          <header className="archstep__head">
            <Tile icon={FileSearch} />
            <div>
              <span className="archstep__n" style={{ ["--step" as string]: 5 }}>6</span>
              <h2 className="archstep__title">Explain, then queue</h2>
            </div>
          </header>
          <ul className="architems">
            <li>
              <Tile icon={FileSearch} size="sm" />
              <span>Why each work was flagged, in the record&rsquo;s own figures</span>
            </li>
            <li>
              <Tile icon={ListOrdered} size="sm" />
              <span>{formatCount(inQueue)} works at 40 and above, ranked</span>
            </li>
            <li>
              <Tile icon={UserCheck} size="sm" />
              <span>Escalate, verify or dismiss, with an audit trail</span>
            </li>
          </ul>
        </article>
        <span className="archflow__arrow" aria-hidden="true"><i className="archpacket" /></span>
        <article className="archstep">
          <header className="archstep__head">
            <Tile icon={LayoutDashboard} />
            <div>
              <span className="archstep__n" style={{ ["--step" as string]: 6 }}>7</span>
              <h2 className="archstep__title">Read it at every level</h2>
            </div>
          </header>
          <ul className="architems">
            <li>
              <Tile icon={LayoutDashboard} size="sm" />
              <span><Link href="/" className="link-quiet">Overview</Link> - the country</span>
            </li>
            <li>
              <Tile icon={MapIcon} size="sm" />
              <span><Link href="/states" className="link-quiet">States</Link> - map and desks</span>
            </li>
            <li>
              <Tile icon={Users} size="sm" />
              <span><Link href="/mps" className="link-quiet">MPs</Link> - every member, compared</span>
            </li>
            <li>
              <Tile icon={ListChecks} size="sm" />
              <span><Link href="/projects" className="link-quiet">Projects</Link> - one work at a time</span>
            </li>
          </ul>
        </article>
      </div>

      {/* The second level, kept apart on purpose (CLAUDE.md §4). */}
      <aside className="archcohort">
        <div className="archcohort__lead">
          <Tile icon={Building2} />
          <div>
            <h2 className="archstep__title">Beside the score, never inside it</h2>
            <p className="archstep__note">
              Four tests describe an agency or a member rather than a work. What they find is
              reported at that grain, and never added to any single work&rsquo;s score.
            </p>
          </div>
        </div>
        <ul className="archcohort__tests">
          {cohort.map((c) => (
            <li key={c.label}>
              <Tile icon={c.icon} size="sm" />
              <span>{c.label}</span>
            </li>
          ))}
        </ul>
      </aside>

      <div className="archstack" aria-label="Built with">
        <h2 className="archstack__title">Built with</h2>
        <div className="archstack__groups">
          {stack.map((g) => (
            <div key={g.group} className="archstack__group">
              <span className="archstack__label">{g.group}</span>
              <ul>
                {g.items.map((t) => (
                  <li key={t.name}>
                    <BrandMark icon={t.icon} />
                    <span>
                      <b>{t.name}</b>
                      <small>{t.note}</small>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
