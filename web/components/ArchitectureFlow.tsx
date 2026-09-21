import Link from "next/link";
import { formatCount } from "@/lib/format";

/**
 * How the system works, end to end - the architecture slide of the deck
 * (docs: "SIH FINAL PPT", slides 2 and 3), drawn in the product's own
 * language rather than pasted as the slide's image: monochrome, with colour
 * only on the three risk bands, where colour means risk (CLAUDE.md §10).
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
  const ingest = [
    "Fetch the extract",
    "Validate every file before writing",
    "Clean and normalise",
    `Refuse bad rows, with a reason (${formatCount(refused)})`,
    "Reconcile with MoSPI's dashboard",
    "Store in PostgreSQL",
  ];
  const components = [
    { name: "Cost", weight: 25, how: "Against the district-and-sector median, with an Isolation Forest" },
    { name: "Delay", weight: 25, how: "Days past the completion date the source publishes" },
    { name: "Duplication", weight: 20, how: "Sentence-BERT similarity at the measured 0.94 cutoff" },
    { name: "Agency", weight: 15, how: "The agency's delay rate, vendor concentration and oldest unpaid bill" },
    { name: "Compliance", weight: 15, how: "Checkable MPLADS rules, each naming what it rests on" },
  ];
  const cohort = [
    "Year-end payment burst",
    "First-digit (Benford) anomaly",
    "Idle allocation",
    "Uniform sanction amounts",
  ];
  const stack = [
    "Next.js",
    "FastAPI",
    "PostgreSQL (Neon)",
    "Gemini",
    "Sentence-BERT",
    "Isolation Forest",
    "pandas",
    "GitHub Actions, nightly",
    "Vercel",
  ];

  return (
    <section className="archflow" aria-label="How Kasauti works">
      <h1 className="display">How Kasauti works</h1>

      {/* 1 -> 2: where the record comes from, and what happens to it first. */}
      <div className="archflow__row archflow__row--source">
        <article className="archstep">
          <span className="archstep__n">1</span>
          <h2 className="archstep__title">The published MPLADS record</h2>
          <dl className="archstep__figs">
            <div>
              <dt>Works</dt>
              <dd>{formatCount(works)}</dd>
            </div>
            <div>
              <dt>Payments</dt>
              <dd>{formatCount(payments)}</dd>
            </div>
          </dl>
          <p className="archstep__note">
            17th and 18th Lok Sabha. The Ministry&rsquo;s record, as Empowered Indian exports it.
          </p>
        </article>
        <span className="archflow__arrow" aria-hidden="true" />
        <article className="archstep archstep--wide">
          <span className="archstep__n">2</span>
          <h2 className="archstep__title">Ingest and validate, every night</h2>
          <ol className="archchain">
            {ingest.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ol>
        </article>
      </div>

      <span className="archflow__down" aria-hidden="true" />

      {/* 3 -> 4: every work gets a peer group, then five scores. */}
      <div className="archflow__row archflow__row--engine">
        <article className="archstep">
          <span className="archstep__n">3</span>
          <h2 className="archstep__title">Find each work&rsquo;s peers</h2>
          <ol className="archchain archchain--stack">
            <li><span>Keyword rules read the description</span></li>
            <li>
              <span>
                <b>Gemini</b> only where the rules cannot decide - and it may answer
                &ldquo;Other&rdquo;
              </span>
            </li>
            <li><span>Sector, district and term make the peer group</span></li>
          </ol>
        </article>
        <span className="archflow__arrow" aria-hidden="true" />
        <article className="archstep archstep--wide">
          <span className="archstep__n">4</span>
          <h2 className="archstep__title">Score the work against its peers</h2>
          <ul className="archweights">
            {components.map((c) => (
              <li key={c.name}>
                <span className="archweights__pct">{c.weight}%</span>
                <span className="archweights__name">{c.name}</span>
                <span className="archweights__how">{c.how}</span>
              </li>
            ))}
          </ul>
        </article>
      </div>

      <span className="archflow__down" aria-hidden="true" />

      {/* 5 -> 6 -> 7: a number, its reasons, and the people who act on it. */}
      <div className="archflow__row archflow__row--out">
        <article className="archstep">
          <span className="archstep__n">5</span>
          <h2 className="archstep__title">Risk score, 0 to 100</h2>
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
        <span className="archflow__arrow" aria-hidden="true" />
        <article className="archstep">
          <span className="archstep__n">6</span>
          <h2 className="archstep__title">Explain, then queue</h2>
          <ul className="archlist">
            <li>Why each work was flagged, in the record&rsquo;s own figures</li>
            <li>{formatCount(inQueue)} works at 40 and above, ranked</li>
            <li>Escalate, verify or dismiss, with an audit trail</li>
          </ul>
        </article>
        <span className="archflow__arrow" aria-hidden="true" />
        <article className="archstep">
          <span className="archstep__n">7</span>
          <h2 className="archstep__title">Read it at every level</h2>
          <ul className="archlinks">
            <li><Link href="/" className="link-quiet">Overview</Link> - the country</li>
            <li><Link href="/states" className="link-quiet">States</Link> - map and state desks</li>
            <li><Link href="/mps" className="link-quiet">MPs</Link> - every member, compared</li>
            <li><Link href="/projects" className="link-quiet">Projects</Link> - one work at a time</li>
          </ul>
        </article>
      </div>

      {/* The second level, kept apart on purpose (CLAUDE.md §4). */}
      <aside className="archcohort">
        <div>
          <h2 className="archstep__title">Beside the score, never inside it</h2>
          <p className="archstep__note">
            Four tests describe an agency or a member rather than a work. What they find is
            reported at that grain, and never added to any single work&rsquo;s score.
          </p>
        </div>
        <ul className="archcohort__tests">
          {cohort.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      </aside>

      <ul className="archstack" aria-label="Built with">
        {stack.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ul>
    </section>
  );
}
