import Link from "next/link";

/**
 * How the score is built and what it will not say.
 *
 * The overview, below the first screen: the owner wants the figures to own
 * the opening screen and this to follow it, not to leave the page.
 */
// Same weights and thresholds as data/scoring.py. Stated on the page because a
// score nobody can take apart is a score nobody should act on.
const COMPONENTS = [
  {
    name: "Cost",
    weight: "25%",
    method:
      "Sanctioned amount against the median for the same sector in the same district, blended with an isolation forest over amount, delay and spend.",
    guard: "Silent unless the district has at least 8 comparable works.",
  },
  {
    name: "Delay",
    weight: "25%",
    method:
      "Days past expected completion, taken from the recommendation and completion dates the portal publishes.",
    guard: "A work with no recorded schedule scores zero, not high.",
  },
  {
    name: "Duplication",
    weight: "20%",
    method:
      "Sentence-transformer embeddings of the work description, compared inside the same district and sector at 0.94 cosine similarity.",
    guard: "Near-identical wording is a lead, not a finding.",
  },
  {
    name: "Agency",
    weight: "15%",
    method:
      "The implementing agency's delay rate, how concentrated its payments are across vendors, and how long its oldest payment has been pending.",
    guard: "Measured per Lok Sabha term, so terms are never pooled.",
  },
  {
    name: "Compliance",
    weight: "15%",
    method:
      "Four stated rules: a recommended work with no schedule, a completed work with no completion date, a completed work with no photograph, and spend beyond the sanction — which cannot fire, because the source publishes one figure per completed work and it serves as both.",
    guard: "Each breach names the rule it breaks. The full book is on Sources.",
  },
];

// Three limits, seven points each, because a limit stated in one line reads as
// a disclaimer and a limit itself has to be checkable. Every point here is
// either a rule in data/scoring.py or an entry in COMPLIANCE_BLIND_SPOTS in
// api/main.py - none of it is written fresh for this page.
//
// The fourth limit, that no model decides alone, moved to /provenance with the
// models it is about; the fourth cell of this grid points there.
const LIMITS = [
  {
    title: "It does not allege wrongdoing",
    points: [
      "A score is a comparison, not a finding: it says a work does not resemble works like it.",
      "Its peers are the works in the same district and the same sector, within one Lok Sabha term.",
      "Five components with fixed weights make it - cost 25%, delay 25%, duplication 20%, agency 15%, the scheme's own rules 15%.",
      "Each component names the rows it came from, so any flag can be read back to the record and argued with.",
      "The cost comparison stays silent unless a district has at least eight comparable works.",
      "What a pattern across an agency or a member shows is reported at that grain, never folded into one work's score.",
      "A reviewer's decision - verified, escalated, dismissed - records what a person concluded, and never moves the score.",
    ],
  },
  {
    title: "It invents no fields",
    points: [
      "No progress percentage is published for an MPLADS work, so none is shown.",
      "No beneficiary count is published, so the system cannot say who a work served.",
      "No geo-tag is published, so nothing here can place a work on the ground.",
      "No bill value or invoice is published, so spending is only ever the totals the source gives.",
      "The source publishes one figure per completed work, recorded as both sanction and expenditure - so the overspend rule cannot fire on this data, and says so rather than reading as passed.",
      "The portal's own category column reads \u201cNormal/Others\u201d on 98.1% of works: the sector shown is derived from the description, good enough to compare like with like and not good enough to call a work impermissible.",
      "Per-work sanction ceilings are not published beside the works, so cost is judged against comparable works rather than against a rule.",
    ],
  },
  {
    title: "It reports, it does not forecast",
    points: [
      "Every figure describes the record as it already stands, not where it is heading.",
      "Delay is days past the completion date the source itself publishes.",
      "A work with no recorded schedule scores zero on delay, not high - an absent date is not a late one.",
      "No progress milestones are published, so there is nothing to project a completion date from.",
      "Cost is distance from the median of comparable works, not an estimate of what a work should have cost.",
      "The nearest thing to an early warning is money committed to an agency that has paid nobody in six months, which is an observation about payments already made.",
      "Figures move when the record moves: the published extract is reloaded and rescored nightly, and the page says when that last happened.",
    ],
  },
];

export default function ScoreMethod() {
  return (
    <>
    <section className="shell mt-9">
      <div className="slab">
        <div className="text-center">
          <h2 className="section-head">What the score is made of</h2>
          <p className="lede">
            Five components, fixed weights, no black box. Every one can be read back to the
            rows it came from.
          </p>
        </div>

        <div className="mt-9 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {COMPONENTS.map((c) => (
            <div key={c.name} className="slab-card">
              <div className="flex items-baseline justify-between gap-3">
                <h3 className="text-[0.98rem] font-medium">{c.name}</h3>
                <span
                  className="text-[0.78rem] tabular-nums"
                  style={{ fontFamily: "var(--font-data)", color: "var(--on-slab-2)" }}
                >
                  {c.weight}
                </span>
              </div>
              <p className="mt-2 text-[0.83rem] leading-relaxed" style={{ color: "var(--on-slab-2)" }}>
                {c.method}
              </p>
              <p className="mt-2.5 text-[0.78rem] leading-relaxed" style={{ color: "var(--on-slab-2)", opacity: 0.75 }}>
                {c.guard}
              </p>
            </div>
          ))}

          <div className="slab-card flex flex-col justify-between">
            <div>
              <h3 className="text-[0.98rem] font-medium">Bands</h3>
              <p className="mt-2 text-[0.83rem] leading-relaxed" style={{ color: "var(--on-slab-2)" }}>
                Below 40 a work is low risk and stays out of the queue. 40 to 70 is medium.
                Above 70 is high, and goes to the top of the list.
              </p>
            </div>
            <Link href="/alerts" className="btn btn--solid mt-4 self-start">
              See what is flagged
            </Link>
          </div>
        </div>
      </div>
    </section>

    <section className="shell mt-6">
      <div className="text-center">
        <h2 className="section-head">What it will not tell you</h2>
        <p className="lede">
          The gaps matter as much as the findings, so they are stated rather than papered
          over.
        </p>
      </div>
      <div className="mt-8 grid gap-3 md:grid-cols-2 lg:grid-cols-4">
        {LIMITS.map((l) => (
          <div key={l.title} className="card">
            <h3 className="text-[0.98rem] font-medium">{l.title}</h3>
            <ul className="limit-points">
              {l.points.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>
          </div>
        ))}
        {/* The fourth cell is the way out of this page rather than a fourth
            limit: the full blind-spot list, the rule book and the detectors are
            all on Sources, and so is the limit these three used to be joined
            by - that no model decides alone. */}
        <div className="card card--more">
          <h3 className="text-[0.98rem] font-medium">And the rest of it</h3>
          <p className="mt-2 text-[0.85rem] leading-relaxed" style={{ color: "var(--ink-2)" }}>
            Four more blind spots are written out in full on Sources, beside the rule
            book each compliance flag comes from, the detectors that describe an agency
            rather than a work, and what each of the three models decides.
          </p>
          <Link href="/provenance" className="btn btn--quiet mt-4 self-start">
            Read the rest on Sources
          </Link>
        </div>
      </div>
    </section>
    </>
  );
}
